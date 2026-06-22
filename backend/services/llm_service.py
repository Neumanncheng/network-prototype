"""
LLM service — generates narrative explanations of graph relationships.

Supports multiple backends controlled by LLM_PROVIDER env var:
  LLM_PROVIDER=deepseek   → DeepSeek Chat (via OpenAI-compatible API)
  LLM_PROVIDER=openai     → OpenAI GPT
  LLM_PROVIDER=mock       → Rule-based mock (default, no API key needed)

Requires the respective API key in env:
  DEEPSEEK_API_KEY or OPENAI_API_KEY
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional

from .graph_engine import GraphEngine
from .analytics_service import AnalyticsService
from .risk_scoring import RiskScoringService


class LLMService:
    """Produces plain-English explanations of graph structures."""

    def __init__(self, engine: GraphEngine):
        self._engine = engine
        self._analytics = AnalyticsService(engine)
        self._risk = RiskScoringService(engine)
        self._provider = os.environ.get("LLM_PROVIDER", "mock").lower()
        self._client = self._init_client()

    _TYPE_LABELS = {
        "customer": "Customer",
        "account": "Bank Account",
        "external": "External Entity",
        "ip": "IP Address",
        "device": "Device",
    }

    def _type_label(self, t: str) -> str:
        return self._TYPE_LABELS.get(t, t)

    # ── Client initialisation ──────────────────────────────

    def _init_client(self):
        if self._provider == "deepseek":
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            if not api_key:
                print("⚠️  DEEPSEEK_API_KEY not set, falling back to mock")
                self._provider = "mock"
                return None
            from openai import OpenAI
            return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

        if self._provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                print("⚠️  OPENAI_API_KEY not set, falling back to mock")
                self._provider = "mock"
                return None
            from openai import OpenAI
            return OpenAI(api_key=api_key)

        self._provider = "mock"
        return None

    def _model_name(self) -> str:
        return {"deepseek": "deepseek-chat", "openai": "gpt-4o"}.get(self._provider, "mock")

    # ── Build subgraph context for LLM ─────────────────────

    def _build_context(self, nid: str) -> Dict[str, Any]:
        """Serialise the node + 1-hop neighbourhood for LLM analysis."""
        node = self._engine.get_node(nid)
        if not node:
            return {}

        neighbors = self._engine.neighbors(nid)
        edges = []
        for nb_id, nb_attrs in neighbors:
            for direction, s, t, e_data in self._engine.get_edges_between(nid, nb_id):
                edges.append({
                    "type": e_data.get("type", "unknown"),
                    "from": s,
                    "to": t,
                    **({k: v for k, v in e_data.items() if k not in ("id", "type", "source", "target")}),
                })

        patterns = self._analytics.detect_patterns()
        node_patterns = []
        for fo in patterns["fan_out"]:
            if fo["node_id"] == nid:
                node_patterns.append(f"fan-out ({fo['out_degree']} connections)")
        for fi in patterns["fan_in"]:
            if fi["node_id"] == nid:
                node_patterns.append(f"fan-in ({fi['in_degree']} connections)")
        for cycle in patterns["cycles"]:
            if any(n["id"] == nid for n in cycle["nodes"]):
                node_patterns.append(f"part of a {cycle['length']}-node cycle")

        risk_info = self._risk.compute_risk_breakdown(nid)

        return {
            "entity": {
                "id": nid,
                "label": node.get("label", nid),
                "type": node.get("type", "unknown"),
                "country": node.get("country"),
                "risk_score": node.get("risk_score", 0),
                "details": {k: v for k, v in node.items()
                            if k not in ("id", "label", "type", "country", "risk_score")},
            },
            "neighborhood": {
                "connected_entities": [
                    {"id": nb_id, "label": nb_attrs.get("label", nb_id), "type": nb_attrs.get("type", "unknown"),
                     "risk_score": nb_attrs.get("risk_score", 0)}
                    for nb_id, nb_attrs in neighbors
                ],
                "edges": edges,
            },
            "patterns_detected": node_patterns,
            "risk_breakdown": risk_info,
        }

    # ── LLM call ───────────────────────────────────────────

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Call the configured LLM provider. Returns None on failure."""
        if self._provider == "mock":
            return None

        try:
            response = self._client.chat.completions.create(
                model=self._model_name(),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️  LLM call failed: {e}")
            return None

    # ── Graph explanation for a node ──────────────────────

    def explain_node(self, nid: str) -> Dict[str, Any]:
        """Full narrative explanation — uses LLM if available, falls back to mock."""
        node = self._engine.get_node(nid)
        if node is None:
            return {"error": f"Node {nid} not found"}

        label = node.get("label", nid)
        node_type = node.get("type", "unknown")
        risk_score = node.get("risk_score", 0)

        # ── Try real LLM first ────────────────────────────────
        if self._provider != "mock":
            context = self._build_context(nid)

            system_prompt = (
                "You are an AML analyst. Give a VERY CONCISE assessment (2-3 short sentences max). "
                "Focus only on what matters for an investigator to make a quick decision.\n\n"
                "Return valid JSON with these exact keys:\n"
                "  - narrative: 2-3 short sentences max. Use **bold** for names and numbers. "
                "State the key risk, how they're connected, and what's suspicious. NO fluff.\n"
                "  - typology: one short phrase classifying the typology "
                "(e.g. 'Trade-based money laundering with shell company layering')\n"
                "  - risk_factors: array of short items, max 5, each 5-10 words "
                "(e.g. ['100% owner of BVI shell company Gold Luck Ltd'])\n"
                "  - investigation_notes: array of short questions, max 3, "
                "each a single actionable question for the investigator\n\n"
                "CRITICAL: Keep it SHORT. Officers need to scan in 10 seconds."
            )

            user_prompt = (
                f"Analyse this entity in its network context:\n\n"
                f"{json.dumps(context, indent=2, default=str)}"
            )

            llm_text = self._call_llm(system_prompt, user_prompt)

            if llm_text:
                try:
                    # Try to parse as JSON
                    parsed = json.loads(llm_text)
                    narrative = parsed.get("narrative", "")
                    typology = parsed.get("typology", "See narrative for details")
                    risk_factors = parsed.get("risk_factors", [])
                    investigation_notes = parsed.get("investigation_notes", "")

                    # Format narrative paragraphs
                    if isinstance(narrative, str):
                        paragraphs = narrative.split("\n\n")
                    else:
                        paragraphs = [str(narrative)]

                    return {
                        "node_id": nid,
                        "label": label,
                        "type": node_type,
                        "risk_score": risk_score,
                        "narrative": "\n\n".join(paragraphs),
                        "typology": typology,
                        "risk_factors": risk_factors,
                        "investigation_notes": investigation_notes,
                        "llm_provider": self._provider,
                    }
                except (json.JSONDecodeError, KeyError):
                    # Return raw text if JSON parsing fails
                    return {
                        "node_id": nid,
                        "label": label,
                        "type": node_type,
                        "risk_score": risk_score,
                        "narrative": llm_text,
                        "typology": "See narrative above",
                        "llm_provider": self._provider,
                    }

        # ── Fallback: rule-based mock ──────────────────────────
        return self._mock_explain_node(nid, node, label, node_type, risk_score)

    # ── Mock explanation (original rule-based logic) ─────

    def _mock_explain_node(self, nid: str, node: Dict, label: str,
                           node_type: str, risk_score: int) -> Dict[str, Any]:
        """Same rule-based mock as before — no LLM needed."""
        neighbors = self._engine.neighbors(nid)
        connections_by_type: Dict[str, list] = {}
        for nb_id, nb_attrs in neighbors:
            t = nb_attrs.get("type", "unknown")
            connections_by_type.setdefault(t, []).append(nb_attrs.get("label", nb_id))

        patterns = self._analytics.detect_patterns()
        node_patterns = []
        for fo in patterns["fan_out"]:
            if fo["node_id"] == nid:
                node_patterns.append(f"fan-out (connects to {fo['out_degree']} entities)")
        for fi in patterns["fan_in"]:
            if fi["node_id"] == nid:
                node_patterns.append(f"fan-in ({fi['in_degree']} entities connect to it)")
        for cycle in patterns["cycles"]:
            if any(n["id"] == nid for n in cycle["nodes"]):
                node_patterns.append(f"part of a {cycle['length']}-node cycle")

        risk_info = self._risk.compute_risk_breakdown(nid)
        top_risk_driver = "N/A"
        if risk_info:
            comps = risk_info["components"]
            top_driver = max(comps.items(), key=lambda x: x[1]["contribution"])
            top_risk_driver = f"{top_driver[0]} ({top_driver[1]['contribution']} pts)"

        paragraphs = []

        type_name = self._type_label(node_type)
        id_info = ""
        if node.get("id_type") and node.get("id_number"):
            id_info = f" ({node['id_type']}: {node['id_number']})"
        location = f" based in {node['country']}" if node.get("country") else ""
        paragraphs.append(
            f"**{label}** is a **{type_name}**{location}{id_info} "
            f"with a composite risk score of **{risk_score}**."
        )

        if connections_by_type:
            conn_parts = []
            for t, names in sorted(connections_by_type.items()):
                type_label = self._type_label(t)
                if len(names) == 1:
                    conn_parts.append(f"1 {type_label} ({names[0]})")
                else:
                    conn_parts.append(f"{len(names)} {type_label}s ({', '.join(names)})")
            paragraphs.append(
                f"This entity connects to **{sum(len(v) for v in connections_by_type.values())}** "
                f"other entities: {', '.join(conn_parts)}."
            )

        if node_patterns:
            paragraphs.append(f"⚠️ **Patterns detected**: {', '.join(node_patterns)}.")

        if risk_info and top_risk_driver != "N/A":
            paragraphs.append(f"The primary risk driver is **{top_risk_driver}**.")

        if risk_score >= 70:
            paragraphs.append("🚨 **High risk — this entity requires immediate attention and escalation to MLRO.**")
        elif risk_score >= 30:
            paragraphs.append("⚠️ **Medium risk — this entity should be reviewed by a human investigator.**")
        else:
            paragraphs.append("✅ **Low risk — suitable for auto-release with logging.**")

        typology = self._classify_typology(node, node_patterns, neighbors)
        if typology:
            paragraphs.append(f"🔍 **Typology classification**: {typology}")

        return {
            "node_id": nid,
            "label": label,
            "type": node_type,
            "risk_score": risk_score,
            "narrative": "\n\n".join(paragraphs),
            "connections_summary": connections_by_type,
            "patterns": node_patterns,
            "top_risk_driver": top_risk_driver,
            "typology": typology,
            "llm_provider": "mock",
        }

    def _classify_typology(self, node: Dict, patterns: List[str], neighbors: List) -> Optional[str]:
        """Classify into common AML typologies based on patterns."""
        node_type = node.get("type", "")

        if node_type == "external" and (
            "shell" in (node.get("label", "")).lower()
            or node.get("country") in ("BVI", "Panama", "Cayman")
        ):
            if any("ownership" in str(n) for n in neighbors):
                return "Shell company with beneficial ownership — possible layering stage"

        if any("cycle" in p for p in patterns):
            return "Circular transaction flow — possible round-tripping or loan-back scheme"

        if any("fan-out" in p for p in patterns):
            return "Funds disbursement hub — possible structuring or funnel activity"

        if node.get("risk_score", 0) >= 70 and node_type == "customer":
            return "High-risk individual with adverse network connections"

        if node_type == "external" and node.get("country") in ("BVI", "Panama"):
            return "Offshore entity in high-risk jurisdiction"

        return "Standard pattern — no immediate typology match"

    # ── Path explanation ─────────────────────────────────

    def explain_path(self, source_id: str, target_id: str, path_data: Dict) -> str:
        """Explain a connection path between two entities."""
        if not path_data or "nodes" not in path_data:
            return "No path found between these entities."

        # ── Try real LLM ───────────────────────────────────────
        if self._provider != "mock":
            system_prompt = (
                "You are an AML investigator. Given a connection path between two entities, "
                "explain what this path suggests in terms of money movement, risk, and "
                "whether it warrants further investigation. Be concise and specific."
            )
            user_prompt = (
                f"Explain this connection path:\n\n"
                f"{json.dumps(path_data, indent=2, default=str)}"
            )
            llm_text = self._call_llm(system_prompt, user_prompt)
            if llm_text:
                return llm_text

        # ── Fallback: rule-based mock ──────────────────────────
        nodes = path_data.get("nodes", [])
        edges = path_data.get("edges", [])
        source_label = nodes[0]["label"] if nodes else source_id
        target_label = nodes[-1]["label"] if nodes else target_id

        parts = [f"**Connection path from {source_label} to {target_label}**\n"]
        parts.append(f"Path length: **{len(nodes) - 1} hop(s)** through {len(nodes) - 2} intermediate entit{'y' if len(nodes) - 2 == 1 else 'ies'}.\n")

        steps = []
        for i, edge in enumerate(edges):
            from_label = "unknown"
            to_label = "unknown"
            for n in nodes:
                if n["id"] == edge["source"]:
                    from_label = n["label"]
                if n["id"] == edge["target"]:
                    to_label = n["label"]
            edge_type = edge.get("type", "connected to").replace("_", " ")
            steps.append(f"  {i + 1}. **{from_label}** _{edge_type}_ → **{to_label}**")

        parts.append("\n".join(steps))

        source_risk = None
        target_risk = None
        for n in nodes:
            n_attrs = self._engine.get_node(n["id"]) or {}
            if n["id"] == source_id:
                source_risk = n_attrs.get("risk_score")
            if n["id"] == target_id:
                target_risk = n_attrs.get("risk_score")

        if source_risk is not None and target_risk is not None:
            parts.append(
                f"\nRisk implication: {source_label} (risk: {source_risk}) "
                f"{'↑' if target_risk > source_risk else '↓'} "
                f"→ {target_label} (risk: {target_risk})."
            )

        return "\n\n".join(parts)
