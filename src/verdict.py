"""
Step 4 — Verdict Rule (deterministic) + Narration (LLM).

Threshold table (documented policy, not a black box):
┌──────────────────────┬──────────────────┬────────────┐
│ Condition            │ Threshold        │ Verdict    │
├──────────────────────┼──────────────────┼────────────┤
│ data_quality         │ < 0.6            │ REJECT     │
│ any other dimension  │ < 0.4            │ REJECT     │
│ otherwise            │ —                │ PASS       │
└──────────────────────┴──────────────────┴────────────┘

data_quality has a stricter floor: a well-documented bad dataset is still bad.
"""

from __future__ import annotations

import json
import os
from typing import Literal, Optional

import groq

from .schemas import (
    CandidateResult,
    DatasetInfo,
    DimensionScores,
    MultiDatasetReport,
    DataQualityScore,
    FreshnessScore,
    MetadataCompletenessScore,
)

DATA_QUALITY_FLOOR = 0.6
OTHER_FLOOR = 0.4

_CLIENT: Optional[groq.Groq] = None


def _client() -> groq.Groq:
    global _CLIENT
    if _CLIENT is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not set.")
        _CLIENT = groq.Groq(api_key=api_key)
    return _CLIENT


def apply_verdict_rule(scores: DimensionScores) -> Literal["PASS", "REJECT"]:
    if scores.data_quality.score < DATA_QUALITY_FLOOR:
        return "REJECT"
    if scores.metadata_completeness.score < OTHER_FLOOR:
        return "REJECT"
    if scores.freshness.score < OTHER_FLOOR:
        return "REJECT"
    return "PASS"


# ---------------------------------------------------------------------------
# Narration — operational consequences, not raw percentages
# ---------------------------------------------------------------------------

_NARRATION_SYSTEM = """You are a policy analyst writing a one-paragraph dataset evaluation note.

STRICT RULES:
1. Translate each score and issue into its OPERATIONAL CONSEQUENCE for someone trying to USE this data.
   - Do NOT write "completeness is 33%". DO write "four required metadata fields are absent, meaning automated pipelines cannot verify the unit of measurement or confirm redistribution rights."
   - Do NOT write "67% missing values". DO write "two-thirds of the requested time series has no observations, making any trend line statistically unreliable."
   - Do NOT write "updated 6 years ago". DO write "the most recent figures predate [specific period], so they cannot reflect conditions after that point."
2. Only reference facts present in the provided JSON. Do not speculate or add context.
3. Write 2–4 sentences. Be direct. Start with the verdict label."""

_PIVOT_SYSTEM = """You are a policy analyst suggesting fallback options when all datasets for a query are rejected.

OUTPUT FORMAT — MANDATORY:
- Output EXACTLY two lines.
- Each line is one complete sentence.
- Each sentence MUST start with an action verb (Expand / Switch / Request / Use / Contact / Try / Query).
- No introduction. No preamble. No numbering. No bullet points. No labels.
- Just the two sentences, one per line, nothing else.

CONTENT RULES:
- Base each suggestion on the specific failure reasons provided.
- Only reference sources, agencies, or time periods that are plausible and specific.
- Do not give generic advice."""


def narrate_candidate(
    dataset_info: DatasetInfo,
    scores: DimensionScores,
    verdict: str,
) -> str:
    evidence = {
        "verdict": verdict,
        "indicator": dataset_info.indicator_name or dataset_info.indicator_code,
        "geography": dataset_info.geography,
        "period": (
            f"{dataset_info.years_in_data[0]}–{dataset_info.years_in_data[1]}"
            if dataset_info.years_in_data else "unknown"
        ),
        "observations_total": dataset_info.row_count,
        "observations_with_values": dataset_info.non_null_count,
        "last_updated": dataset_info.last_updated,
        "metadata_completeness": {
            "score": scores.metadata_completeness.score,
            "missing_fields": scores.metadata_completeness.missing_fields,
        },
        "data_quality": {
            "score": scores.data_quality.score,
            "issues": scores.data_quality.issues,
        },
        "freshness": {
            "score": scores.freshness.score,
            "note": scores.freshness.note,
        },
    }

    prompt = (
        "Write the evaluation note for this dataset. Translate every metric into "
        "its operational consequence. Do not repeat raw percentages.\n\n"
        f"```json\n{json.dumps(evidence, indent=2)}\n```"
    )

    resp = _client().chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=350,
        messages=[
            {"role": "system", "content": _NARRATION_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content.strip()


def generate_pivots(
    topic: str,
    geography: str,
    time_range: Optional[tuple[int, int]],
    candidates: list[CandidateResult],
) -> list[str]:
    """Generate 2 actionable pivot suggestions when every candidate is rejected."""
    failure_summary = []
    for c in candidates:
        issues = []
        if c.dimension_scores.metadata_completeness.score < OTHER_FLOOR:
            issues.append(
                f"missing metadata fields: {c.dimension_scores.metadata_completeness.missing_fields}"
            )
        if c.dimension_scores.data_quality.score < DATA_QUALITY_FLOOR:
            issues.append(
                f"data quality issues: {c.dimension_scores.data_quality.issues}"
            )
        if c.dimension_scores.freshness.score < OTHER_FLOOR:
            issues.append(f"stale data — {c.dimension_scores.freshness.note}")
        if not c.dimension_scores.data_quality.issues and c.dataset_info.non_null_count == 0:
            issues.append("no observations available for the requested period")
        failure_summary.append({
            "indicator": c.dataset_info.indicator_name or c.dataset_info.indicator_code,
            "rejection_reasons": issues,
            "data_available": (
                f"{c.dataset_info.years_in_data[0]}–{c.dataset_info.years_in_data[1]}"
                if c.dataset_info.years_in_data else "none"
            ),
        })

    evidence = {
        "topic": topic,
        "geography": geography,
        "requested_time_range": (
            f"{time_range[0]}–{time_range[1]}" if time_range else "not specified"
        ),
        "all_candidates_rejected": failure_summary,
    }

    prompt = (
        "All candidate datasets for this query were rejected. "
        "Suggest exactly 2 actionable pivots the analyst can take.\n\n"
        f"```json\n{json.dumps(evidence, indent=2)}\n```"
    )

    resp = _client().chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=200,
        messages=[
            {"role": "system", "content": _PIVOT_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )

    raw = resp.choices[0].message.content.strip()
    # Keep only lines that look like actionable sentences (start with a capital,
    # are long enough to be a real sentence, and aren't preamble/labels).
    _SKIP_PREFIXES = ("here are", "below are", "pivot", "note:", "option")
    lines = []
    for ln in raw.splitlines():
        cleaned = ln.strip(" \t•-–*123456789.)>")
        if (
            len(cleaned) > 20
            and not any(cleaned.lower().startswith(p) for p in _SKIP_PREFIXES)
        ):
            lines.append(cleaned)
    return lines[:2] if len(lines) >= 2 else [raw]


def evaluate_candidate(
    dataset_info: DatasetInfo,
    scores: DimensionScores,
) -> CandidateResult:
    verdict = apply_verdict_rule(scores)
    explanation = narrate_candidate(dataset_info, scores, verdict)
    return CandidateResult(
        dataset_info=dataset_info,
        dimension_scores=scores,
        verdict=verdict,
        operational_explanation=explanation,
    )


def make_error_report(query: str, reason: str) -> MultiDatasetReport:
    """Fast-fail report when parsing fails before any dataset can be evaluated."""
    empty_scores = DimensionScores(
        metadata_completeness=MetadataCompletenessScore(
            score=0.0, missing_fields=[], present_fields=[]
        ),
        data_quality=DataQualityScore(score=0.0, issues=[]),
        freshness=FreshnessScore(score=0.0, days_since_update=None, note=""),
    )
    return MultiDatasetReport(
        query=query,
        topic="unknown",
        geography="unknown",
        time_range=None,
        candidates=[],
        overall_status="NOT_VIABLE",
        pivots=[],
        parse_error=reason,
    )
