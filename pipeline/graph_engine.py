import json
from pathlib import Path
import networkx as nx


def build_graph_from_rules(rules: list[dict]) -> nx.DiGraph:
    G = nx.DiGraph()
    for rule in rules:
        G.add_edge(
            rule["from"],
            rule["to"],
            strength=rule["strength"],
            probability=rule["probability"],
            direction=rule["direction"],
            lag_days=rule["lag_days"],
            domain=rule["domain"],
            description=rule.get("description", ""),
        )
    return G


def load_causal_graph() -> tuple[nx.DiGraph, list[dict]]:
    """Load causal_rules.json and return (DiGraph, raw rules list)."""
    rules_path = Path(__file__).parent.parent / "data" / "causal_rules.json"
    with open(rules_path, encoding="utf-8") as fh:
        data = json.load(fh)
    rules: list[dict] = data["rules"]
    graph = build_graph_from_rules(rules)
    return graph, rules


def get_all_source_nodes(rules: list[dict]) -> list[str]:
    """Return deduplicated list of all 'from' nodes — valid propagation roots."""
    seen: set[str] = set()
    result: list[str] = []
    for rule in rules:
        node = rule["from"]
        if node not in seen:
            seen.add(node)
            result.append(node)
    return result
