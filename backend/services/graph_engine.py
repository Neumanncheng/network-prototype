"""
NetworkX-based graph engine — in-memory graph with typed nodes and edges.

Provides the underlying data store used by all analytics and routing layers.
Designed so a Neo4j adapter can be swapped in later without changing the API.
"""

from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx


class GraphEngine:
    """Wraps a NetworkX DiGraph with typed node/edge helpers."""

    # ── Edge type categories (for styling / filtering) ──────────
    FINANCIAL_EDGES = {"transaction", "ownership"}
    SHARED_ATTR_EDGES = {"shared_address", "shared_phone", "shared_email", "shared_ip", "shared_device"}
    LLM_EDGES = {"llm_discovered"}

    def __init__(self):
        self._g: nx.DiGraph = nx.DiGraph()
        self._node_counter = 0

    # ── Node operations ─────────────────────────────────────────

    def _next_id(self) -> str:
        self._node_counter += 1
        return f"n-{self._node_counter}"

    def add_node(self, node_type: str, **attrs) -> str:
        """Add a typed node. Returns its string ID."""
        nid = self._next_id()
        attrs["id"] = nid
        attrs["type"] = node_type
        self._g.add_node(nid, **attrs)
        return nid

    def get_node(self, nid: str) -> Optional[Dict[str, Any]]:
        if nid not in self._g:
            return None
        attrs = dict(self._g.nodes[nid])
        return attrs

    def get_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        return [dict(self._g.nodes[n]) for n in self._g.nodes
                if self._g.nodes[n].get("type") == node_type]

    @property
    def all_nodes(self) -> List[Dict[str, Any]]:
        return [dict(self._g.nodes[n]) for n in self._g.nodes]

    @property
    def node_count(self) -> int:
        return self._g.number_of_nodes()

    # ── Edge operations ─────────────────────────────────────────

    def add_edge(self, source: str, target: str, edge_type: str, **attrs) -> str:
        """Add a typed, directed edge. Returns its ID."""
        eid = f"e-{uuid.uuid4().hex[:8]}"
        attrs["id"] = eid
        attrs["type"] = edge_type
        self._g.add_edge(source, target, **attrs)
        return eid

    def get_edge(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        if not self._g.has_edge(source, target):
            return None
        return dict(self._g.edges[source, target])

    def get_edges_between(self, nid_a: str, nid_b: str) -> List[Dict[str, Any]]:
        """Return all edges (both directions) bridging two nodes."""
        edges = []
        if self._g.has_edge(nid_a, nid_b):
            edges.append(("directed", nid_a, nid_b, dict(self._g.edges[nid_a, nid_b])))
        if self._g.has_edge(nid_b, nid_a):
            edges.append(("directed", nid_b, nid_a, dict(self._g.edges[nid_b, nid_a])))
        return edges

    @property
    def all_edges(self) -> List[Dict[str, Any]]:
        result = []
        for u, v, d in self._g.edges(data=True):
            e = dict(d)
            e["source"] = u
            e["target"] = v
            result.append(e)
        return result

    @property
    def edge_count(self) -> int:
        return self._g.number_of_edges()

    # ── Export ──────────────────────────────────────────────────

    def to_cytoscape_json(self) -> Dict[str, List[Dict[str, Any]]]:
        """Produce {nodes: [...], edges: [...]} for the front-end."""
        nodes = []
        for nid in self._g.nodes:
            data = dict(self._g.nodes[nid])
            data["id"] = nid
            nodes.append({"group": "nodes", "data": data})

        edges = []
        for u, v, d in self._g.edges(data=True):
            data = dict(d)
            data["id"] = data.get("id", f"e-{u}-{v}")
            data["source"] = u
            data["target"] = v
            edges.append({"group": "edges", "data": data})

        return {"nodes": nodes, "edges": edges}

    # ── Convenience properties for analytics ────────────────────

    @property
    def nx_graph(self) -> nx.DiGraph:
        return self._g

    def undirected(self) -> nx.Graph:
        """Return an undirected view (faster for community detection, etc.)."""
        return self._g.to_undirected()

    def neighbors(self, nid: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Return (neighbor_id, node_attrs) for all 1-hop neighbors."""
        results = []
        for nb in self._g.neighbors(nid):
            results.append((nb, dict(self._g.nodes[nb])))
        # Also consider reverse edges (predecessors)
        for pred in self._g.predecessors(nid):
            if pred not in [r[0] for r in results]:
                results.append((pred, dict(self._g.nodes[pred])))
        return results
