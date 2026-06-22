"""
Risk scoring engine — computes composite risk score from 5 weighted components:

  Centrality(20%) + Community Risk(30%) + Pattern Risk(25%)
  + Temporal Risk(15%) + Propagated Risk(10%)

Each sub-score is 0-100. The composite is a weighted sum, also 0-100.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

import networkx as nx

from .graph_engine import GraphEngine
from .analytics_service import AnalyticsService

# ── Weight configuration (matches the diagram) ───────────────────
WEIGHTS = {
    "centrality": 0.20,
    "community": 0.30,
    "pattern": 0.25,
    "temporal": 0.15,
    "propagated": 0.10,
}


class RiskScoringService:
    """Computes per-node and propagated risk scores."""

    def __init__(self, engine: GraphEngine):
        self._engine = engine
        self._analytics = AnalyticsService(engine)

    # ── Individual component scoring ────────────────────────────

    def _centrality_subscore(self, nid: str) -> float:
        """How central is this node? Higher = riskier."""
        scores = self._analytics.centrality_scores()
        if nid not in scores:
            return 0.0
        # Average the three centrality metrics, cap at 100
        s = scores[nid]
        return min(100.0, round((s["degree"] + s["betweenness"] + s["pagerank"]) / 3, 1))

    def _community_subscore(self, nid: str) -> float:
        """Risk from being in a high-risk community."""
        communities = self._analytics.communities()
        for comm in communities:
            for member in comm["members"]:
                if member["id"] == nid:
                    return min(100.0, comm["avg_risk_score"])
        return 0.0

    def _pattern_subscore(self, nid: str) -> float:
        """Risk contributed by patterns this node participates in."""
        patterns = self._analytics.detect_patterns()
        score = 0.0

        # Check fan-out
        for fo in patterns["fan_out"]:
            if fo["node_id"] == nid:
                score += 25.0

        # Check fan-in
        for fi in patterns["fan_in"]:
            if fi["node_id"] == nid:
                score += 20.0

        # Check if node appears in any cycle
        for cycle in patterns["cycles"]:
            for node in cycle["nodes"]:
                if node["id"] == nid:
                    score += 30.0
                    break

        return min(100.0, score)

    def _temporal_subscore(self, nid: str) -> float:
        """Risk from temporal anomalies involving this node."""
        temporal = self._analytics.temporal_analysis()
        score = 0.0

        for anomaly in temporal.get("anomalies", []):
            if anomaly.get("node_id") == nid:
                score += 35.0
            # Also check if node appears in anomalous month (as source/target)
        return min(100.0, score)

    def _propagated_subscore(self, nid: str) -> float:
        """Risk propagated from high-risk neighbors."""
        g = self._engine.nx_graph
        if nid not in g:
            return 0.0

        base_risk = g.nodes[nid].get("risk_score", 0) or 0
        # BFS up to depth 2, decaying by 0.5 per hop
        score = 0.0
        visited = {nid}

        # 1-hop neighbors
        for nb in g.neighbors(nid):
            if nb not in visited:
                visited.add(nb)
                nb_risk = g.nodes[nb].get("risk_score", 0) or 0
                score += nb_risk * 0.5

        # Predecessors (reverse edges)
        for pred in g.predecessors(nid):
            if pred not in visited:
                visited.add(pred)
                pred_risk = g.nodes[pred].get("risk_score", 0) or 0
                score += pred_risk * 0.5

        return min(100.0, round(score / 2, 1))  # normalize

    # ── Composite score for a single node ───────────────────────

    def compute_risk_breakdown(self, nid: str) -> Optional[Dict[str, Any]]:
        """Return component scores + weighted composite for one node."""
        node = self._engine.get_node(nid)
        if node is None:
            return None

        centrality = self._centrality_subscore(nid)
        community = self._community_subscore(nid)
        pattern = self._pattern_subscore(nid)
        temporal = self._temporal_subscore(nid)
        propagated = self._propagated_subscore(nid)

        composite = round(
            centrality * WEIGHTS["centrality"]
            + community * WEIGHTS["community"]
            + pattern * WEIGHTS["pattern"]
            + temporal * WEIGHTS["temporal"]
            + propagated * WEIGHTS["propagated"],
            1,
        )

        return {
            "node_id": nid,
            "label": node.get("label", nid),
            "type": node.get("type", "unknown"),
            "composite_score": composite,
            "components": {
                "centrality": {"score": centrality, "weight": WEIGHTS["centrality"], "contribution": round(centrality * WEIGHTS["centrality"], 1)},
                "community": {"score": community, "weight": WEIGHTS["community"], "contribution": round(community * WEIGHTS["community"], 1)},
                "pattern": {"score": pattern, "weight": WEIGHTS["pattern"], "contribution": round(pattern * WEIGHTS["pattern"], 1)},
                "temporal": {"score": temporal, "weight": WEIGHTS["temporal"], "contribution": round(temporal * WEIGHTS["temporal"], 1)},
                "propagated": {"score": propagated, "weight": WEIGHTS["propagated"], "contribution": round(propagated * WEIGHTS["propagated"], 1)},
            },
            "weights": WEIGHTS,
        }

    # ── Risk propagation simulation ─────────────────────────────

    def risk_propagation(self, from_id: str, depth: int = 3) -> Dict[str, Any]:
        """
        Simulate risk spreading outward from `from_id`.
        Each hop decays risk by factor 0.5.
        Returns list of affected nodes with propagated risk.
        """
        g = self._engine.nx_graph
        if from_id not in g:
            return {"error": f"Node {from_id} not found"}

        source_attrs = self._engine.get_node(from_id) or {}
        source_risk = source_attrs.get("risk_score", 50) or 50

        # BFS
        visited = {from_id: 0}
        queue = [(from_id, 0)]
        propagation = []

        while queue:
            current, d = queue.pop(0)
            if d >= depth:
                continue

            for neighbor in g.neighbors(current):
                new_d = d + 1
                if neighbor not in visited or visited[neighbor] > new_d:
                    visited[neighbor] = new_d
                    queue.append((neighbor, new_d))

            # Also check predecessors (undirected propagation)
            for pred in g.predecessors(current):
                new_d = d + 1
                if pred not in visited or visited[pred] > new_d:
                    visited[pred] = new_d
                    queue.append((pred, new_d))

        # Build result (skip source node itself)
        for nid, d in visited.items():
            if nid == from_id:
                continue
            attrs = self._engine.get_node(nid) or {}
            factor = 0.5 ** d
            propagated = round(source_risk * factor, 1)
            propagation.append({
                "node_id": nid,
                "label": attrs.get("label", nid),
                "type": attrs.get("type", "unknown"),
                "hops": d,
                "decay_factor": factor,
                "propagated_risk": propagated,
                "original_risk": attrs.get("risk_score", 0),
            })

        propagation.sort(key=lambda x: x["hops"])

        return {
            "source_id": from_id,
            "source_label": source_attrs.get("label", from_id),
            "source_risk": source_risk,
            "max_depth": depth,
            "propagation": propagation,
            "affected_count": len(propagation),
        }
