"""
JSON bridge for the Next.js frontend — Phase 2 (trust evaluation).
Run as: python3 -m src.run_evaluate
Reads: JSON on stdin  { "query": "...", "selected_codes": [...], "labels": {...} }
Writes: MultiDatasetReport JSON on stdout
"""
from __future__ import annotations
import sys
import json

from dotenv import load_dotenv
load_dotenv()

from .agentic_pipeline import evaluate_agentic


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON input: {exc}"}))
        sys.exit(1)

    query = (payload.get("query") or "").strip()
    if not query:
        print(json.dumps({"error": "query field is required"}))
        sys.exit(1)

    selected_codes: list[str] = payload.get("selected_codes") or []
    labels: dict[str, str] = payload.get("labels") or {}

    result = evaluate_agentic(
        query,
        selected_codes=selected_codes or None,
        labels=labels or None,
    )
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
