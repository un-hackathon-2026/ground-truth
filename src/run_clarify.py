"""Bridge script: generate a clarifying question (no data fetch)."""
import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read())
    query = (payload.get("query") or "").strip()
    if not query:
        print(json.dumps({"error": "query is required"}))
        sys.exit(1)

    from .agentic_pipeline import generate_clarification
    from . import usage_tracker
    result = generate_clarification(query)
    out = json.loads(result.model_dump_json())
    out["usage"] = usage_tracker.totals()
    print(json.dumps(out))


if __name__ == "__main__":
    main()
