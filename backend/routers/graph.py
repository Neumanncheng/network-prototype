"""
Graph data endpoints — return nodes, edges, neighborhoods.
"""

from fastapi import APIRouter, HTTPException, Request

from services.graph_engine import GraphEngine

router = APIRouter(prefix="/api", tags=["graph"])


def _engine(req: Request) -> GraphEngine:
    return req.app.state.engine


@router.get("/graph")
def get_graph(request: Request):
    """Full graph in Cytoscape.js format."""
    eng = _engine(request)
    return eng.to_cytoscape_json()


@router.get("/stats")
def get_stats(request: Request):
    """Overview statistics."""
    from services.analytics_service import AnalyticsService
    eng = _engine(request)
    svc = AnalyticsService(eng)
    return svc.summary_stats()


@router.get("/graph/node/{node_id}")
def get_node(node_id: str, request: Request):
    """Single node attributes."""
    eng = _engine(request)
    node = eng.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    return node


@router.get("/graph/node/{node_id}/neighborhood")
def get_neighborhood(node_id: str, request: Request, depth: int = 1):
    """Node + its neighbors up to `depth` hops."""
    eng = _engine(request)
    if eng.get_node(node_id) is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    sub_nodes = {}
    sub_edges = []
    visited = {node_id}

    # BFS
    queue = [(node_id, 0)]
    while queue:
        current, d = queue.pop(0)
        current_attrs = eng.get_node(current)
        if current_attrs:
            sub_nodes[current] = current_attrs

        if d >= depth:
            continue

        for nb, _ in eng.neighbors(current):
            if nb not in visited:
                visited.add(nb)
                queue.append((nb, d + 1))
            # Add edge
            edges = eng.get_edges_between(current, nb)
            for _, s, t, e_data in edges:
                sub_edges.append({
                    "group": "edges",
                    "data": {**e_data, "source": s, "target": t},
                })

    return {
        "nodes": [{"group": "nodes", "data": data} for nid, data in sub_nodes.items()],
        "edges": sub_edges,
    }


@router.get("/graph/nodes")
def list_nodes(request: Request, type: str = None):
    """List all nodes, optionally filtered by type."""
    eng = _engine(request)
    if type:
        return eng.get_nodes_by_type(type)
    return eng.all_nodes


@router.get("/graph/edges")
def list_edges(request: Request):
    """List all edges."""
    eng = _engine(request)
    return eng.all_edges
