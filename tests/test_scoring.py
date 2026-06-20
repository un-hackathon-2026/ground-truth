"""
Unit tests for Step 3 — Dimension Scoring.

Run with: python -m pytest tests/test_scoring.py -v
Tests are self-contained: no API calls, no LLM calls, no external dependencies.
"""

import datetime
import json
from pathlib import Path

import pytest

from src.schemas import DataRow, RawDataset, RawMetadata
from src.scoring import (
    FRESHNESS_STALE_SCORE,
    score_data_quality,
    score_freshness,
    score_metadata_completeness,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_metadata(key: str) -> RawMetadata:
    raw = json.loads((FIXTURE_DIR / "sample_metadata.json").read_text())
    return RawMetadata(**raw[key])


def make_dataset(rows: list[tuple[int, float | None]]) -> RawDataset:
    return RawDataset(
        indicator_code="SI.POV.NAHC",
        geography="KEN",
        rows=[DataRow(year=y, value=v) for y, v in rows],
    )


# ---------------------------------------------------------------------------
# Metadata completeness
# ---------------------------------------------------------------------------

class TestMetadataCompleteness:
    def test_full_metadata_scores_one(self):
        meta = load_metadata("full")
        result = score_metadata_completeness(meta)
        assert result.score == 1.0
        assert result.missing_fields == []
        assert len(result.present_fields) == 6

    def test_partial_metadata_scores_correctly(self):
        meta = load_metadata("partial")
        result = score_metadata_completeness(meta)
        # unit + source_org present; methodology_note, time_coverage,
        # geography_coverage, license missing → 2/6
        assert result.score == pytest.approx(2 / 6, abs=1e-4)
        assert "methodology_note" in result.missing_fields
        assert "license" in result.missing_fields
        assert "unit" in result.present_fields

    def test_minimal_metadata_scores_near_zero(self):
        meta = load_metadata("minimal")
        result = score_metadata_completeness(meta)
        assert result.score == 0.0
        assert len(result.missing_fields) == 6


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------

class TestDataQuality:
    def test_clean_data_scores_one(self):
        dataset = make_dataset([(2018, 38.2), (2019, 36.1), (2020, 35.8)])
        result = score_data_quality(dataset)
        assert result.score == 1.0
        assert result.issues == []

    def test_half_null_penalises_score(self):
        dataset = make_dataset([(2018, 38.2), (2019, None), (2020, None)])
        result = score_data_quality(dataset)
        assert result.score < 1.0
        assert any("missing" in i for i in result.issues)

    def test_duplicate_years_penalise_score(self):
        dataset = make_dataset([(2018, 38.2), (2018, 39.0), (2019, 36.1)])
        result = score_data_quality(dataset)
        assert result.score < 1.0
        assert any("duplicate" in i.lower() for i in result.issues)

    def test_negative_values_flagged(self):
        dataset = make_dataset([(2018, -5.0), (2019, 36.1)])
        result = score_data_quality(dataset)
        assert any("negative" in i.lower() for i in result.issues)

    def test_empty_dataset_scores_zero(self):
        dataset = make_dataset([])
        result = score_data_quality(dataset)
        assert result.score == 0.0
        assert result.issues  # must explain why


# ---------------------------------------------------------------------------
# Freshness
# ---------------------------------------------------------------------------

class TestFreshness:
    def test_recent_update_scores_one(self):
        meta = RawMetadata(
            indicator_code="X",
            last_updated=str(datetime.date.today().year),
        )
        result = score_freshness(meta)
        assert result.score == 1.0
        assert result.days_since_update is not None

    def test_three_year_old_update_scores_midrange(self):
        three_years_ago = str(datetime.date.today().year - 3)
        meta = RawMetadata(indicator_code="X", last_updated=three_years_ago)
        result = score_freshness(meta)
        assert result.score == 0.6

    def test_six_year_old_update_scores_low(self):
        six_years_ago = str(datetime.date.today().year - 6)
        meta = RawMetadata(indicator_code="X", last_updated=six_years_ago)
        result = score_freshness(meta)
        assert result.score == FRESHNESS_STALE_SCORE

    def test_missing_last_updated_scores_zero(self):
        meta = RawMetadata(indicator_code="X", last_updated=None)
        result = score_freshness(meta)
        assert result.score == 0.0
        assert result.days_since_update is None
        assert "No last_updated" in result.note

    def test_unparseable_date_scores_zero(self):
        meta = RawMetadata(indicator_code="X", last_updated="not-a-date")
        result = score_freshness(meta)
        assert result.score == 0.0


# ---------------------------------------------------------------------------
# Verdict rule (imported from verdict module, tested here for completeness)
# ---------------------------------------------------------------------------

class TestVerdictRule:
    def _scores(self, mc: float, dq: float, fr: float):
        from src.schemas import (
            DataQualityScore,
            DimensionScores,
            FreshnessScore,
            MetadataCompletenessScore,
        )
        return DimensionScores(
            metadata_completeness=MetadataCompletenessScore(
                score=mc, missing_fields=[], present_fields=[]
            ),
            data_quality=DataQualityScore(score=dq, issues=[]),
            freshness=FreshnessScore(score=fr, days_since_update=None, note=""),
        )

    def test_all_high_gives_pass(self):
        from src.verdict import apply_verdict_rule
        assert apply_verdict_rule(self._scores(0.8, 0.9, 0.8)) == "PASS"

    def test_data_quality_below_floor_gives_reject(self):
        from src.verdict import apply_verdict_rule
        assert apply_verdict_rule(self._scores(1.0, 0.5, 1.0)) == "REJECT"

    def test_completeness_below_floor_gives_reject(self):
        from src.verdict import apply_verdict_rule
        assert apply_verdict_rule(self._scores(0.3, 0.9, 0.9)) == "REJECT"

    def test_mid_scores_above_floor_gives_pass(self):
        from src.verdict import apply_verdict_rule
        assert apply_verdict_rule(self._scores(0.5, 0.7, 0.6)) == "PASS"
