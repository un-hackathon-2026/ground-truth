"""
JSON bridge for the Next.js frontend — Phase 1 (candidate discovery).
Run as: python3 -m src.run_candidates
Reads: JSON on stdin  { "query": "..." }
Writes: CandidateList JSON on stdout
"""
from __future__ import annotations
import sys
import json

from dotenv import load_dotenv
load_dotenv()

from .agentic_pipeline import get_candidates_agentic


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

    result = get_candidates_agentic(query)
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
