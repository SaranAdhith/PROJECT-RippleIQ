from collections import deque
import networkx as nx

MAX_DEPTH = 6
MIN_SCORE = 0.05
HOP_DECAY = 0.75


def propagate(graph: nx.DiGraph, root_node: str) -> list[dict]:
    """
    BFS causal propagation from root_node.

    Score formula per hop:
        cumulative_strength = parent_cumulative_strength × edge.strength
        effective_score     = cumulative_strength × edge.probability
        decayed_score       = effective_score × HOP_DECAY ^ hop_number

    Stops when decayed_score < MIN_SCORE or hop > MAX_DEPTH.
    If a node is reached again at a higher score, its entry is updated.
    """
    if root_node not in graph:
        return []

    # node -> best decayed_score seen so far
    best_scores: dict[str, float] = {root_node: 1.0}
    # node -> result dict (kept up-to-date when score improves)
    result_map: dict[str, dict] = {
        root_node: {
            "id": root_node,
            "label": _label(root_node),
            "score": 1.0,
            "hop": 0,
            "domain": "root",
            "direction": "neutral",
            "parent": None,
            "edge_strength": 1.0,
            "probability": 1.0,
        }
    }

    # Queue entries: (node, hop, parent, parent_cumulative_strength, edge_data)
    queue: deque[tuple] = deque()
    for neighbor in graph.successors(root_node):
        edge_data = graph[root_node][neighbor]
        queue.append((neighbor, 1, root_node, 1.0, edge_data))

    while queue:
        node, hop, parent, parent_cs, edge_data = queue.popleft()

        if hop > MAX_DEPTH:
            continue

        cumulative_strength = parent_cs * edge_data["strength"]
        effective_score = cumulative_strength * edge_data["probability"]
        decayed_score = effective_score * (HOP_DECAY ** hop)

        if decayed_score < MIN_SCORE:
            continue

        # Only process if this path yields a higher score than any previous path
        if node in best_scores and best_scores[node] >= decayed_score:
            continue

        best_scores[node] = decayed_score
        result_map[node] = {
            "id": node,
            "label": _label(node),
            "score": round(decayed_score, 4),
            "hop": hop,
            "domain": edge_data.get("domain", "unknown"),
            "direction": edge_data.get("direction", "positive"),
            "parent": parent,
            "edge_strength": edge_data["strength"],
            "probability": edge_data["probability"],
        }

        for neighbor in graph.successors(node):
            next_edge = graph[node][neighbor]
            queue.append((neighbor, hop + 1, node, cumulative_strength, next_edge))

    # Return sorted by hop then descending score for consistent rendering
    results = list(result_map.values())
    results.sort(key=lambda x: (x["hop"], -x["score"]))
    return results


def _label(node_id: str) -> str:
    return node_id.replace("_", " ").title()
