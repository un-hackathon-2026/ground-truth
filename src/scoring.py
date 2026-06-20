"""
Step 3 — Dimension Scoring (deterministic, no LLM).

Three independent scoring functions. Each score is traceable to a specific
field or check; if a check can't run because data/metadata is absent, the
dimension scores 0.0 with an explicit reason — never silently skipped.
"""

from __future__ import annotations

import datetime
from typing import Optional

import pandas as pd

from .schemas import (
    DataQualityScore,
    DimensionScores,
    FreshnessScore,
    MetadataCompletenessScore,
    RawDataset,
    RawMetadata,
)

# Required metadata fields and the attribute on RawMetadata that holds each.
REQUIRED_METADATA_FIELDS: list[tuple[str, str]] = [
    ("unit", "unit"),
    ("source_org", "source_org"),
    ("methodology_note", "methodology_note"),
    ("time_coverage", "time_coverage"),
    ("geography_coverage", "geography_coverage"),
    ("license", "license"),
]

# Freshness thresholds (days).
# A policy choice — documented here, not buried in an if-chain.
# | Updated within | Score |
# |----------------|-------|
# | 2 years        | 1.0   |
# | 5 years        | 0.6   |
# | > 5 years      | 0.2   |
FRESHNESS_THRESHOLDS: list[tuple[int, float]] = [
    (365 * 2, 1.0),
    (365 * 5, 0.6),
]
FRESHNESS_STALE_SCORE = 0.2


def score_metadata_completeness(metadata: RawMetadata) -> MetadataCompletenessScore:
    """
    Score = present_required_fields / total_required_fields.
    Missing list becomes the raw evidence for Step 4's caveat text.
    """
    present: list[str] = []
    missing: list[str] = []

    for field_label, attr in REQUIRED_METADATA_FIELDS:
        value = getattr(metadata, attr, None)
        if value and str(value).strip():
            present.append(field_label)
        else:
            missing.append(field_label)

    score = len(present) / len(REQUIRED_METADATA_FIELDS) if REQUIRED_METADATA_FIELDS else 0.0
    return MetadataCompletenessScore(
        score=round(score, 4),
        missing_fields=missing,
        present_fields=present,
    )


def score_data_quality(dataset: RawDataset) -> DataQualityScore:
    """
    Three cheap, explainable checks:
    1. Null/missing value rate
    2. Duplicate year detection
    3. Basic range/sanity check (values must be non-negative; rates must be ≤ 100)

    Final score = mean of per-check sub-scores. Issues list is the evidence.
    """
    rows = dataset.rows
    if not rows:
        # Should not reach here (Step 2 short-circuits on 0 rows), but fail loudly.
        return DataQualityScore(
            score=0.0,
            issues=["No data rows — cannot assess quality."],
        )

    df = pd.DataFrame([{"year": r.year, "value": r.value} for r in rows])
    issues: list[str] = []
    sub_scores: list[float] = []

    # 1. Null rate
    null_count = df["value"].isna().sum()
    null_rate = null_count / len(df)
    null_score = 1.0 - null_rate
    sub_scores.append(null_score)
    if null_rate > 0:
        issues.append(
            f"{null_count} of {len(df)} observations ({null_rate:.0%}) have missing values."
        )

    # 2. Duplicate years
    dupe_count = df["year"].duplicated().sum()
    dupe_score = 0.0 if dupe_count > 0 else 1.0
    sub_scores.append(dupe_score)
    if dupe_count > 0:
        issues.append(f"{dupe_count} duplicate year(s) found in the dataset.")

    # 3. Range/sanity check (non-negative; rates and percentages must be ≤ 100)
    non_null = df["value"].dropna()
    negative_count = (non_null < 0).sum()
    over_100_count = (non_null > 100).sum()

    # Over-100 is only invalid for percentage-type indicators. For raw counts
    # (GDP, population) it's expected. We flag it but don't penalise as hard.
    range_issues: list[str] = []
    if negative_count > 0:
        range_issues.append(
            f"{negative_count} observation(s) have negative values, which are invalid for this indicator."
        )
    # Only flag >100 if ALL non-null values are ≤ 100 would be expected —
    # we can't know for certain without the indicator type, so we note it softly.
    if over_100_count > 0 and over_100_count == len(non_null):
        range_issues.append(
            f"All {over_100_count} non-null values exceed 100 — "
            "unexpected if this is a percentage indicator."
        )

    range_score = 1.0 if not range_issues else max(0.0, 1.0 - 0.3 * len(range_issues))
    sub_scores.append(range_score)
    issues.extend(range_issues)

    final_score = sum(sub_scores) / len(sub_scores)
    return DataQualityScore(score=round(final_score, 4), issues=issues)


def score_freshness(metadata: RawMetadata) -> FreshnessScore:
    """
    Flat threshold rule (v1 — not indicator-specific, noted as v2 refinement).
    If last_updated is absent, score 0.0 and record why.
    """
    if not metadata.last_updated:
        return FreshnessScore(
            score=0.0,
            days_since_update=None,
            note="No last_updated date available in metadata.",
        )

    update_date = _parse_date(metadata.last_updated)
    if update_date is None:
        return FreshnessScore(
            score=0.0,
            days_since_update=None,
            note=f"Could not parse last_updated value: '{metadata.last_updated}'.",
        )

    today = datetime.date.today()
    days = (today - update_date).days

    score = FRESHNESS_STALE_SCORE
    for threshold_days, threshold_score in FRESHNESS_THRESHOLDS:
        if days <= threshold_days:
            score = threshold_score
            break

    age_str = f"{days} days" if days < 365 else f"{days // 365} year(s)"
    return FreshnessScore(
        score=score,
        days_since_update=days,
        note=f"Last updated {age_str} ago ({metadata.last_updated}).",
    )


def compute_dimension_scores(dataset: RawDataset, metadata: RawMetadata) -> DimensionScores:
    return DimensionScores(
        metadata_completeness=score_metadata_completeness(metadata),
        data_quality=score_data_quality(dataset),
        freshness=score_freshness(metadata),
    )


def _parse_date(value: str) -> Optional[datetime.date]:
    """Try common date formats against the full string; return None if none match."""
    stripped = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y"):
        try:
            return datetime.datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue
    return None
