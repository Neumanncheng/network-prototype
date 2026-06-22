"""
FastAPI entry point — Network Analytics Engine Backend.

Backend switch via env vars (or .env file):
    DB_BACKEND=networkx    (default)  — in-memory NetworkX, no dependencies
    DB_BACKEND=neo4j                  — Neo4j persistent graph database

    LLM_PROVIDER=mock      (default)  — rule-based explanations, no API key
    LLM_PROVIDER=deepseek             — DeepSeek Chat (set DEEPSEEK_API_KEY)
    LLM_PROVIDER=openai               — OpenAI GPT (set OPENAI_API_KEY)

Run with:
    pip install -r requirements.txt

    # NetworkX (default):
    uvicorn main:app --reload --port 8000

    # Neo4j:
    DB_BACKEND=neo4j uvicorn main:app --reload --port 8000

    # Or just fill in backend/.env and run:
    uvicorn main:app --reload --port 8000
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from routers import graph, analytics, risk, auth
from routers.auth import require_auth

# ── Load .env file from backend directory ──────────────────
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"📄 Loaded config from {env_path}")

# ── Select backend engine ───────────────────────────────────────
DB_BACKEND = os.environ.get("DB_BACKEND", "networkx").lower()

if DB_BACKEND == "neo4j":
    from services.neo4j_engine import Neo4jEngine
    from seed_neo4j import seed_neo4j_data

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password123")

    engine = Neo4jEngine(uri=uri, user=user, password=password)
    engine.clear_all()
    seed_neo4j_data(engine)
    engine.load_from_neo4j()
    backend_name = "neo4j"
else:
    from services.graph_engine import GraphEngine
    from sample_data import seed_sample_data

    engine = GraphEngine()
    seed_sample_data(engine)
    backend_name = "networkx"

print(f"🔧 Backend engine: {backend_name} ({engine.node_count} nodes, {engine.edge_count} edges)")

# ── FastAPI app ────────────────────────────────────────────────
app = FastAPI(
    title="Network Analytics Engine API",
    version="1.0.0",
    description="Relationship graph analytics, risk scoring, and LLM explanations for AML name screening.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store engine on app.state for router access
@app.on_event("startup")
async def startup():
    app.state.engine = engine

# ── Register routers ──────────────────────────────────────────
app.include_router(auth.router)  # public — login endpoint
# Protected routes (require valid JWT)
protected_routers = [graph.router, analytics.router, risk.router]
for r in protected_routers:
    app.include_router(r, dependencies=[Depends(require_auth)])


# ── Health-check ──────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "backend": backend_name,
        "nodes": engine.node_count,
        "edges": engine.edge_count,
    }


# ── Direct run ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
