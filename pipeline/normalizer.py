import os
from groq import Groq
from thefuzz import process as fuzz_process

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def normalize_event(raw_event: str, available_nodes: list[str]) -> str:
    """Map a raw event phrase to the closest canonical node name via LLM + fuzzy fallback."""
    nodes_str = "\n".join(f"- {n}" for n in available_nodes)

    system_prompt = (
        "You are an event normalization engine. Given a raw event description "
        "and a list of canonical node names, return EXACTLY one canonical node "
        "name from the list that best matches the event. "
        "Do not invent new names. Do not add any explanation.\n\n"
        f"Canonical nodes:\n{nodes_str}"
    )

    response = _get_client().chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Raw event: {raw_event}"},
        ],
        temperature=0.0,
    )

    candidate = (response.choices[0].message.content or "").strip()

    # Direct match — trust the LLM
    if candidate in available_nodes:
        return candidate

    # Fuzzy fallback — the LLM returned something close but not exact
    best_match, score = fuzz_process.extractOne(candidate, available_nodes)
    if score >= 50:
        return best_match

    # Last resort — fuzzy match raw_event directly against nodes
    best_match, _ = fuzz_process.extractOne(raw_event.upper(), available_nodes)
    return best_match
