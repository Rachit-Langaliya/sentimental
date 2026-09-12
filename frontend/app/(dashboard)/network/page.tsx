"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Network, Users, Share2, GitFork, Activity, RefreshCw } from "lucide-react";
import { networkApi, type NetworkGraph, type NetworkNode, type NetworkInfluencer, type NetworkBridge, type NetworkCommunity } from "@/lib/api";
import { fmtNumber, fmtPct, sentimentColor } from "@/lib/utils";
import { cn } from "@/lib/utils";

// ── Colour palette (community + platform) ─────────────────────────────────────
const COMMUNITY_COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
  "#8B5CF6", "#EC4899", "#14B8A6", "#F97316",
];
const PLATFORM_COLORS: Record<string, string> = {
  twitter: "#1DA1F2", telegram: "#2CA5E0", instagram: "#E1306C",
  reddit: "#FF4500", youtube: "#FF0000", facebook: "#1877F2",
};

function communityColor(id: number) {
  return COMMUNITY_COLORS[id % COMMUNITY_COLORS.length];
}
function platformColor(platform: string) {
  return PLATFORM_COLORS[platform] ?? "#64748B";
}
function sentimentFill(s: string) {
  return s === "positive" ? "#10B981" : s === "negative" ? "#EF4444" : "#64748B";
}

// ── Force-directed layout ─────────────────────────────────────────────────────
interface FNode extends NetworkNode {
  x: number; y: number; vx: number; vy: number;
}

function initLayout(nodes: NetworkNode[], w: number, h: number): FNode[] {
  const rng = (i: number) => ((i * 2654435761) >>> 0) / 0xFFFFFFFF;
  return nodes.map((n, i) => ({
    ...n,
    x: w * 0.15 + rng(i * 3) * w * 0.7,
    y: h * 0.15 + rng(i * 3 + 1) * h * 0.7,
    vx: 0, vy: 0,
  }));
}

function runTick(
  fnodes: FNode[],
  edges: { source: string; target: string; weight: number }[],
  w: number,
  h: number,
  alpha: number,
): void {
  const idxMap: Record<string, number> = {};
  fnodes.forEach((n, i) => { idxMap[n.id] = i; });

  const k = Math.sqrt((w * h) / Math.max(fnodes.length, 1));

  // Repulsion (Barnes–Hut approximated as O(n²) for ≤120 nodes)
  for (let i = 0; i < fnodes.length; i++) {
    let fx = 0, fy = 0;
    for (let j = 0; j < fnodes.length; j++) {
      if (i === j) continue;
      const dx = fnodes[i].x - fnodes[j].x;
      const dy = fnodes[i].y - fnodes[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const force = (k * k) / dist * alpha * 0.8;
      fx += (dx / dist) * force;
      fy += (dy / dist) * force;
    }
    fnodes[i].vx += fx;
    fnodes[i].vy += fy;
  }

  // Attraction (spring along edges)
  for (const e of edges) {
    const si = idxMap[e.source], ti = idxMap[e.target];
    if (si == null || ti == null) continue;
    const dx = fnodes[ti].x - fnodes[si].x;
    const dy = fnodes[ti].y - fnodes[si].y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
    const force = (dist - k) / dist * alpha * 0.35 * Math.log1p(e.weight);
    fnodes[si].vx += (dx / dist) * force;
    fnodes[si].vy += (dy / dist) * force;
    fnodes[ti].vx -= (dx / dist) * force;
    fnodes[ti].vy -= (dy / dist) * force;
  }

  // Gravity toward centre
  const cx = w / 2, cy = h / 2;
  for (const n of fnodes) {
    n.vx += (cx - n.x) * 0.008 * alpha;
    n.vy += (cy - n.y) * 0.008 * alpha;
  }

  // Apply velocity + damping + bounds
  const damping = 0.88;
  for (const n of fnodes) {
    n.vx *= damping;
    n.vy *= damping;
    n.x = Math.max(12, Math.min(w - 12, n.x + n.vx));
    n.y = Math.max(12, Math.min(h - 12, n.y + n.vy));
  }
}

// ── Graph canvas ──────────────────────────────────────────────────────────────
function GraphCanvas({ graph, colorBy }: {
  graph: NetworkGraph;
  colorBy: "community" | "platform" | "sentiment";
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [fnodes, setFnodes] = useState<FNode[]>([]);
  const [hovered, setHovered] = useState<string | null>(null);
  const [selected, setSelected] = useState<FNode | null>(null);
  const rafRef = useRef<number>(0);
  const alphaRef = useRef(1.0);
  const fnodesRef = useRef<FNode[]>([]);
  const W = 700, H = 480;

  useEffect(() => {
    const initial = initLayout(graph.nodes, W, H);
    fnodesRef.current = initial;
    setFnodes([...initial]);
    alphaRef.current = 1.0;

    let tick = 0;
    function animate() {
      if (alphaRef.current < 0.01) return;
      runTick(fnodesRef.current, graph.edges, W, H, alphaRef.current);
      alphaRef.current *= 0.97;
      tick++;
      if (tick % 3 === 0) setFnodes([...fnodesRef.current]);
      rafRef.current = requestAnimationFrame(animate);
    }
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [graph]);

  function nodeColor(n: FNode) {
    if (colorBy === "community") return communityColor(n.community_id);
    if (colorBy === "platform") return platformColor(n.platform);
    return sentimentFill(n.dominant_sentiment);
  }
  function nodeRadius(n: FNode) {
    return 4 + Math.sqrt(n.post_count) * 0.9 + n.pagerank * 12;
  }

  const idxMap: Record<string, FNode> = {};
  fnodes.forEach(n => { idxMap[n.id] = n; });

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full rounded-xl border border-bdr bg-bg"
        style={{ maxHeight: 480 }}
      >
        {/* Edges */}
        <g opacity={0.35}>
          {graph.edges.map((e, i) => {
            const s = idxMap[e.source], t = idxMap[e.target];
            if (!s || !t) return null;
            return (
              <line
                key={i}
                x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                stroke="#334155"
                strokeWidth={Math.min(e.weight * 0.6, 2.5)}
              />
            );
          })}
        </g>

        {/* Nodes */}
        {fnodes.map((n) => {
          const r = nodeRadius(n);
          const color = nodeColor(n);
          const isHov = hovered === n.id;
          const isSel = selected?.id === n.id;
          return (
            <g
              key={n.id}
              transform={`translate(${n.x},${n.y})`}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHovered(n.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => setSelected(isSel ? null : n)}
            >
              {n.is_bridge && (
                <circle r={r + 4} fill="none" stroke="#F59E0B" strokeWidth={1.5} strokeDasharray="3 2" />
              )}
              <circle
                r={isSel ? r + 2 : r}
                fill={color}
                fillOpacity={isHov || isSel ? 1 : 0.82}
                stroke={isSel ? "#fff" : "none"}
                strokeWidth={1.5}
              />
              {r > 8 && (
                <text
                  textAnchor="middle"
                  dy="0.35em"
                  fontSize={Math.min(r * 0.75, 9)}
                  fill="#fff"
                  fontWeight="600"
                  style={{ pointerEvents: "none", userSelect: "none" }}
                >
                  {n.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Hover / select tooltip */}
      {(hovered || selected) && (() => {
        const n = selected || fnodes.find(fn => fn.id === hovered);
        if (!n) return null;
        return (
          <div className="absolute top-3 right-3 bg-surface border border-bdr rounded-xl p-3 text-xs space-y-1 min-w-36 shadow-lg pointer-events-none">
            <p className="font-bold text-ink">{n.label}</p>
            <p className="text-ink-3">{n.platform}</p>
            <p className="text-ink-2">Posts: <span className="font-semibold">{n.post_count}</span></p>
            <p className="text-ink-2">PageRank: <span className="font-semibold">{n.pagerank.toFixed(4)}</span></p>
            <p className="text-ink-2">Community: <span className="font-semibold">{n.community_id + 1}</span></p>
            {n.is_bridge && <p className="text-warning font-semibold">⚡ Bridge actor</p>}
            <p className={cn("capitalize font-semibold", sentimentColor(n.dominant_sentiment))}>{n.dominant_sentiment}</p>
          </div>
        );
      })()}
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
type Tab = "graph" | "influencers" | "communities" | "bridges";

function StatChip({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-bg border border-bdr rounded-lg px-3 py-2 text-center">
      <p className="text-base font-bold tabular-nums text-ink">{value}</p>
      <p className="text-[10px] text-ink-3 mt-0.5">{label}</p>
    </div>
  );
}

export default function NetworkPage() {
  const [graph, setGraph] = useState<NetworkGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("graph");
  const [colorBy, setColorBy] = useState<"community" | "platform" | "sentiment">("community");
  const [days, setDays] = useState(7);

  const load = useCallback((d: number) => {
    setLoading(true);
    networkApi.graph(d)
      .then(r => { setGraph(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => { load(days); }, [days, load]);

  const stats = graph?.stats;

  return (
    <div className="p-6 space-y-5 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-ink">Network Analysis</h1>
          <p className="text-sm text-ink-2 mt-0.5">Influence propagation, community detection, bridge actors</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            className="text-xs bg-bg border border-bdr rounded-lg px-2 py-1.5 text-ink focus:outline-none"
          >
            {[1, 3, 7, 14, 30].map(d => <option key={d} value={d}>Last {d}d</option>)}
          </select>
          <button
            onClick={() => load(days)}
            disabled={loading}
            className="p-1.5 rounded-lg border border-bdr hover:bg-surface text-ink-3 hover:text-ink transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* Stat chips */}
      {stats && (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
          <StatChip label="Nodes" value={fmtNumber(stats.node_count)} />
          <StatChip label="Edges" value={fmtNumber(stats.edge_count)} />
          <StatChip label="Communities" value={stats.community_count} />
          <StatChip label="Avg Degree" value={stats.avg_degree.toFixed(1)} />
          <StatChip label="Density" value={stats.density.toFixed(4)} />
          <StatChip label="Bridges" value={stats.bridge_count} />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-bg border border-bdr rounded-xl p-1 w-fit">
        {([
          ["graph", Network, "Graph"],
          ["influencers", Activity, "Influencers"],
          ["communities", Users, "Communities"],
          ["bridges", GitFork, "Bridges"],
        ] as [Tab, any, string][]).map(([t, Icon, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors",
              tab === t ? "bg-accent text-white" : "text-ink-3 hover:text-ink"
            )}
          >
            <Icon className="w-3.5 h-3.5" />{label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : !graph ? (
        <div className="text-center py-20 text-ink-3">Failed to load network data</div>
      ) : (
        <>
          {/* Graph tab */}
          {tab === "graph" && (
            <div className="space-y-3">
              {graph.is_synthetic && (
                <div className="flex items-center gap-2 text-xs text-warning bg-warning/10 border border-warning/20 rounded-lg px-3 py-2">
                  <Share2 className="w-3.5 h-3.5 flex-shrink-0" />
                  Showing synthetic demo graph — run an ingestion cycle to see real interaction data
                </div>
              )}

              {/* Color-by control */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-ink-3 uppercase tracking-widest">Color by:</span>
                {(["community", "platform", "sentiment"] as const).map((c) => (
                  <button
                    key={c}
                    onClick={() => setColorBy(c)}
                    className={cn(
                      "text-[11px] px-2.5 py-1 rounded-full border transition-colors capitalize",
                      colorBy === c
                        ? "bg-accent text-white border-accent"
                        : "border-bdr text-ink-3 hover:text-ink"
                    )}
                  >
                    {c}
                  </button>
                ))}
              </div>

              <GraphCanvas graph={graph} colorBy={colorBy} />

              {/* Legend */}
              <div className="flex flex-wrap gap-3">
                {colorBy === "community" && graph.communities.slice(0, 8).map((c) => (
                  <div key={c.id} className="flex items-center gap-1.5 text-[10px] text-ink-3">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: communityColor(c.id) }} />
                    {c.name}
                  </div>
                ))}
                {colorBy === "platform" && Object.entries(PLATFORM_COLORS).map(([p, c]) => (
                  <div key={p} className="flex items-center gap-1.5 text-[10px] text-ink-3">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: c }} />
                    {p}
                  </div>
                ))}
                {colorBy === "sentiment" && [["positive","#10B981"],["neutral","#64748B"],["negative","#EF4444"]].map(([s,c]) => (
                  <div key={s} className="flex items-center gap-1.5 text-[10px] text-ink-3">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: c }} />
                    {s}
                  </div>
                ))}
                <div className="flex items-center gap-1.5 text-[10px] text-warning">
                  <span className="w-2.5 h-2.5 rounded-full border border-warning flex-shrink-0" />
                  Bridge actor (dashed ring)
                </div>
              </div>
            </div>
          )}

          {/* Influencers tab */}
          {tab === "influencers" && (
            <div className="bg-surface border border-bdr rounded-xl overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-bdr text-ink-3 uppercase tracking-wide">
                    {["#","Author","Platform","PageRank","Posts","Community","Sentiment"].map(h => (
                      <th key={h} className="px-4 py-3 text-left font-semibold">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {graph.influencers.map((inf: NetworkInfluencer) => (
                    <tr key={inf.rank} className="border-b border-bdr hover:bg-surface-2 transition-colors">
                      <td className="px-4 py-3 font-bold text-ink-3">#{inf.rank}</td>
                      <td className="px-4 py-3 font-mono font-semibold text-ink">{inf.label}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium text-white"
                          style={{ background: platformColor(inf.platform) }}>
                          {inf.platform}
                        </span>
                      </td>
                      <td className="px-4 py-3 tabular-nums text-ink">{inf.pagerank.toFixed(4)}</td>
                      <td className="px-4 py-3 tabular-nums text-ink">{fmtNumber(inf.post_count)}</td>
                      <td className="px-4 py-3">
                        <span className="px-1.5 py-0.5 rounded text-[10px]"
                          style={{ background: communityColor(inf.community_id) + "30", color: communityColor(inf.community_id) }}>
                          C{inf.community_id + 1}
                        </span>
                      </td>
                      <td className={cn("px-4 py-3 capitalize font-semibold", sentimentColor(inf.dominant_sentiment))}>
                        {inf.dominant_sentiment}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Communities tab */}
          {tab === "communities" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {graph.communities.map((c: NetworkCommunity) => (
                <div key={c.id} className="bg-surface border border-bdr rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: communityColor(c.id) }} />
                    <p className="text-sm font-semibold text-ink">{c.name}</p>
                    <span className="ml-auto text-xs font-bold tabular-nums text-ink">{c.size} nodes</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(c.platform_breakdown).map(([p, cnt]) => (
                      <span key={p} className="text-[10px] px-2 py-0.5 rounded-full font-medium text-white"
                        style={{ background: platformColor(p) }}>
                        {p} {cnt}
                      </span>
                    ))}
                  </div>
                  <p className="text-[11px] text-ink-3">
                    Avg PageRank: <span className="text-ink font-semibold">{c.avg_pagerank.toFixed(4)}</span>
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Bridges tab */}
          {tab === "bridges" && (
            <div className="space-y-2">
              <p className="text-xs text-ink-3 leading-relaxed max-w-xl">
                Bridge actors have high betweenness centrality — they sit on the shortest paths between communities and act as information conduits. Monitoring them can reveal cross-community narrative diffusion early.
              </p>
              {graph.bridges.length === 0 ? (
                <div className="text-center py-12 text-ink-3 text-sm">No clear bridge actors detected in this window</div>
              ) : (
                <div className="bg-surface border border-bdr rounded-xl overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-bdr text-ink-3 uppercase tracking-wide">
                        {["Author","Platform","Betweenness","Posts","Community"].map(h => (
                          <th key={h} className="px-4 py-3 text-left font-semibold">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {graph.bridges.map((b: NetworkBridge, i) => (
                        <tr key={i} className="border-b border-bdr hover:bg-surface-2 transition-colors">
                          <td className="px-4 py-3 font-mono font-semibold text-warning">{b.label}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium text-white"
                              style={{ background: platformColor(b.platform) }}>
                              {b.platform}
                            </span>
                          </td>
                          <td className="px-4 py-3 tabular-nums text-ink">{b.betweenness.toFixed(4)}</td>
                          <td className="px-4 py-3 tabular-nums text-ink">{fmtNumber(b.post_count)}</td>
                          <td className="px-4 py-3">
                            <span className="px-1.5 py-0.5 rounded text-[10px]"
                              style={{ background: communityColor(b.community_id) + "30", color: communityColor(b.community_id) }}>
                              C{b.community_id + 1}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
