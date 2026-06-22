"""
Neo4j-backed GraphEngine — drop-in replacement for graph_engine.py.

Keeps the same public API so analytics_service, risk_scoring, and llm_service
work unchanged. Internally stores/retrieves from Neo4j, and builds a NetworkX
copy for analytics (future: can swap to GDS algorithms).

Usage in main.py:
    engine = Neo4jEngine(uri="bolt://localhost:7687", user="neo4j", password="password123")
    # OR for read-only fallback:
    engine = Neo4jEngine(uri="bolt://localhost:7687", user="neo4j", password="password123").load_from_neo4j()
"""

from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
from neo4j import GraphDatabase


class Neo4jEngine:
    """GraphEngine-compatible wrapper around a Neo4j database."""

    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "password123"):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._g: nx.DiGraph = nx.DiGraph()  # in-memory copy for analytics
        self._node_counter = 0

    def close(self):
        self._driver.close()

    # ── Helper: generate IDs ───────────────────────────────

    def _next_id(self) -> str:
        self._node_counter += 1
        return f"n-{self._node_counter}"

    # ── Node operations (Neo4j + NetworkX mirror) ─────────

    def add_node(self, node_type: str, **attrs) -> str:
        nid = self._next_id()
        attrs["id"] = nid
        attrs["type"] = node_type

        # Write to Neo4j
        labels = node_type.capitalize()
        props = ", ".join(f"{k}: ${k}" for k in attrs)
        query = f"CREATE (n:{labels} {{{props}}}) RETURN n.id AS id"
        with self._driver.session() as session:
            session.run(query, **attrs)

        # Mirror in NetworkX for analytics
        self._g.add_node(nid, **attrs)
        return nid

    def add_node_with_id(self, nid: str, node_type: str, **attrs) -> str:
        """Add a node with a pre-determined ID (used during seeding)."""
        attrs["id"] = nid
        attrs["type"] = node_type

        labels = node_type.capitalize()
        props = ", ".join(f"{k}: ${k}" for k in attrs)
        query = f"CREATE (n:{labels} {{{props}}})"
        with self._driver.session() as session:
            session.run(query, **attrs)

        self._g.add_node(nid, **attrs)
        return nid

    def get_node(self, nid: str) -> Optional[Dict[str, Any]]:
        # First check NetworkX (faster)
        if nid in self._g:
            return dict(self._g.nodes[nid])
        # Fallback to Neo4j
        with self._driver.session() as session:
            result = session.run("MATCH (n) WHERE n.id = $id RETURN n", id=nid)
            record = result.single()
            if record:
                return dict(record["n"])
        return None

    def get_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        return [dict(self._g.nodes[n]) for n in self._g.nodes
                if self._g.nodes[n].get("type") == node_type]

    @property
    def all_nodes(self) -> List[Dict[str, Any]]:
        return [dict(self._g.nodes[n]) for n in self._g.nodes]

    @property
    def node_count(self) -> int:
        return self._g.number_of_nodes()

    # ── Edge operations ─────────────────────────────────

    def add_edge(self, source: str, target: str, edge_type: str, **attrs) -> str:
        eid = f"e-{uuid.uuid4().hex[:8]}"
        attrs["id"] = eid
        attrs["type"] = edge_type

        # Write to Neo4j
        rel_type = edge_type.upper()
        props = ", ".join(f"{k}: ${k}" for k in attrs)
        query = (
            f"MATCH (a) WHERE a.id = $source "
            f"MATCH (b) WHERE b.id = $target "
            f"CREATE (a)-[r:{rel_type} {{{props}}}]->(b)"
        )
        with self._driver.session() as session:
            session.run(query, source=source, target=target, **attrs)

        # Mirror in NetworkX
        self._g.add_edge(source, target, **attrs)
        return eid

    def get_edge(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        if not self._g.has_edge(source, target):
            return None
        return dict(self._g.edges[source, target])

    def get_edges_between(self, nid_a: str, nid_b: str) -> List[Dict[str, Any]]:
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

    # ── Load entire graph from Neo4j into NetworkX ──────

    def load_from_neo4j(self) -> Neo4jEngine:
        """Rebuild the in-memory NetworkX graph from Neo4j state.
        Call this after seeding to sync."""
        self._g.clear()

        with self._driver.session() as session:
            # Load all nodes
            nodes_result = session.run("MATCH (n) RETURN n")
            for record in nodes_result:
                node = dict(record["n"])
                nid = node.pop("id", None)
                if nid:
                    self._g.add_node(nid, **node)

            # Load all edges
            edges_result = session.run("MATCH (a)-[r]->(b) RETURN a.id AS src, b.id AS tgt, r")
            for record in edges_result:
                src = record["src"]
                tgt = record["tgt"]
                rel = dict(record["r"])
                rel_id = rel.pop("id", f"e-{uuid.uuid4().hex[:8]}")
                rel_type = rel.pop("type", "unknown")
                rel["id"] = rel_id
                rel["type"] = rel_type
                self._g.add_edge(src, tgt, **rel)

        # Update counter
        max_id = 0
        for n in self._g.nodes:
            parts = n.split("-")
            if len(parts) == 2 and parts[1].isdigit():
                max_id = max(max_id, int(parts[1]))
        self._node_counter = max_id

        return self

    # ── Clear the database ──────────────────────────────

    def clear_all(self):
        """Delete all nodes and edges from Neo4j and NetworkX."""
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        self._g.clear()
        self._node_counter = 0

    # ── Export (same API as GraphEngine) ────────────────

    def to_cytoscape_json(self) -> Dict[str, List[Dict[str, Any]]]:
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

    # ── Analytics interface (same as GraphEngine) ───────

    @property
    def nx_graph(self) -> nx.DiGraph:
        return self._g

    def undirected(self) -> nx.Graph:
        return self._g.to_undirected()

    def neighbors(self, nid: str) -> List[Tuple[str, Dict[str, Any]]]:
        results = []
        for nb in self._g.neighbors(nid):
            results.append((nb, dict(self._g.nodes[nb])))
        for pred in self._g.predecessors(nid):
            if pred not in [r[0] for r in results]:
                results.append((pred, dict(self._g.nodes[pred])))
        return results
