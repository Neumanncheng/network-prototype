"""
Seed Neo4j with the same sample data as sample_data.py.
Run standalone to populate Neo4j:

    python seed_neo4j.py

Or import and call seed_neo4j_data(engine).
"""

from services.neo4j_engine import Neo4jEngine


def seed_neo4j_data(engine: Neo4jEngine):
    """Seed Neo4j with the sample graph (same data as sample_data.py)."""

    # ── Customers ────────────────────────────────────────────
    alice = engine.add_node_with_id("n-1", "customer", label="Alice Wang", label_zh="王愛麗",
                                    risk_score=85, country="HK", id_type="HKID", id_number="A123456(7)")
    bob = engine.add_node_with_id("n-2", "customer", label="Bob Li", label_zh="李波",
                                  risk_score=42, country="CN", id_type="Passport", id_number="EB1234567")
    carol = engine.add_node_with_id("n-3", "customer", label="Carol Chen", label_zh="陳雅婷",
                                    risk_score=12, country="HK", id_type="HKID", id_number="C789012(3)")
    dave = engine.add_node_with_id("n-4", "customer", label="Dave Zhang", label_zh="張大衛",
                                   risk_score=68, country="CN", id_type="Passport", id_number="EZ9876543")
    eve = engine.add_node_with_id("n-5", "customer", label="Eve Liu", label_zh="劉怡文",
                                  risk_score=91, country="MO", id_type="Macau ID", id_number="M123456")

    # ── Bank Accounts ─────────────────────────────────────────
    acc_a1 = engine.add_node_with_id("n-6", "account", label="HSBC-7890", bank="HSBC")
    acc_a2 = engine.add_node_with_id("n-7", "account", label="BOCHK-4321", bank="BOCHK")
    acc_b1 = engine.add_node_with_id("n-8", "account", label="ICBC-5566", bank="ICBC")
    acc_b2 = engine.add_node_with_id("n-9", "account", label="ABC-7788", bank="ABC")
    acc_c1 = engine.add_node_with_id("n-10", "account", label="HSBC-1122", bank="HSBC")
    acc_e1 = engine.add_node_with_id("n-11", "account", label="BNU-3344", bank="BNU")

    # ── External Entities ─────────────────────────────────────
    shell1 = engine.add_node_with_id("n-12", "external", label="Gold Luck Ltd", country="BVI", risk_score=90)
    shell2 = engine.add_node_with_id("n-13", "external", label="Silver Star Ltd", country="BVI", risk_score=75)
    offshore = engine.add_node_with_id("n-14", "external", label="Pinnacle Corp", country="Panama", risk_score=88)

    # ── IP Addresses ──────────────────────────────────────────
    engine.add_node_with_id("n-15", "ip", label="203.0.113.42", geo="Hong Kong", isp="HKBN")
    engine.add_node_with_id("n-16", "ip", label="198.51.100.7", geo="Macau", isp="CTM")
    engine.add_node_with_id("n-17", "ip", label="192.0.2.88", geo="Shenzhen", isp="China Telecom")

    # ── Devices ───────────────────────────────────────────────
    engine.add_node_with_id("n-18", "device", label="iPhone-XXXX", os="iOS 17")
    engine.add_node_with_id("n-19", "device", label="Samsung-YYYY", os="Android 14")

    # ── Transactions ──────────────────────────────────────────
    engine.add_edge(alice, acc_a1, "transaction", amount=500000, currency="HKD", date="2026-03-15")
    engine.add_edge(acc_a1, shell1, "transaction", amount=480000, currency="HKD", date="2026-03-16")
    engine.add_edge(alice, acc_a2, "transaction", amount=1200000, currency="HKD", date="2026-04-01")
    engine.add_edge(acc_a2, offshore, "transaction", amount=1150000, currency="HKD", date="2026-04-02")
    engine.add_edge(bob, acc_b1, "transaction", amount=250000, currency="CNY", date="2026-02-10")
    engine.add_edge(bob, acc_b2, "transaction", amount=180000, currency="CNY", date="2026-02-11")
    engine.add_edge(carol, acc_c1, "transaction", amount=50000, currency="HKD", date="2026-05-20")
    engine.add_edge(eve, acc_e1, "transaction", amount=2000000, currency="MOP", date="2026-06-01")
    engine.add_edge(acc_e1, offshore, "transaction", amount=1900000, currency="MOP", date="2026-06-02")
    engine.add_edge(dave, shell2, "transaction", amount=350000, currency="USD", date="2026-01-05")

    # ── Ownership ─────────────────────────────────────────────
    engine.add_edge(alice, shell1, "ownership", percentage=100)
    engine.add_edge(eve, offshore, "ownership", percentage=60)
    engine.add_edge(bob, shell2, "ownership", percentage=30)

    # ── Shared Attributes ─────────────────────────────────────
    engine.add_edge(alice, bob, "shared_phone")
    engine.add_edge(alice, carol, "shared_address")
    engine.add_edge(alice, dave, "shared_email")
    engine.add_edge(bob, dave, "shared_ip", ip="203.0.113.42")
    engine.add_edge(alice, eve, "shared_ip", ip="198.51.100.7")
    engine.add_edge(bob, eve, "shared_device")

    # ── LLM-discovered ────────────────────────────────────────
    engine.add_edge(alice, offshore, "llm_discovered",
                    evidence="Alice controls Pinnacle Corp through nested BVI entities",
                    confidence=0.78)
    engine.add_edge(dave, eve, "llm_discovered",
                    evidence="Transaction timing correlation — both fund same Panama entity within 48h",
                    confidence=0.65)


if __name__ == "__main__":
    import os
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password123")

    print(f"Connecting to Neo4j at {uri} ...")
    engine = Neo4jEngine(uri=uri, user=user, password=password)
    engine.clear_all()
    seed_neo4j_data(engine)
    engine.load_from_neo4j()
    print(f"Seeded {engine.node_count} nodes, {engine.edge_count} edges")
    engine.close()
    print("Done!")
