from pydantic import BaseModel
from typing import Optional


class AnalyzeRequest(BaseModel):
    article: str


class CausalNode(BaseModel):
    id: str
    label: str
    score: float
    hop: int
    domain: str
    direction: str
    parent: Optional[str] = None
    edge_strength: float
    probability: float


class EdgeData(BaseModel):
    id: str
    source: str
    target: str
    strength: float
    label: str


class CytoscapeEdge(BaseModel):
    data: EdgeData


class AnalyzeStats(BaseModel):
    total_nodes: int
    max_depth: int
    avg_confidence: float


class AnalyzeResponse(BaseModel):
    root_event: str
    canonical_node: str
    domain: str
    entities: list[str]
    causal_chain: list[dict]
    edges: list[dict]
    stats: AnalyzeStats
