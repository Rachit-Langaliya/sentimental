"""
Network Analysis API — Phase 6.
Exposes graph data for the frontend force-directed visualisation.
"""
from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DB

router = APIRouter()


@router.get("/graph")
async def get_network_graph(
    current_user: CurrentUser,
    db: DB,
    days: int = Query(default=7, ge=1, le=30),
):
    """
    Return the full interaction graph (nodes, edges, communities, influencers, bridges).
    Expensive — results are suitable for client-side caching (ETag or short TTL).
    """
    from app.services.network_analyzer import build_network
    return await build_network(db, days=days)


@router.get("/influencers")
async def get_influencers(
    current_user: CurrentUser,
    db: DB,
    days: int = Query(default=7, ge=1, le=30),
    top: int = Query(default=10, ge=1, le=50),
):
    """Top-N authors by PageRank (cross-platform influence)."""
    from app.services.network_analyzer import build_network
    result = await build_network(db, days=days)
    return {"items": result["influencers"][:top], "stats": result["stats"]}


@router.get("/communities")
async def get_communities(
    current_user: CurrentUser,
    db: DB,
    days: int = Query(default=7, ge=1, le=30),
):
    """Detected communities with platform breakdown and cohesion score."""
    from app.services.network_analyzer import build_network
    result = await build_network(db, days=days)
    return {"items": result["communities"], "stats": result["stats"]}


@router.get("/bridges")
async def get_bridge_actors(
    current_user: CurrentUser,
    db: DB,
    days: int = Query(default=7, ge=1, le=30),
):
    """High-betweenness nodes that connect otherwise separate communities."""
    from app.services.network_analyzer import build_network
    result = await build_network(db, days=days)
    return {"items": result["bridges"], "stats": result["stats"]}
