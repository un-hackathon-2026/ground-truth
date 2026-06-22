"""
Session-scoped token usage accumulator.

Each bridge script (run_*.py) runs as its own process, so this module
resets automatically per invocation — no cross-request bleed.
"""

_log: list[dict] = []

# llama-3.3-70b-versatile Groq pricing (USD per token)
_PRICE_INPUT  = 0.59 / 1_000_000
_PRICE_OUTPUT = 0.79 / 1_000_000


def record(prompt_tokens: int, completion_tokens: int) -> None:
    _log.append({"p": int(prompt_tokens or 0), "c": int(completion_tokens or 0)})


def totals() -> dict:
    p = sum(u["p"] for u in _log)
    c = sum(u["c"] for u in _log)
    cost = p * _PRICE_INPUT + c * _PRICE_OUTPUT
    return {
        "prompt_tokens": p,
        "completion_tokens": c,
        "total_tokens": p + c,
        "estimated_cost_usd": round(cost, 6),
    }
