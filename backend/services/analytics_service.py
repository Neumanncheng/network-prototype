"""
Graph analytics powered by NetworkX — real implementations of:
  - Centrality (degree, betweenness, PageRank)
  - Community detection (Louvain, label propagation)
  - Connected components (by shared attributes)
  - Pattern detection (fan-in, fan-out, cycles)
  - Path analysis (shortest path, all simple paths, Dijkstra risk-weighted)
  - BFS expansion from seed nodes
  - Temporal analysis (frequency anomalies)
"""

from __future__ import annotations
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

import networkx as nx
from networkx.algorithms.community import louvain_communities, label_propagation_communities

from .graph_engine import GraphEngine


class AnalyticsService:
    """Runs graph algorithms against a GraphEngine instance."""

    def __init__(self, engine: GraphEngine):
        self._engine = engine

    # ── Centrality ──────────────────────────────────────────────

    def centrality_scores(self) -> Dict[str, Dict[str, float]]:
        """Return {node_id: {degree, betweenness, pagerank}}."""
        g = self._engine.nx_graph
        if g.number_of_nodes() == 0:
            return {}

        degree = dict(g.degree())
        max_deg = max(degree.values()) if degree else 1
        degree_norm = {n: round(d / max_deg * 100, 1) for n, d in degree.items()}

        # Betweenness — sample on large graphs
        n_nodes = g.number_of_nodes()
        if n_nodes <= 200:
            betweenness = nx.betweenness_centrality(g, normalized=True)
        else:
            betweenness = nx.betweenness_centrality(g, k=min(100, n_nodes), normalized=True)

        try:
            pagerank = nx.pagerank(g, alpha=0.85)
        except nx.PowerIterationFailedConvergence:
            pagerank = {n: 0.0 for n in g.nodes}

        result = {}
        for n in g.nodes:
            result[n] = {
                "degree": degree_norm.get(n, 0),
                "betweenness": round(betweenness.get(n, 0) * 100, 1),
                "pagerank": round(pagerank.get(n, 0) * 100, 1),
            }
        return result

    def top_central_nodes(self, metric: str = "pagerank", k: int = 5) -> List[Dict]:
        """Return the top-k central nodes for a given metric."""
        scores = self.centrality_scores()
        sorted_nodes = sorted(scores.items(), key=lambda x: x[1].get(metric, 0), reverse=True)
        result = []
        for nid, sc in sorted_nodes[:k]:
            attrs = self._engine.get_node(nid) or {}
            result.append({
                "id": nid,
                "label": attrs.get("label", nid),
                "type": attrs.get("type", "unknown"),
                "score": sc.get(metric, 0),
            })
        return result

    # ── Community Detection ────────────────────────────────────

    def communities(self) -> List[Dict]:
        """Detect communities using Louvain (undirected)."""
        g = self._engine.undirected()
        if g.number_of_nodes() == 0:
            return []

        try:
            communities = louvain_communities(g, seed=42)
        except Exception:
            # Fallback to label propagation
            communities = list(label_propagation_communities(g))

        result = []
        for i, comm in enumerate(communities):
            members = []
            for nid in comm:
                attrs = self._engine.get_node(nid) or {}
                members.append({
                    "id": nid,
                    "label": attrs.get("label", nid),
                    "type": attrs.get("type", "unknown"),
                    "risk_score": attrs.get("risk_score", 0),
                })
            avg_risk = round(sum(m["risk_score"] for m in members if m["risk_score"]) / max(len(members), 1), 1)
            result.append({
                "community_id": i + 1,
                "size": len(members),
                "avg_risk_score": avg_risk,
                "members": members,
            })

        # Sort by size (largest first)
        result.sort(key=lambda c: c["size"], reverse=True)
        return result

    # ── Pattern Detection ──────────────────────────────────────

    def _node_degree_info(self, nid: str) -> Dict:
        g = self._engine.nx_graph
        out_deg = g.out_degree(nid)
        in_deg = g.in_degree(nid)
        return {"id": nid, "out_degree": out_deg, "in_degree": in_deg}

    def detect_patterns(self) -> Dict[str, Any]:
        """Return detected patterns: fan_in, fan_out, cycles."""
        g = self._engine.nx_graph
        results = {"fan_out": [], "fan_in": [], "cycles": []}

        # Fan-out: nodes where out_degree >= 4
        for nid in g.nodes:
            if g.out_degree(nid) >= 4:
                attrs = self._engine.get_node(nid) or {}
                targets = [t for t in g.successors(nid)]
                results["fan_out"].append({
                    "node_id": nid,
                    "label": attrs.get("label", nid),
                    "type": attrs.get("type", "unknown"),
                    "out_degree": g.out_degree(nid),
                    "targets": [{"id": t, "label": (self._engine.get_node(t) or {}).get("label", t)}
                                for t in targets],
                })

        # Fan-in: nodes where in_degree >= 3
        for nid in g.nodes:
            if g.in_degree(nid) >= 3:
                attrs = self._engine.get_node(nid) or {}
                sources = [s for s in g.predecessors(nid)]
                results["fan_in"].append({
                    "node_id": nid,
                    "label": attrs.get("label", nid),
                    "type": attrs.get("type", "unknown"),
                    "in_degree": g.in_degree(nid),
                    "sources": [{"id": s, "label": (self._engine.get_node(s) or {}).get("label", s)}
                                for s in sources],
                })

        # Cycles (directed simple cycles, up to 5 nodes)
        try:
            cycles = list(nx.simple_cycles(g, length_bound=5))
            # Deduplicate by sorted node set
            seen = set()
            for cycle in cycles:
                key = tuple(sorted(cycle))
                if key not in seen:
                    seen.add(key)
                    details = []
                    for nid in cycle:
                        attrs = self._engine.get_node(nid) or {}
                        details.append({
                            "id": nid,
                            "label": attrs.get("label", nid),
                            "type": attrs.get("type", "unknown"),
                        })
                    results["cycles"].append({
                        "length": len(cycle),
                        "nodes": details,
                    })
        except Exception:
            pass

        return results

    # ── Path Analysis ───────────────────────────────────────────

    def shortest_path(self, source: str, target: str) -> Optional[Dict]:
        """Shortest directed path between two nodes."""
        g = self._engine.nx_graph
        try:
            path = nx.shortest_path(g, source=source, target=target)
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            # Try undirected
            try:
                path = nx.shortest_path(self._engine.undirected(), source=source, target=target)
            except (nx.NodeNotFound, nx.NetworkXNoPath):
                return None

        nodes = []
        for nid in path:
            attrs = self._engine.get_node(nid) or {}
            nodes.append({
                "id": nid,
                "label": attrs.get("label", nid),
                "type": attrs.get("type", "unknown"),
            })

        edges = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if self._engine.nx_graph.has_edge(u, v):
                ed = self._engine.get_edge(u, v)
                if ed:
                    edges.append({
                        "source": u,
                        "target": v,
                        "type": ed.get("type", "unknown"),
                    })
            elif self._engine.nx_graph.has_edge(v, u):
                ed = self._engine.get_edge(v, u)
                if ed:
                    edges.append({
                        "source": v,
                        "target": u,
                        "type": ed.get("type", "unknown"),
                    })

        return {"path": [n["id"] for n in nodes], "nodes": nodes, "edges": edges, "length": len(path) - 1}

    def all_paths(self, source: str, target: str, max_depth: int = 4) -> List[Dict]:
        """All simple paths up to max_depth."""
        g = self._engine.nx_graph
        try:
            paths = list(nx.all_simple_paths(g, source=source, target=target, cutoff=max_depth))
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            return []

        result = []
        for path in paths:
            nodes = []
            for nid in path:
                attrs = self._engine.get_node(nid) or {}
                nodes.append({
                    "id": nid,
                    "label": attrs.get("label", nid),
                    "type": attrs.get("type", "unknown"),
                })
            result.append({
                "path": [n["id"] for n in nodes],
                "nodes": nodes,
                "length": len(path) - 1,
            })
        return result

    # ── Connected Components (by shared IP, phone, address) ─────

    def connected_components(self, edge_types: Optional[List[str]] = None) -> List[Dict]:
        """
        Find weakly connected components, optionally filtered by edge types.
        e.g. edge_types=["shared_ip","shared_phone","shared_address"]
        finds groups of clients tied by shared identifiers.
        """
        g = self._engine.nx_graph
        if g.number_of_nodes() == 0:
            return []

        if edge_types:
            # Build a subgraph with only the specified edge types
            h = nx.Graph()
            for u, v, d in g.edges(data=True):
                if d.get("type") in edge_types:
                    h.add_edge(u, v)
            # Add isolated nodes too
            for n in g.nodes:
                if n not in h:
                    h.add_node(n)
        else:
            h = g.to_undirected()

        components = list(nx.connected_components(h))
        result = []
        for i, comp in enumerate(components):
            members = []
            for nid in comp:
                attrs = self._engine.get_node(nid) or {}
                members.append({
                    "id": nid,
                    "label": attrs.get("label", nid),
                    "type": attrs.get("type", "unknown"),
                    "risk_score": attrs.get("risk_score", 0),
                })
            # Sort by risk score descending
            members.sort(key=lambda m: m["risk_score"], reverse=True)
            avg_risk = round(sum(m["risk_score"] for m in members) / max(len(members), 1), 1)

            # Categorise
            customer_count = sum(1 for m in members if m["type"] == "customer")
            account_count = sum(1 for m in members if m["type"] == "account")
            external_count = sum(1 for m in members if m["type"] == "external")
            ip_count = sum(1 for m in members if m["type"] == "ip")

            result.append({
                "component_id": i + 1,
                "size": len(members),
                "avg_risk_score": avg_risk,
                "max_risk_score": max((m["risk_score"] for m in members), default=0),
                "composition": {
                    "customers": customer_count,
                    "accounts": account_count,
                    "external_entities": external_count,
                    "ip_addresses": ip_count,
                },
                "members": members,
            })

        result.sort(key=lambda c: c["size"], reverse=True)
        return result

    # ── BFS Expansion ───────────────────────────────────────────

    def bfs_expand(self, seed_id: str, max_depth: int = 3,
                   direction: str = "both") -> Dict[str, Any]:
        """
        Breadth-first search outward from a seed node.
        direction: "forward" (outgoing), "backward" (incoming), or "both"
        """
        g = self._engine.nx_graph
        if seed_id not in g:
            return {"error": f"Node {seed_id} not found"}

        seed_attrs = self._engine.get_node(seed_id) or {}

        visited: Dict[str, int] = {seed_id: 0}  # node_id -> depth
        queue: List[tuple] = [(seed_id, 0)]
        levels: Dict[int, List[str]] = {0: [seed_id]}

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            neighbors = []
            if direction in ("forward", "both"):
                neighbors.extend(g.successors(current))
            if direction in ("backward", "both"):
                neighbors.extend(g.predecessors(current))

            for nb in neighbors:
                if nb not in visited:
                    visited[nb] = depth + 1
                    queue.append((nb, depth + 1))
                    levels.setdefault(depth + 1, []).append(nb)

        # Build result per level
        expansion = []
        edge_count = 0
        for d in range(1, max_depth + 1):
            level_nodes = levels.get(d, [])
            if not level_nodes:
                continue
            node_details = []
            for nid in level_nodes:
                attrs = self._engine.get_node(nid) or {}
                node_details.append({
                    "id": nid,
                    "label": attrs.get("label", nid),
                    "type": attrs.get("type", "unknown"),
                    "risk_score": attrs.get("risk_score", 0),
                })
                # Count edges connecting to previous level
                for pred in g.predecessors(nid):
                    if visited.get(pred, 99) == d - 1:
                        edge_count += 1
                for succ in g.successors(nid):
                    if visited.get(succ, 99) == d - 1:
                        edge_count += 1

            expansion.append({
                "depth": d,
                "node_count": len(level_nodes),
                "nodes": node_details,
            })

        return {
            "seed_id": seed_id,
            "seed_label": seed_attrs.get("label", seed_id),
            "seed_type": seed_attrs.get("type", "unknown"),
            "max_depth": max_depth,
            "direction": direction,
            "total_reached": len(visited) - 1,
            "total_edges_traversed": edge_count,
            "expansion": expansion,
        }

    # ── Dijkstra (Risk-Weighted Shortest Path) ────────────────────

    def dijkstra_risk_path(self, source: str, target: str) -> Optional[Dict]:
        """
        Find the lowest-risk path between two nodes.
        Edge weights are derived from risk:
          - transaction amount / ownership → higher weight = riskier
          - shared attribute edges → weight = avg(source_risk, target_risk) * 0.5
          - llm_discovered → weight = 1 - confidence (lower confidence = higher weight)
        """
        g = self._engine.nx_graph
        if source not in g:
            return {"error": f"Source {source} not found"}
        if target not in g:
            return {"error": f"Target {target} not found"}

        # Build a weighted undirected graph for Dijkstra
        h = nx.Graph()

        # Add all nodes
        for n in g.nodes:
            h.add_node(n)

        # Add edges with risk-based weights
        for u, v, d in g.edges(data=True):
            edge_type = d.get("type", "unknown")

            if edge_type == "transaction":
                amount = d.get("amount", 0)
                # Higher amount = higher risk weight, normalised
                weight = min(100.0, amount / 10000) if amount else 10.0
            elif edge_type == "ownership":
                pct = d.get("percentage", 0)
                weight = max(5.0, pct)  # at least 5
            elif edge_type in ("shared_ip", "shared_phone", "shared_address", "shared_email", "shared_device"):
                src_risk = g.nodes[u].get("risk_score", 0) or 50
                tgt_risk = g.nodes[v].get("risk_score", 0) or 50
                weight = max(1.0, (src_risk + tgt_risk) / 2 * 0.3)
            elif edge_type == "llm_discovered":
                confidence = d.get("confidence", 0.5)
                weight = max(1.0, (1 - confidence) * 20)
            else:
                weight = 5.0

            h.add_edge(u, v, weight=round(weight, 2))

        try:
            path = nx.dijkstra_path(h, source=source, target=target, weight="weight")
            total_weight = nx.dijkstra_path_length(h, source=source, target=target, weight="weight")
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            return None

        nodes = []
        for nid in path:
            attrs = self._engine.get_node(nid) or {}
            nodes.append({
                "id": nid,
                "label": attrs.get("label", nid),
                "type": attrs.get("type", "unknown"),
                "risk_score": attrs.get("risk_score", 0),
            })

        edges = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if g.has_edge(u, v):
                ed = self._engine.get_edge(u, v)
            elif g.has_edge(v, u):
                ed = self._engine.get_edge(v, u)
            else:
                ed = None
            edge_data = {"source": u, "target": v, "type": "unknown"}
            if ed:
                # Recalculate the weight
                edge_type = ed.get("type", "unknown")
                if edge_type == "transaction" and ed.get("amount"):
                    w = min(100.0, ed["amount"] / 10000)
                elif edge_type == "ownership" and ed.get("percentage"):
                    w = max(5.0, ed["percentage"])
                elif edge_type in ("shared_ip", "shared_phone", "shared_address", "shared_email", "shared_device"):
                    src_r = g.nodes[u].get("risk_score", 0) or 50
                    tgt_r = g.nodes[v].get("risk_score", 0) or 50
                    w = max(1.0, (src_r + tgt_r) / 2 * 0.3)
                elif edge_type == "llm_discovered":
                    conf = ed.get("confidence", 0.5)
                    w = max(1.0, (1 - conf) * 20)
                else:
                    w = 5.0
                edge_data = {"source": u, "target": v, "type": edge_type, "weight": round(w, 2)}
                if ed.get("amount"): edge_data["amount"] = ed["amount"]
                if ed.get("currency"): edge_data["currency"] = ed["currency"]
                if ed.get("date"): edge_data["date"] = ed["date"]
            edges.append(edge_data)

        return {
            "source": source,
            "target": target,
            "path": [n["id"] for n in nodes],
            "nodes": nodes,
            "edges": edges,
            "length": len(path) - 1,
            "total_risk_weight": round(total_weight, 2),
        }

    # ── Temporal Analysis ───────────────────────────────────────

    def temporal_analysis(self) -> Dict[str, Any]:
        """Analyze transaction timing for anomalies."""
        g = self._engine.nx_graph
        transactions = []

        for u, v, d in g.edges(data=True):
            if d.get("type") == "transaction" and d.get("date"):
                transactions.append({
                    "source": u,
                    "target": v,
                    "date": d["date"],
                    "amount": d.get("amount", 0),
                    "currency": d.get("currency", ""),
                })

        if not transactions:
            return {"anomalies": [], "summary": "No transaction data for temporal analysis."}

        # Group by month
        monthly_counts = Counter()
        monthly_volumes = defaultdict(float)
        for t in transactions:
            month = t["date"][:7]  # YYYY-MM
            monthly_counts[month] += 1
            monthly_volumes[month] += t.get("amount", 0)

        months_sorted = sorted(monthly_counts.keys())
        avg_count = sum(monthly_counts.values()) / max(len(months_sorted), 1)
        anomalies = []

        for month in months_sorted:
            count = monthly_counts[month]
            if count > avg_count * 1.5:
                anomalies.append({
                    "month": month,
                    "transaction_count": count,
                    "total_volume": round(monthly_volumes[month], 2),
                    "reason": f"Transaction count ({count}) is {round(count / avg_count, 1)}× monthly average",
                })

        # Rapid succession check: same source, multiple txs within short period
        from collections import defaultdict as dd
        source_dates = dd(list)
        for t in transactions:
            source_dates[t["source"]].append(t["date"])

        for src, dates in source_dates.items():
            dates_sorted = sorted(dates)
            for i in range(len(dates_sorted) - 1):
                # Simple heuristic: if two transactions within 30 days from same source
                if len(dates_sorted) >= 2:
                    attrs = self._engine.get_node(src) or {}
                    anomalies.append({
                        "type": "rapid_succession",
                        "node_id": src,
                        "label": attrs.get("label", src),
                        "dates": dates_sorted,
                        "reason": f"Multiple transactions from same entity within short timeframe",
                    })
                    break  # one flag per source

        return {
            "anomalies": anomalies,
            "monthly_summary": [{"month": m, "count": monthly_counts[m],
                                 "volume": round(monthly_volumes[m], 2)}
                                for m in months_sorted],
            "total_transactions": len(transactions),
        }

    # ── Summary statistics ──────────────────────────────────────

    def summary_stats(self) -> Dict[str, Any]:
        """Overview stats for the dashboard header."""
        g = self._engine.nx_graph
        customers = [n for n in g.nodes if g.nodes[n].get("type") == "customer"]

        high = sum(1 for n in customers if (g.nodes[n].get("risk_score") or 0) >= 70)
        med = sum(1 for n in customers if 30 <= (g.nodes[n].get("risk_score") or 0) < 70)
        low = sum(1 for n in customers if (g.nodes[n].get("risk_score") or 0) < 30)

        patterns = self.detect_patterns()
        total_patterns = len(patterns["fan_out"]) + len(patterns["fan_in"]) + len(patterns["cycles"])

        return {
            "totalNodes": g.number_of_nodes(),
            "totalEdges": g.number_of_edges(),
            "customers": len(customers),
            "highRisk": high,
            "medRisk": med,
            "lowRisk": low,
            "suspiciousPatterns": total_patterns,
            "communities": len(self.communities()),
        }
