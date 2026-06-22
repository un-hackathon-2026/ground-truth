"""
Cross-source integration (Chichi) — wires the conflict layer into the pipeline.

Provides three things the pipeline needs:
  1. to_cross_source_dimension()  — turn a CrossSourceResult into the 4th
                                     DimensionScores field.
  2. extended_verdict()           — fold the 4th dimension into a 3-state
                                     verdict: PASS / REVIEW / REJECT.
  3. chain_recommendations()      — the "want a neighbouring country?" follow-up.

Design decisions (documented, arguable — same spirit as the planning doc):
  - A cross-source CONFLICT does NOT auto-REJECT. The data may be perfectly
    fine; the sources just disagree and a human must choose. So CONFLICT maps
    to REVIEW (route to human-in-the-loop), not REJECT.
  - SINGLE_SOURCE / NO_DATA / NO_COMMONS_EQUIVALENT never make the verdict
    worse — absence of a second source is not evidence of a problem. They
    leave the original 3-dimension verdict intact.
  - Non-authoritative sources (Wikipedia/Wikidata) are counted separately so a
    conflict driven only by crowd-sourced data can be down-weighted.
"""

from __future__ import annotations

from typing import Literal

from .schemas import (
    CrossSourceScore,
    DimensionScores,
    ChainRecommendation,
    NEIGHBOURS,
    TOPIC_GROUPS,
)
from .fetch_commons import CrossSourceResult  # the standalone layer

# Sources we treat as non-authoritative (crowd-sourced, not official statistics)
NON_AUTHORITATIVE = ("wikipedia", "wikidata")


def _is_authoritative(source_name: str) -> bool:
    low = (source_name or "").lower()
    return not any(tag in low for tag in NON_AUTHORITATIVE)


def to_cross_source_dimension(result: CrossSourceResult) -> CrossSourceScore:
    """Convert the standalone CrossSourceResult into the 4th dimension."""
    auth = sum(1 for s in result.sources if _is_authoritative(s.source_name))
    return CrossSourceScore(
        score=result.agreement_score,
        status=result.status,
        spread_pct=result.spread_pct,
        source_count=len(result.sources),
        authoritative_count=auth,
        note=result.explanation,
    )


# Floor below which agreement is bad enough to matter (policy choice).
CROSS_SOURCE_AGREEMENT_FLOOR = 0.6


def extended_verdict(
    base_verdict: Literal["PASS", "REJECT"],
    scores: DimensionScores,
) -> Literal["PASS", "REVIEW", "REJECT"]:
    """
    Combine the existing 3-dimension verdict with the cross-source dimension.

    Rules:
      - If the 3-dim rule already says REJECT, stay REJECT (bad data is bad
        regardless of how many sources agree on it).
      - If sources CONFLICT (and the disagreement involves >1 authoritative
        source), downgrade a PASS to REVIEW — route to a human to pick.
      - Otherwise keep the base verdict.
    """
    if base_verdict == "REJECT":
        return "REJECT"

    cs = scores.cross_source
    if cs is None:
        return base_verdict  # no cross-source info → unchanged

    if cs.status == "CONFLICT" and cs.authoritative_count >= 2:
        return "REVIEW"

    # conflict driven ONLY by non-authoritative sources → note it, but still PASS
    return base_verdict


def chain_recommendations(
    topic: str,
    geography: str,
    max_items: int = 3,
) -> list[ChainRecommendation]:
    """
    The 'want a neighbouring country?' chain. After answering for one country,
    suggest the same topic for neighbours so the user can compare across a
    region. Deterministic, grounded in the NEIGHBOURS map — no LLM needed.
    """
    from .schemas import country_name
    iso = geography.upper()
    here = country_name(iso)
    neighbours = NEIGHBOURS.get(iso, [])
    out: list[ChainRecommendation] = []
    for nb in neighbours[:max_items]:
        nb_name = country_name(nb)
        out.append(ChainRecommendation(
            label=f"Compare {topic} with {nb_name} ({nb})",
            geography=nb,
            topic=topic,
            reason=f"{nb_name} borders {here} — comparing the same indicator "
                   "across neighbours reveals regional patterns and outliers.",
        ))
    return out
