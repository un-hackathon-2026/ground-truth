"""
End-to-end pipeline: natural-language query → MultiDatasetReport.

[User Query]
     │
     ▼ Step 1 — Query Parsing (LLM): classify topic + geography + time
     │  → StructuredQuery  (topic maps to 3-4 candidate indicators)
     │
     ▼ Step 2–4 repeated for EACH candidate indicator:
     │   Step 2 — Fetch data + metadata (World Bank API)
     │   Step 3 — Dimension scoring (deterministic)
     │   Step 4 — PASS/REJECT verdict + operational narration (LLM)
     │
     ▼ If ALL rejected: generate 2 actionable pivot suggestions (LLM)
     │
     → MultiDatasetReport shown to user
"""

from __future__ import annotations

from pydantic import ValidationError

from .fetch import fetch_by_code
from .parser import parse_query
from .schemas import (
    CandidateResult,
    DataQualityScore,
    DatasetInfo,
    DimensionScores,
    FetchError,
    FreshnessScore,
    MetadataCompletenessScore,
    MultiDatasetReport,
)
from .scoring import compute_dimension_scores
from .verdict import evaluate_candidate, generate_pivots, make_error_report

_NO_OBS_SCORES = DimensionScores(
    metadata_completeness=MetadataCompletenessScore(score=0.0, missing_fields=[], present_fields=[]),
    data_quality=DataQualityScore(score=0.0, issues=[]),
    freshness=FreshnessScore(score=0.0, days_since_update=None, note=""),
)


def run(raw_query: str) -> MultiDatasetReport:
    """
    Run the full multi-dataset pipeline.
    Never raises — all failure paths return a NOT_VIABLE MultiDatasetReport.
    """
    # Step 1 — Query Parsing
    try:
        structured = parse_query(raw_query)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(l) for l in first["loc"])
        return make_error_report(
            raw_query,
            f"Query parameters failed validation on field '{field}': {first['msg']}",
        )
    except RuntimeError as exc:
        return make_error_report(raw_query, f"Query parsing failed: {exc}")

    results: list[CandidateResult] = []

    for indicator_label, indicator_code in structured.candidates:
        api_url = (
            f"https://api.worldbank.org/v2/country/{structured.geography}"
            f"/indicator/{indicator_code}?format=json"
        )

        # Step 2 — Fetch
        fetch_result = fetch_by_code(
            geography=structured.geography,
            indicator_code=indicator_code,
            time_range=structured.time_range,
        )

        if isinstance(fetch_result, FetchError):
            results.append(CandidateResult(
                dataset_info=DatasetInfo(
                    indicator_name=indicator_label,
                    indicator_code=indicator_code,
                    geography=structured.geography,
                    api_url=api_url,
                ),
                dimension_scores=_NO_OBS_SCORES,
                verdict="REJECT",
                operational_explanation=f"Data fetch failed: {fetch_result.reason}",
            ))
            continue

        dataset, metadata = fetch_result

        if not dataset.rows:
            results.append(CandidateResult(
                dataset_info=DatasetInfo(
                    indicator_name=metadata.indicator_name or indicator_label,
                    indicator_code=indicator_code,
                    geography=structured.geography,
                    source_org=metadata.source_org,
                    api_url=api_url,
                    last_updated=metadata.last_updated,
                ),
                dimension_scores=_NO_OBS_SCORES,
                verdict="REJECT",
                operational_explanation=(
                    "No observations exist for the requested geography and time range. "
                    "The indicator is catalogued but contains no data for these parameters."
                ),
            ))
            continue

        # Step 3 — Dimension Scoring
        scores = compute_dimension_scores(dataset, metadata)

        years = [r.year for r in dataset.rows]
        dataset_info = DatasetInfo(
            indicator_name=metadata.indicator_name or indicator_label,
            indicator_code=indicator_code,
            geography=structured.geography,
            years_in_data=(min(years), max(years)),
            row_count=len(dataset.rows),
            non_null_count=sum(1 for r in dataset.rows if r.value is not None),
            source_org=metadata.source_org,
            api_url=api_url,
            last_updated=metadata.last_updated,
        )

        # Step 4 — Verdict + Operational Narration
        results.append(evaluate_candidate(dataset_info, scores))

    all_rejected = all(r.verdict == "REJECT" for r in results)
    overall_status = "NOT_VIABLE" if (all_rejected or not results) else "VIABLE"

    pivots: list[str] = []
    if all_rejected and results:
        pivots = generate_pivots(
            structured.topic,
            structured.geography,
            structured.time_range,
            results,
        )

    return MultiDatasetReport(
        query=raw_query,
        topic=structured.topic,
        geography=structured.geography,
        time_range=structured.time_range,
        candidates=results,
        overall_status=overall_status,
        pivots=pivots,
    )
