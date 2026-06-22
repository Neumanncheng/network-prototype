"""
Analytics endpoints — centrality, communities, components, patterns, paths, bfs, dijkstra, temporal.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Query

from services.analytics_service import AnalyticsService
from services.graph_engine import GraphEngine

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _svc(req: Request) -> AnalyticsService:
    return AnalyticsService(req.app.state.engine)


@router.get("/centrality")
def get_centrality(request: Request, top_k: int = Query(0, description="Return only top-K nodes (0 = all)")):
    """Centrality scores: degree, betweenness, PageRank."""
    svc = _svc(request)
    scores = svc.centrality_scores()
    if top_k > 0:
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1].get("pagerank", 0), reverse=True)
        return {nid: sc for nid, sc in sorted_nodes[:top_k]}
    return scores


@router.get("/centrality/top")
def get_top_central(request: Request, metric: str = "pagerank", k: int = 5):
    """Top-K central nodes by metric."""
    svc = _svc(request)
    return svc.top_central_nodes(metric=metric, k=k)


@router.get("/communities")
def get_communities(request: Request):
    """Detected communities (Louvain)."""
    svc = _svc(request)
    return {"communities": svc.communities(), "count": len(svc.communities())}


@router.get("/components")
def get_components(
    request: Request,
    edge_types: Optional[str] = Query(None, description="Comma-separated edge types to filter by"),
):
    """Connected components, optionally filtered by edge types (e.g. shared_ip,shared_phone)."""
    svc = _svc(request)
    types_list = [t.strip() for t in edge_types.split(",")] if edge_types else None
    return {"components": svc.connected_components(edge_types=types_list), "count": 0}


@router.get("/components/shared-identifiers")
def get_shared_identifier_components(request: Request):
    """Groups of nodes connected by shared IPs, phones, addresses, emails, or devices."""
    svc = _svc(request)
    shared_types = ["shared_ip", "shared_phone", "shared_address", "shared_email", "shared_device"]
    result = svc.connected_components(edge_types=shared_types)
    return {"components": result, "count": len(result)}


@router.get("/patterns")
def get_patterns(request: Request):
    """Detected patterns: fan-in, fan-out, cycles."""
    svc = _svc(request)
    return svc.detect_patterns()


@router.get("/path")
def find_path(
    request: Request,
    source: str = Query(...),
    target: str = Query(...),
    max_depth: int = Query(4, description="Max path length for multi-path search"),
):
    """Find paths between two nodes."""
    svc = _svc(request)
    shortest = svc.shortest_path(source, target)
    all_paths = svc.all_paths(source, target, max_depth=max_depth)
    return {
        "source": source,
        "target": target,
        "shortest_path": shortest,
        "all_paths": all_paths,
        "total_paths_found": len(all_paths),
    }


@router.get("/path/dijkstra")
def dijkstra_path(
    request: Request,
    source: str = Query(...),
    target: str = Query(...),
):
    """Lowest-risk path between two nodes (Dijkstra with risk-weighted edges)."""
    svc = _svc(request)
    result = svc.dijkstra_risk_path(source, target)
    if result is None:
        return {"error": "No path found between these nodes"}
    return result


@router.get("/bfs")
def bfs_expand(
    request: Request,
    seed: str = Query(..., description="Seed node ID to expand from"),
    max_depth: int = Query(3, description="Max expansion depth"),
    direction: str = Query("both", description="forward, backward, or both"),
):
    """BFS expansion outward from a seed node."""
    svc = _svc(request)
    result = svc.bfs_expand(seed, max_depth=max_depth, direction=direction)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/temporal")
def get_temporal(request: Request):
    """Temporal analysis — transaction anomalies."""
    svc = _svc(request)
    return svc.temporal_analysis()
