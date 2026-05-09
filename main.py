import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from models.schemas import AnalyzeRequest, AnalyzeResponse  # noqa: E402
from pipeline.extractor import extract_event  # noqa: E402
from pipeline.normalizer import normalize_event  # noqa: E402
from pipeline.graph_engine import load_causal_graph, get_all_source_nodes  # noqa: E402
from pipeline.propagator import propagate  # noqa: E402

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RippleIQ",
    description="Extracts causal chains from news articles using LLM + graph propagation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Load graph once at startup
# ---------------------------------------------------------------------------

GRAPH, RULES = load_causal_graph()
AVAILABLE_NODES: list[str] = get_all_source_nodes(RULES)

# ---------------------------------------------------------------------------
# Routes — define BEFORE mounting static to avoid shadowing
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "graph_nodes": GRAPH.number_of_nodes(), "graph_edges": GRAPH.number_of_edges()}


@app.get("/graph-schema")
async def graph_schema():
    """Return all nodes and edges from causal_rules.json for full-schema visualisation."""
    seen_nodes: set[str] = set()
    nodes: list[dict] = []
    edges: list[dict] = []

    for i, rule in enumerate(RULES):
        for node_id in (rule["from"], rule["to"]):
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append(
                    {
                        "data": {
                            "id": node_id,
                            "label": node_id.replace("_", " ").title(),
                            "domain": rule["domain"],
                        }
                    }
                )
        edges.append(
            {
                "data": {
                    "id": f"e{i}",
                    "source": rule["from"],
                    "target": rule["to"],
                    "strength": rule["strength"],
                    "label": f"{int(rule['probability'] * 100)}%",
                    "domain": rule["domain"],
                }
            }
        )

    return {"nodes": nodes, "edges": edges}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    if not request.article.strip():
        raise HTTPException(status_code=400, detail="Article text cannot be empty.")

    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set.")

    # Step 1 — extract primary event via LLM
    extracted = extract_event(request.article)

    # Step 2 — normalise raw event to canonical graph node
    canonical_node = normalize_event(extracted["raw_event"], AVAILABLE_NODES)

    # Step 3 — propagate causal chain through the graph
    causal_chain = propagate(GRAPH, canonical_node)

    # Patch root node domain with the LLM-detected domain
    if causal_chain and causal_chain[0]["hop"] == 0:
        causal_chain[0]["domain"] = extracted["domain"]

    # Step 4 — build Cytoscape-ready edges list
    edges: list[dict] = []
    for i, node in enumerate(causal_chain):
        if node["parent"] is not None:
            edges.append(
                {
                    "data": {
                        "id": f"e{i}",
                        "source": node["parent"],
                        "target": node["id"],
                        "strength": node["edge_strength"],
                        "label": f"{int(node['probability'] * 100)}%",
                    }
                }
            )

    # Step 5 — compute summary stats
    total_nodes = len(causal_chain)
    max_depth = max((n["hop"] for n in causal_chain), default=0)
    avg_confidence = (
        sum(n["score"] for n in causal_chain) / total_nodes if total_nodes else 0.0
    )

    return {
        "root_event": extracted["raw_event"],
        "canonical_node": canonical_node,
        "domain": extracted["domain"],
        "entities": extracted["entities"],
        "causal_chain": causal_chain,
        "edges": edges,
        "stats": {
            "total_nodes": total_nodes,
            "max_depth": max_depth,
            "avg_confidence": round(avg_confidence, 4),
        },
    }


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


# Static assets (served under /static/*)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
