"""
Analytics endpoints — centrality, communities, patterns, paths, temporal.
"""

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

    # Single shortest path
    shortest = svc.shortest_path(source, target)

    # All simple paths up to max_depth
    all_paths = svc.all_paths(source, target, max_depth=max_depth)

    return {
        "source": source,
        "target": target,
        "shortest_path": shortest,
        "all_paths": all_paths,
        "total_paths_found": len(all_paths),
    }


@router.get("/temporal")
def get_temporal(request: Request):
    """Temporal analysis — transaction anomalies."""
    svc = _svc(request)
    return svc.temporal_analysis()
