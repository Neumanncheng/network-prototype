"""
Risk scoring endpoints — composite risk breakdown, propagation simulation.
"""

from fastapi import APIRouter, HTTPException, Request, Query

from services.risk_scoring import RiskScoringService

router = APIRouter(prefix="/api/risk", tags=["risk"])


def _svc(req: Request) -> RiskScoringService:
    return RiskScoringService(req.app.state.engine)


# Concrete paths FIRST (before the /{node_id} catch-all)
@router.get("/propagate")
def propagate_risk(
    request: Request,
    from_id: str = Query(...),
    depth: int = Query(3, description="Max propagation depth"),
):
    """Simulate risk propagation outward from a node."""
    svc = _svc(request)
    return svc.risk_propagation(from_id, depth=depth)


@router.get("/llm/explain/{node_id}")
def llm_explain_node(node_id: str, request: Request):
    """LLM-generated narrative explanation of a node."""
    from services.llm_service import LLMService
    svc = LLMService(request.app.state.engine)
    result = svc.explain_node(node_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/llm/explain-path")
def llm_explain_path(
    request: Request,
    source: str = Query(...),
    target: str = Query(...),
):
    """LLM explanation of a connection path."""
    from services.analytics_service import AnalyticsService
    from services.llm_service import LLMService

    eng = request.app.state.engine
    analytics = AnalyticsService(eng)
    path_data = analytics.shortest_path(source, target)

    svc = LLMService(eng)
    narrative = svc.explain_path(source, target, path_data or {})

    return {
        "source": source,
        "target": target,
        "narrative": narrative,
        "path_found": path_data is not None,
    }


# Catch-all node ID route must be last
@router.get("/{node_id}")
def get_risk_breakdown(node_id: str, request: Request):
    """Composite risk score with 5-component breakdown."""
    svc = _svc(request)
    result = svc.compute_risk_breakdown(node_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    return result
