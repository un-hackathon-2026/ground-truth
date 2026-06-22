"""
Bridge script: find ALL candidates for a (query + context) and evaluate every one.

Stdin:  { "query": "...", "context": "..." }
Stdout: MultiDatasetReport JSON
"""
import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read())
    query = (payload.get("query") or "").strip()
    context = (payload.get("context") or "").strip()
    if not query:
        print(json.dumps({"error": "query is required"}))
        sys.exit(1)

    # Combine original query with the user's clarification context
    refined = f"{query} — specifically: {context}" if context else query

    from .agentic_pipeline import get_candidates_agentic, evaluate_agentic

    # Phase 1: discover all candidates for the refined query
    candidates = get_candidates_agentic(refined)

    if candidates.parse_error:
        from .schemas import MultiDatasetReport
        fallback = MultiDatasetReport(
            query=refined, topic="unknown", geography="unknown",
            time_range=None, candidates=[], overall_status="NOT_VIABLE",
            parse_error=candidates.parse_error,
        )
        print(fallback.model_dump_json())
        return

    if not candidates.options:
        from .schemas import MultiDatasetReport
        fallback = MultiDatasetReport(
            query=refined, topic=candidates.topic, geography=candidates.geography,
            time_range=candidates.time_range, candidates=[], overall_status="NOT_VIABLE",
            parse_error="No matching datasets found in the UN Data Commons.",
        )
        print(fallback.model_dump_json())
        return

    all_codes = [o.indicator_code for o in candidates.options]
    labels = {o.indicator_code: o.indicator_name for o in candidates.options}

    # Phase 2: evaluate every candidate (no user selection)
    report = evaluate_agentic(refined, selected_codes=all_codes, labels=labels)
    from . import usage_tracker
    out = json.loads(report.model_dump_json())
    out["usage"] = usage_tracker.totals()
    print(json.dumps(out))


if __name__ == "__main__":
    main()
