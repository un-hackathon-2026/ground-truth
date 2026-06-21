"""
End-to-end pipeline: natural-language query -> MultiDatasetReport.

MODIFIED (Chichi): after the 3 dimensions are scored for each candidate, the
cross-source layer runs (Commons multi-source check) and becomes the 4th
dimension; the verdict is extended to PASS / REVIEW / REJECT; and chain
recommendations (neighbouring countries) are attached to the report.

The cross-source step is wrapped in try/except and is fully optional — if the
Commons is unreachable or the indicator has no Commons equivalent, the pipeline
falls back to the original 3-dimension behaviour. It can never crash the run.
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

# NEW imports — cross-source layer + integration helpers
from .fetch_commons import cross_source_check
from .integrate import (
    to_cross_source_dimension,
    extended_verdict,
    chain_recommendations,
)

_NO_OBS_SCORES = DimensionScores(
    metadata_completeness=MetadataCompletenessScore(score=0.0, missing_fields=[], present_fields=[]),
    data_quality=DataQualityScore(score=0.0, issues=[]),
    freshness=FreshnessScore(score=0.0, days_since_update=None, note=""),
)


def _attach_cross_source(candidate: CandidateResult) -> CandidateResult:
    """
    Run the cross-source check for this candidate's indicator, attach it as the
    4th dimension, and upgrade the verdict to PASS/REVIEW/REJECT.
    Fully defensive: any failure leaves the candidate unchanged.
    """
    try:
        result = cross_source_check(
            indicator_code=candidate.dataset_info.indicator_code,
            iso3=candidate.dataset_info.geography,
            narrate=False,   # keep deterministic in the pipeline; UI can narrate
        )
        dim = to_cross_source_dimension(result)
        candidate.dimension_scores.cross_source = dim
        candidate.verdict = extended_verdict(candidate.verdict, candidate.dimension_scores)
        # If it became REVIEW, surface that in the explanation.
        if candidate.verdict == "REVIEW":
            candidate.operational_explanation = (
                "NEEDS HUMAN REVIEW — independent sources disagree on this value "
                f"(spread {dim.spread_pct}% across {dim.authoritative_count} "
                "authoritative sources). The data itself may be sound, but a person "
                "should choose which source to trust. "
                + candidate.operational_explanation
            )
    except Exception:
        # Cross-source is additive; never let it break the base pipeline.
        pass
    return candidate


def run(raw_query: str) -> MultiDatasetReport:
    """Run the full multi-dataset pipeline (now with the 4th dimension + chain)."""
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

        fetch_result = fetch_by_code(
            geography=structured.geography,
            indicator_code=indicator_code,
            time_range=structured.time_range,
        )

        if isinstance(fetch_result, FetchError):
            results.append(CandidateResult(
                dataset_info=DatasetInfo(
                    indicator_name=indicator_label, indicator_code=indicator_code,
                    geography=structured.geography, api_url=api_url,
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
                    indicator_code=indicator_code, geography=structured.geography,
                    source_org=metadata.source_org, api_url=api_url,
                    last_updated=metadata.last_updated,
                ),
                dimension_scores=_NO_OBS_SCORES,
                verdict="REJECT",
                operational_explanation=(
                    "No observations exist for the requested geography and time range."
                ),
            ))
            continue

        scores = compute_dimension_scores(dataset, metadata)
        years = [r.year for r in dataset.rows]
        dataset_info = DatasetInfo(
            indicator_name=metadata.indicator_name or indicator_label,
            indicator_code=indicator_code, geography=structured.geography,
            years_in_data=(min(years), max(years)),
            row_count=len(dataset.rows),
            non_null_count=sum(1 for r in dataset.rows if r.value is not None),
            source_org=metadata.source_org, api_url=api_url,
            last_updated=metadata.last_updated,
        )

        candidate = evaluate_candidate(dataset_info, scores)   # base 3-dim verdict
        candidate = _attach_cross_source(candidate)            # + 4th dimension
        results.append(candidate)

    # Overall status: any PASS or REVIEW counts as viable (REVIEW = usable w/ a human)
    usable = any(r.verdict in ("PASS", "REVIEW") for r in results)
    overall_status = "VIABLE" if (usable and results) else "NOT_VIABLE"

    pivots: list[str] = []
    if not usable and results:
        pivots = generate_pivots(
            structured.topic, structured.geography, structured.time_range, results,
        )

    # NEW — chain recommendations (neighbouring countries, same topic)
    chain = chain_recommendations(structured.topic, structured.geography)

    return MultiDatasetReport(
        query=raw_query, topic=structured.topic, geography=structured.geography,
        time_range=structured.time_range, candidates=results,
        overall_status=overall_status, pivots=pivots, chain=chain,
    )
