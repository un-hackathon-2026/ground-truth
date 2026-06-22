"""
Cross-source layer (v2 increment) — UN Data Commons multi-source fetch
and discrepancy detection.

This is the piece flagged "out of scope for the MVP" in planning.md §6:
"Multi-source fetching and cross-source discrepancy detection."

KEY INSIGHT: the Commons returns MULTIPLE sources (facets) for the same
variable + entity in a SINGLE call. Each facet is an independent agency /
dataset (e.g. World Development Indicators vs national census vs UN IGME).
So conflict detection runs on one Commons response — no second API needed.

This module:
  1. fetches one variable for one country from the Commons (all facets)
  2. extracts each facet's latest value + provenance
  3. compares values across facets -> AGREE / CONFLICT / SINGLE_SOURCE / NO_DATA
  4. (optionally) asks Claude to narrate *why* sources differ, constrained
     to the facet metadata it is given (no speculation).

It produces a CrossSourceResult that the pipeline can attach to a
CandidateResult, OR fold into the verdict as a fourth signal.

Endpoint (no API key for Custom DC):
  https://cdc-un-cs-datacommons-web-service-620046630330.us-central1.run.app/core/api/v2/observation
"""

from __future__ import annotations

import json
import os
from typing import Literal, Optional

import requests
from pydantic import BaseModel

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

COMMONS_BASE = (
    "https://cdc-un-cs-datacommons-web-service-620046630330.us-central1.run.app"
    "/core/api"
)
OBS_ENDPOINT = f"{COMMONS_BASE}/v2/observation"
REQUEST_TIMEOUT = 25

# Relative gap above which two source values are considered in CONFLICT.
# 0.05 = 5%. A policy choice (documented, arguable) — same spirit as
# Dilasha's verdict thresholds: visible, not buried.
CONFLICT_REL_THRESHOLD = 0.05

# Map Dilasha's flat World Bank indicator codes (schemas.TOPIC_GROUPS)
# to the Commons aggregate variable (total / no demographic breakdown).
# Only codes that have a Commons equivalent are listed; others return
# NO_COMMONS_EQUIVALENT so we never fabricate a match.
WB_TO_COMMONS: dict[str, str] = {
    "SP.POP.TOTL": "Count_Person",                 # total population
    "SH.DYN.MORT": "undata/unicef/CME_MRY0T4",      # under-5 mortality (totals) *verify id*
    "SH.STA.MMRT": "undata/undp-hdro/GII_MMR",      # maternal mortality ratio *verify id*
    # add more as they are confirmed against the variable list:
    # "NY.GDP.PCAP.CD": "Amount_EconomicActivity_GrossDomesticProduction_..."
}


# --------------------------------------------------------------------------
# Schemas (extend Dilasha's contracts; do not modify hers)
# --------------------------------------------------------------------------

class SourceObservation(BaseModel):
    """One source's (facet's) latest value for a variable + country."""
    source_name: str                 # importName / provenance label
    provenance_url: Optional[str] = None
    measurement_method: Optional[str] = None
    observation_period: Optional[str] = None
    latest_year: Optional[int] = None
    value: Optional[float] = None


class CrossSourceResult(BaseModel):
    """Output of the cross-source check for one indicator + country."""
    indicator_code: str              # the WB code from the pipeline
    commons_variable: Optional[str]  # mapped Commons dcid, or None
    geography: str
    status: Literal[
        "AGREE", "CONFLICT", "SINGLE_SOURCE", "NO_DATA", "NO_COMMONS_EQUIVALENT"
    ]
    sources: list[SourceObservation] = []
    # 0-1, where 1.0 = all sources identical, lower = wider spread
    agreement_score: float = 1.0
    spread_pct: Optional[float] = None     # max relative gap between sources
    explanation: str = ""                  # plain-language, optional LLM


# --------------------------------------------------------------------------
# Fetch
# --------------------------------------------------------------------------

def _country_dcid(iso3: str) -> str:
    return f"country/{iso3.upper()}"


def fetch_commons_facets(
    commons_variable: str,
    iso3: str,
) -> list[SourceObservation]:
    """
    POST to the Commons observation endpoint and pull EVERY facet
    (every source) for this variable+country. Returns one
    SourceObservation per facet, using each facet's latest observation.

    Never raises — returns [] on any failure so the caller stays linear.
    """
    body = {
        "date": "",  # empty string = all observations (per Postman examples)
        "variable": {"dcids": [commons_variable]},
        "entity": {"dcids": [_country_dcid(iso3)]},
        "select": ["entity", "variable", "value", "date", "facet"],
    }
    try:
        resp = requests.post(OBS_ENDPOINT, json=body, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    # Response shape (confirmed via Postman collection / live Kenya pull):
    # data["byVariable"][var]["byEntity"][entity]["orderedFacets"] = [
    #    {"facetId": "...", "observations": [{"date": "2024", "value": ...}, ...]}, ...
    # ]
    # data["facets"][facetId] = {"importName":..., "provenanceUrl":...,
    #    "measurementMethod":..., "observationPeriod":...}
    facets_meta = data.get("facets", {}) or {}
    try:
        entity_block = (
            data["byVariable"][commons_variable]["byEntity"][_country_dcid(iso3)]
        )
    except (KeyError, TypeError):
        return []

    ordered = entity_block.get("orderedFacets", []) or []
    out: list[SourceObservation] = []

    for f in ordered:
        fid = str(f.get("facetId", ""))
        obs = f.get("observations", []) or []
        if not obs:
            continue
        # latest observation by year
        def _yr(o):
            try:
                return int(str(o.get("date", "0"))[:4])
            except (ValueError, TypeError):
                return 0
        latest = max(obs, key=_yr)
        meta = facets_meta.get(fid, {})

        val = latest.get("value")
        try:
            val = float(val) if val is not None else None
        except (ValueError, TypeError):
            val = None

        out.append(SourceObservation(
            source_name=meta.get("importName") or fid or "Unknown source",
            provenance_url=meta.get("provenanceUrl"),
            measurement_method=meta.get("measurementMethod"),
            observation_period=meta.get("observationPeriod"),
            latest_year=_yr(latest) or None,
            value=val,
        ))
    return out


# --------------------------------------------------------------------------
# Compare
# --------------------------------------------------------------------------

def _dedupe_sources(sources: list[SourceObservation]) -> list[SourceObservation]:
    """Drop facets with no value, and collapse exact duplicate (name,value)."""
    seen = set()
    out = []
    for s in sources:
        if s.value is None:
            continue
        key = (s.source_name, round(s.value, 6))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def compare_sources(
    indicator_code: str,
    commons_variable: Optional[str],
    iso3: str,
    sources: list[SourceObservation],
) -> CrossSourceResult:
    """
    Turn a list of source observations into a verdict on cross-source
    agreement. Deterministic — no LLM here (narration is separate).
    """
    if commons_variable is None:
        return CrossSourceResult(
            indicator_code=indicator_code, commons_variable=None,
            geography=iso3, status="NO_COMMONS_EQUIVALENT",
            explanation="No Commons variable is mapped for this indicator yet.",
        )

    usable = _dedupe_sources(sources)

    if not usable:
        return CrossSourceResult(
            indicator_code=indicator_code, commons_variable=commons_variable,
            geography=iso3, status="NO_DATA", sources=sources,
            explanation="No source returned a usable value for this variable and country.",
        )

    if len(usable) == 1:
        return CrossSourceResult(
            indicator_code=indicator_code, commons_variable=commons_variable,
            geography=iso3, status="SINGLE_SOURCE", sources=usable,
            agreement_score=1.0, spread_pct=0.0,
            explanation=f"Only one independent source available: {usable[0].source_name}.",
        )

    values = [s.value for s in usable if s.value is not None]
    vmin, vmax = min(values), max(values)
    denom = abs(vmax) if vmax != 0 else 1.0
    spread = (vmax - vmin) / denom          # relative gap, 0..1+
    agreement = max(0.0, 1.0 - spread)      # 1.0 = identical, lower = wider

    status = "CONFLICT" if spread > CONFLICT_REL_THRESHOLD else "AGREE"

    return CrossSourceResult(
        indicator_code=indicator_code, commons_variable=commons_variable,
        geography=iso3, status=status, sources=usable,
        agreement_score=round(agreement, 4),
        spread_pct=round(spread * 100, 2),
    )


# --------------------------------------------------------------------------
# Narrate (Claude — optional, constrained transcriber)
# --------------------------------------------------------------------------

_NARRATION_SYSTEM = (
    "You are a mechanical transcriber for a data-trust tool. You are given "
    "a JSON list of sources that report the same indicator for the same "
    "country, with their values, methods, and reference periods. In 2-3 "
    "sentences, state plainly whether they agree or disagree and, ONLY using "
    "the method/period fields provided, note the likely reason for any "
    "difference (e.g. different reference year, different measurement method). "
    "You are forbidden from inventing reasons not supported by the fields "
    "given. Do not recommend which source to trust — that is the human's "
    "decision."
)


def narrate_conflict(result: CrossSourceResult) -> str:
    """
    Optional: use Claude to phrase the conflict for the report.
    Falls back to a deterministic sentence if no API key is set.
    Requires ANTHROPIC_API_KEY.
    """
    if result.status in ("NO_DATA", "NO_COMMONS_EQUIVALENT", "SINGLE_SOURCE"):
        return result.explanation

    payload = {
        "indicator": result.indicator_code,
        "country": result.geography,
        "status": result.status,
        "spread_pct": result.spread_pct,
        "sources": [
            {
                "source": s.source_name,
                "value": s.value,
                "year": s.latest_year,
                "method": s.measurement_method,
                "period": s.observation_period,
            }
            for s in result.sources
        ],
    }

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Deterministic fallback — no LLM needed to ship.
        names = ", ".join(s.source_name for s in result.sources)
        if result.status == "CONFLICT":
            return (
                f"Sources disagree by {result.spread_pct}% on "
                f"{result.indicator_code} for {result.geography}. "
                f"Reporting sources: {names}. A human should pick which to trust."
            )
        return f"Sources agree (within {result.spread_pct}%): {names}."

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=200,
            system=_NARRATION_SYSTEM,
            messages=[{
                "role": "user",
                "content": "Sources:\n```json\n" + json.dumps(payload, indent=2) + "\n```",
            }],
        )
        return msg.content[0].text.strip()
    except Exception:
        names = ", ".join(s.source_name for s in result.sources)
        return f"{result.status}: {names} (spread {result.spread_pct}%)."


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def cross_source_check(
    indicator_code: str,
    iso3: str,
    narrate: bool = True,
) -> CrossSourceResult:
    """
    Full cross-source check for one of Dilasha's WB indicator codes.
    1. map WB code -> Commons variable
    2. fetch all facets (sources) from the Commons
    3. compare -> AGREE / CONFLICT / SINGLE_SOURCE / NO_DATA / NO_COMMONS_EQUIVALENT
    4. (optional) narrate with Claude
    """
    commons_var = WB_TO_COMMONS.get(indicator_code)
    if commons_var is None:
        return compare_sources(indicator_code, None, iso3, [])

    sources = fetch_commons_facets(commons_var, iso3)
    result = compare_sources(indicator_code, commons_var, iso3, sources)
    if narrate:
        result.explanation = narrate_conflict(result)
    return result


if __name__ == "__main__":
    # Smoke test — run from your machine where the Commons host is reachable.
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else "SP.POP.TOTL"
    iso = sys.argv[2] if len(sys.argv) > 2 else "KEN"
    res = cross_source_check(code, iso, narrate=True)
    print(json.dumps(res.model_dump(), indent=2))
