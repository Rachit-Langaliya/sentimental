"""
Network Analysis Service — Phase 6.

Builds an interaction graph from ingested posts:
  - Nodes:  anonymised author-hashes (pseudonymised per DPDP Act)
  - Edges:  co-topic interactions (same topic window), weighted by volume
  - Metrics: PageRank, betweenness centrality (sampled), Louvain communities

With USE_REAL_NLP=True: uses networkx + python-louvain if installed.
Fallback: platform-based community assignment + degree-ranked influence.

Output is stored as lightweight JSON dicts — not persisted to a dedicated
table (graph is recomputed on demand, sized to fit in a single API response).
"""
from __future__ import annotations

import hashlib
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Platform, PostNLP, RawPost

logger = structlog.get_logger()

MAX_NODES    = 120   # cap nodes for readable graph
MAX_EDGES    = 400   # cap edges
EDGE_WINDOW  = timedelta(hours=2)   # posts within this window on same topic → edge


# ── Main entry ────────────────────────────────────────────────────────────────

async def build_network(db: AsyncSession, days: int = 7) -> dict[str, Any]:
    """
    Build and return the full network graph dict:
      { nodes, edges, communities, influencers, bridges, stats }
    """
    now = datetime.now(timezone.utc)
    window = now - timedelta(days=days)

    plat_r = await db.execute(select(Platform))
    plat_map: dict[int, str] = {p.id: p.name for p in plat_r.scalars().all()}

    rows_r = await db.execute(
        select(
            RawPost.author_hash,
            RawPost.platform_id,
            RawPost.post_ts,
            RawPost.metadata_,
            PostNLP.sentiment,
        )
        .outerjoin(PostNLP, PostNLP.post_id == RawPost.id)
        .where(RawPost.post_ts >= window)
        .where(RawPost.author_hash.isnot(None))
        .where(RawPost.expires_at > now)
        .order_by(RawPost.post_ts)
        .limit(5000)
    )
    posts = rows_r.all()

    if not posts:
        return _synthetic_network()

    # Build adjacency and node attributes
    nodes, edges = _build_graph(posts, plat_map)

    if len(nodes) < 5:
        return _synthetic_network()

    # Limit graph size
    nodes, edges = _prune(nodes, edges)

    # Community detection
    communities = _detect_communities(nodes, edges)
    for n in nodes:
        n["community_id"] = communities.get(n["id"], 0)

    # PageRank
    pr = _pagerank(nodes, edges)
    for n in nodes:
        n["pagerank"] = round(pr.get(n["id"], 0.0), 6)

    # Betweenness (sampled — exact is O(V*E))
    bt = _betweenness_sampled(nodes, edges, samples=min(len(nodes), 30))
    for n in nodes:
        n["betweenness"] = round(bt.get(n["id"], 0.0), 6)
        n["is_bridge"] = bt.get(n["id"], 0.0) > _bridge_threshold(bt)

    # Derived lists
    influencers = _top_influencers(nodes)
    bridges     = _bridge_actors(nodes)
    comm_list   = _community_list(nodes, plat_map)
    stats       = _graph_stats(nodes, edges, communities)

    return {
        "nodes":       nodes,
        "edges":       edges,
        "communities": comm_list,
        "influencers": influencers,
        "bridges":     bridges,
        "stats":       stats,
        "generated_at": now.isoformat(),
    }


# ── Graph construction ────────────────────────────────────────────────────────

def _build_graph(posts: list, plat_map: dict[int, str]) -> tuple[list[dict], list[dict]]:
    """
    Co-topic edge: two distinct authors who posted on the same topic within
    EDGE_WINDOW hours. Edge weight = number of such co-occurrences.
    """
    node_attrs: dict[str, dict] = {}
    edge_counts: dict[tuple[str, str], int] = defaultdict(int)

    # Group posts by topic
    by_topic: dict[str, list] = defaultdict(list)
    for p in posts:
        topic = (p.metadata_ or {}).get("topic", "unknown")
        by_topic[topic].append(p)

    for topic, topic_posts in by_topic.items():
        # Sort by time
        topic_posts = sorted(topic_posts, key=lambda p: p.post_ts)
        # Sliding window
        for i, p1 in enumerate(topic_posts):
            # Accumulate node
            h1 = p1.author_hash
            if h1 not in node_attrs:
                node_attrs[h1] = {
                    "id": h1,
                    "label": _short_label(h1),
                    "platform": plat_map.get(p1.platform_id, "unknown"),
                    "post_count": 0,
                    "topics": set(),
                    "sentiments": defaultdict(int),
                }
            node_attrs[h1]["post_count"] += 1
            node_attrs[h1]["topics"].add(topic)
            if p1.sentiment:
                node_attrs[h1]["sentiments"][p1.sentiment] += 1

            for p2 in topic_posts[i + 1:]:
                if (p2.post_ts - p1.post_ts) > EDGE_WINDOW:
                    break
                h2 = p2.author_hash
                if h2 == h1:
                    continue
                key = (min(h1, h2), max(h1, h2))
                edge_counts[key] += 1

                if h2 not in node_attrs:
                    node_attrs[h2] = {
                        "id": h2,
                        "label": _short_label(h2),
                        "platform": plat_map.get(p2.platform_id, "unknown"),
                        "post_count": 0,
                        "topics": set(),
                        "sentiments": defaultdict(int),
                    }
                node_attrs[h2]["post_count"] += 1
                node_attrs[h2]["topics"].add(topic)
                if p2.sentiment:
                    node_attrs[h2]["sentiments"][p2.sentiment] += 1

    # Serialise node attrs
    nodes = []
    for h, attrs in node_attrs.items():
        sents = dict(attrs["sentiments"])
        total = max(sum(sents.values()), 1)
        dominant_sent = max(sents, key=sents.get) if sents else "neutral"
        nodes.append({
            "id": h,
            "label": attrs["label"],
            "platform": attrs["platform"],
            "post_count": attrs["post_count"],
            "topic_count": len(attrs["topics"]),
            "dominant_sentiment": dominant_sent,
            "community_id": 0,
            "pagerank": 0.0,
            "betweenness": 0.0,
            "is_bridge": False,
        })

    edges = [
        {"source": s, "target": t, "weight": w}
        for (s, t), w in edge_counts.items()
        if s in node_attrs and t in node_attrs
    ]

    return nodes, edges


def _short_label(h: str) -> str:
    """4-char display label from hash prefix."""
    return h[:4].upper()


def _prune(nodes: list[dict], edges: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep the MAX_NODES highest-degree nodes and their edges."""
    if len(nodes) <= MAX_NODES and len(edges) <= MAX_EDGES:
        return nodes, edges

    # Compute degree
    degree: dict[str, int] = defaultdict(int)
    for e in edges:
        degree[e["source"]] += e["weight"]
        degree[e["target"]] += e["weight"]

    top_ids = {n["id"] for n in sorted(nodes, key=lambda n: degree.get(n["id"], 0), reverse=True)[:MAX_NODES]}
    pruned_nodes = [n for n in nodes if n["id"] in top_ids]

    pruned_edges = [e for e in edges if e["source"] in top_ids and e["target"] in top_ids]
    # Sort edges by weight desc and cap
    pruned_edges.sort(key=lambda e: -e["weight"])
    pruned_edges = pruned_edges[:MAX_EDGES]

    return pruned_nodes, pruned_edges


# ── Algorithms ────────────────────────────────────────────────────────────────

def _pagerank(nodes: list[dict], edges: list[dict], iterations: int = 50, d: float = 0.85) -> dict[str, float]:
    ids = [n["id"] for n in nodes]
    n = len(ids)
    if n == 0:
        return {}

    # Adjacency: out-edges with weights
    out_weight: dict[str, float] = defaultdict(float)
    in_edges: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for e in edges:
        w = float(e["weight"])
        out_weight[e["source"]] += w
        in_edges[e["target"]].append((e["source"], w))
        out_weight[e["target"]] += w
        in_edges[e["source"]].append((e["target"], w))  # undirected

    pr = {nid: 1.0 / n for nid in ids}
    for _ in range(iterations):
        new_pr: dict[str, float] = {}
        for nid in ids:
            rank = (1 - d) / n
            for src, w in in_edges[nid]:
                ow = out_weight[src]
                if ow > 0:
                    rank += d * pr[src] * (w / ow)
            new_pr[nid] = rank
        pr = new_pr

    # Normalise to [0, 1]
    max_pr = max(pr.values()) or 1.0
    return {nid: v / max_pr for nid, v in pr.items()}


def _betweenness_sampled(
    nodes: list[dict], edges: list[dict], samples: int = 30
) -> dict[str, float]:
    """
    Sampled betweenness: BFS from `samples` random source nodes,
    count how many shortest paths pass through each node.
    Approximate — sufficient for identifying clear bridge actors.
    """
    ids = [n["id"] for n in nodes]
    if len(ids) < 3:
        return {}

    # Build adjacency list (undirected)
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        adj[e["source"]].append(e["target"])
        adj[e["target"]].append(e["source"])

    bt: dict[str, float] = defaultdict(float)
    rng = random.Random(42)
    sources = rng.sample(ids, min(samples, len(ids)))

    for src in sources:
        # BFS to find shortest paths
        dist: dict[str, int] = {src: 0}
        pred: dict[str, list[str]] = defaultdict(list)
        sigma: dict[str, int] = defaultdict(int)
        sigma[src] = 1
        queue = [src]
        order = []

        while queue:
            v = queue.pop(0)
            order.append(v)
            for w in adj[v]:
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist.get(w) == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        # Accumulate dependency
        delta: dict[str, float] = defaultdict(float)
        for w in reversed(order):
            for v in pred[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != src:
                bt[w] += delta[w]

    # Normalise
    max_bt = max(bt.values()) if bt else 1.0
    return {k: v / max_bt for k, v in bt.items()}


def _bridge_threshold(bt: dict[str, float]) -> float:
    if not bt:
        return 1.0
    vals = sorted(bt.values(), reverse=True)
    if len(vals) < 4:
        return vals[0] * 0.5
    # Top ~15% by betweenness are bridges
    idx = max(1, len(vals) // 7)
    return vals[idx]


def _detect_communities(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    """
    Louvain via python-louvain if available; falls back to platform-based communities.
    """
    try:
        import community as cm  # python-louvain
        import networkx as nx

        G = nx.Graph()
        for n in nodes:
            G.add_node(n["id"])
        for e in edges:
            G.add_edge(e["source"], e["target"], weight=e["weight"])
        return cm.best_partition(G, weight="weight")
    except Exception:
        # Fallback: community = platform index
        plat_ids = {n["platform"]: i for i, n in enumerate({n["platform"]: n for n in nodes}.values())}
        return {n["id"]: plat_ids.get(n["platform"], 0) for n in nodes}


# ── Derived outputs ────────────────────────────────────────────────────────────

def _top_influencers(nodes: list[dict], top_n: int = 10) -> list[dict]:
    ranked = sorted(nodes, key=lambda n: n["pagerank"], reverse=True)[:top_n]
    return [
        {
            "rank": i + 1,
            "label": n["label"],
            "platform": n["platform"],
            "pagerank": n["pagerank"],
            "post_count": n["post_count"],
            "community_id": n["community_id"],
            "dominant_sentiment": n["dominant_sentiment"],
        }
        for i, n in enumerate(ranked)
    ]


def _bridge_actors(nodes: list[dict], top_n: int = 8) -> list[dict]:
    bridges = [n for n in nodes if n["is_bridge"]]
    bridges.sort(key=lambda n: n["betweenness"], reverse=True)
    return [
        {
            "label": n["label"],
            "platform": n["platform"],
            "betweenness": n["betweenness"],
            "community_id": n["community_id"],
            "post_count": n["post_count"],
        }
        for n in bridges[:top_n]
    ]


def _community_list(nodes: list[dict], plat_map: dict[int, str]) -> list[dict]:
    groups: dict[int, list[dict]] = defaultdict(list)
    for n in nodes:
        groups[n["community_id"]].append(n)

    result = []
    for cid, members in sorted(groups.items()):
        plats = [m["platform"] for m in members]
        plat_counts: dict[str, int] = defaultdict(int)
        for p in plats:
            plat_counts[p] += 1
        dominant_plat = max(plat_counts, key=plat_counts.get)  # type: ignore[arg-type]
        avg_pr = sum(m["pagerank"] for m in members) / len(members)
        result.append({
            "id": cid,
            "name": f"Community {cid + 1} ({dominant_plat})",
            "size": len(members),
            "dominant_platform": dominant_plat,
            "avg_pagerank": round(avg_pr, 6),
            "platform_breakdown": dict(plat_counts),
        })
    return sorted(result, key=lambda c: -c["size"])


def _graph_stats(nodes: list[dict], edges: list[dict], communities: dict[str, int]) -> dict:
    n = len(nodes)
    e = len(edges)
    density = (2 * e) / (n * (n - 1)) if n > 1 else 0.0
    avg_degree = (2 * e) / n if n > 0 else 0.0
    return {
        "node_count": n,
        "edge_count": e,
        "community_count": len(set(communities.values())),
        "avg_degree": round(avg_degree, 2),
        "density": round(density, 4),
        "bridge_count": sum(1 for nd in nodes if nd.get("is_bridge")),
    }


# ── Synthetic fallback (cold-start) ───────────────────────────────────────────

def _synthetic_network() -> dict[str, Any]:
    """Pre-built representative network for demo when no ingested data exists."""
    rng = random.Random(2026)
    platforms = ["twitter", "telegram", "reddit", "facebook", "instagram", "youtube"]
    plat_colors = {p: i for i, p in enumerate(platforms)}

    nodes: list[dict] = []
    for i in range(60):
        plat = platforms[i % len(platforms)]
        nid = hashlib.md5(f"node_{i}".encode()).hexdigest()[:8]
        nodes.append({
            "id": nid,
            "label": nid[:4].upper(),
            "platform": plat,
            "post_count": rng.randint(3, 80),
            "topic_count": rng.randint(1, 4),
            "dominant_sentiment": rng.choice(["positive", "neutral", "negative"]),
            "community_id": i % 5,
            "pagerank": 0.0,
            "betweenness": 0.0,
            "is_bridge": False,
        })

    edges: list[dict] = []
    id_list = [n["id"] for n in nodes]
    for _ in range(110):
        s, t = rng.sample(id_list, 2)
        edges.append({"source": s, "target": t, "weight": rng.randint(1, 5)})

    # Assign PageRank-like scores based on degree
    degree: dict[str, int] = defaultdict(int)
    for e in edges:
        degree[e["source"]] += 1
        degree[e["target"]] += 1
    max_deg = max(degree.values()) or 1
    for n in nodes:
        n["pagerank"] = round(degree.get(n["id"], 0) / max_deg, 4)
        n["is_bridge"] = n["community_id"] != (list(nodes).index(n) % 5) and degree.get(n["id"], 0) > 2

    communities = {n["id"]: n["community_id"] for n in nodes}

    return {
        "nodes": nodes,
        "edges": edges,
        "communities": _community_list(nodes, {}),
        "influencers": _top_influencers(nodes),
        "bridges": _bridge_actors(nodes),
        "stats": _graph_stats(nodes, edges, communities),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "is_synthetic": True,
    }
