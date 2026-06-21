"""
agentic_pipeline.py — Commons-native agentic pipeline (Chichi).

This is the full agentic flow the Challenge-3 brief asks for:
  discovery -> verification -> explanation -> output, evidence chain visible.

It is SEPARATE from the original World-Bank pipeline (pipeline.py) on purpose:
the existing pipeline keeps working untouched; this is the Commons-native path.

Flow:
  1. parse_concept(query)          -> concept + geography + time   (LLM, light)
  2. find_indicators(concept)      -> live Commons candidates       (agentic search)
  3. [user picks a variable_id]
  4. evaluate_agentic(...)         -> fetch that Commons variable,
                                      score 4 dimensions, verdict, chain

Reuses what already works:
  - commons_search.find_indicators   (Commons search + LLM grouping)
  - fetch_commons.fetch_commons_facets (Commons observation fetch + provenance)
  - scoring.compute_dimension_scores   (metadata / quality / freshness)
  - integrate.* + verdict.*            (4th dimension, PASS/REVIEW/REJECT, chain)

Confirmed live response shape (probe_obs.py):
  facets[fid] = {importName, provenanceUrl, measurementMethod?, unit?, observationPeriod?}
  byVariable[var].byEntity[ent].orderedFacets[i] = {facetId, observations:[{date,value}]}
"""

from __future__ import annotations

import json
import os
from typing import Optional

import groq

from .schemas import (
    DataRow, RawDataset, RawMetadata, DatasetInfo, DimensionScores,
    MetadataCompletenessScore, DataQualityScore, FreshnessScore,
    CandidateResult, MultiDatasetReport, CandidateList, CandidateOption,
    country_name,
)
from .scoring import compute_dimension_scores
from .verdict import evaluate_candidate
from .fetch_commons import fetch_commons_facets, cross_source_check, OBS_ENDPOINT
from .integrate import (
    to_cross_source_dimension, extended_verdict, chain_recommendations,
)
from .commons_search import find_indicators

import requests

REQUEST_TIMEOUT = 25
_CLIENT: Optional[groq.Groq] = None


def commons_request(variable_id: str, iso3: str) -> dict:
    """
    The REAL, callable Commons observation request for a variable + country.
    Returns everything the front-end needs to fetch this data itself:
      - method: POST
      - url:    the observation endpoint
      - body:   the exact JSON payload to POST
    The Commons observation endpoint is POST (not a GET URL like World Bank),
    so we hand over the endpoint + body rather than a clickable link.
    """
    return {
        "method": "POST",
        "url": OBS_ENDPOINT,
        "body": {
            "date": "",
            "variable": {"dcids": [variable_id]},
            "entity": {"dcids": [f"country/{iso3.upper()}"]},
            "select": ["entity", "variable", "value", "date", "facet"],
        },
    }


# ===========================================================================
# Step 1 — lightweight concept parse (no topic enum; free-form concept)
# ===========================================================================

def _client() -> groq.Groq:
    global _CLIENT
    if _CLIENT is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY not set.")
        _CLIENT = groq.Groq(api_key=key)
    return _CLIENT


_CONCEPT_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_concept",
        "description": "Extract the data concept, country, and years from a question.",
        "parameters": {
            "type": "object",
            "properties": {
                "concept": {"type": "string",
                    "description": "The statistical concept, e.g. 'under-5 mortality', "
                    "'access to clean water', 'CO2 emissions per capita'. Plain words."},
                "geography": {"type": "string",
                    "description": "ISO 3166-1 alpha-3 country code, e.g. KEN, NGA, IND."},
                "time_range_start": {"type": "integer"},
                "time_range_end": {"type": "integer"},
            },
            "required": ["concept", "geography"],
        },
    },
}


class AgenticQuery:
    """Lightweight parsed query for the agentic path."""
    def __init__(self, raw, concept, geography, time_range):
        self.raw = raw
        self.concept = concept
        self.geography = geography
        self.time_range = time_range


def parse_concept(raw_query: str) -> AgenticQuery:
    """Extract concept + country + years. Raises RuntimeError on LLM failure."""
    resp = _client().chat.completions.create(
        model="llama-3.3-70b-versatile", max_tokens=200,
        messages=[
            {"role": "system", "content":
             "Extract the data concept, country, and years from the user's "
             "question by calling extract_concept. Concept is plain words "
             "(the thing being measured), not a code."},
            {"role": "user", "content": raw_query},
        ],
        tools=[_CONCEPT_TOOL],
        tool_choice={"type": "function", "function": {"name": "extract_concept"}},
    )
    calls = resp.choices[0].message.tool_calls
    if not calls:
        raise RuntimeError("LLM did not extract a concept.")
    p = json.loads(calls[0].function.arguments)

    tr = None
    s, e = p.get("time_range_start"), p.get("time_range_end")
    if s is not None and e is not None:
        tr = (int(s), int(e))
    elif s is not None:
        tr = (int(s), int(s))
    elif e is not None:
        tr = (int(e), int(e))

    return AgenticQuery(raw_query, p["concept"],
                        p["geography"].upper().strip(), tr)


# ===========================================================================
# PHASE 1 (agentic) — get candidates from the live Commons search
# ===========================================================================

def get_candidates_agentic(raw_query: str) -> CandidateList:
    """Parse the concept, search the Commons, return grouped choices to pick from."""
    try:
        q = parse_concept(raw_query)
    except RuntimeError as exc:
        return CandidateList(query=raw_query, topic="unknown",
                             geography="unknown", time_range=None,
                             parse_error=f"Could not understand the question: {exc}")

    choices = find_indicators(q.concept)   # live Commons search + LLM grouping
    options = [
        CandidateOption(index=i, indicator_name=c.label, indicator_code=c.variable_id)
        for i, c in enumerate(choices, 1)
    ]
    return CandidateList(
        query=raw_query, topic=q.concept, geography=q.geography,
        time_range=q.time_range, options=options,
    )


# ===========================================================================
# Commons fetch -> RawDataset + RawMetadata (the "Commons switch")
# ===========================================================================

def _fetch_commons_dataset(
    commons_variable: str, iso3: str,
) -> Optional[tuple[RawDataset, RawMetadata, dict]]:
    """
    Fetch one Commons variable for a country. Returns (RawDataset, RawMetadata,
    facets_meta) using the BEST authoritative facet for the time series, with
    metadata (unit etc.) pulled from that facet. None on failure.
    """
    body = {"date": "", "variable": {"dcids": [commons_variable]},
            "entity": {"dcids": [f"country/{iso3.upper()}"]},
            "select": ["entity", "variable", "value", "date", "facet"]}
    try:
        resp = requests.post(OBS_ENDPOINT, json=body, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    facets_meta = data.get("facets", {}) or {}
    try:
        eb = data["byVariable"][commons_variable]["byEntity"][f"country/{iso3.upper()}"]
        ordered = eb.get("orderedFacets", []) or []
    except (KeyError, TypeError):
        return None
    if not ordered:
        return None

    # pick the facet with the most observations that is NOT crowd-sourced
    def is_auth(fid):
        m = facets_meta.get(fid, {})
        name = (m.get("importName") or "").lower()
        return not ("wikipedia" in name or "wikidata" in name)

    ordered_sorted = sorted(
        ordered,
        key=lambda f: (is_auth(str(f.get("facetId", ""))), len(f.get("observations", []))),
        reverse=True,
    )
    best = ordered_sorted[0]
    fid = str(best.get("facetId", ""))
    meta = facets_meta.get(fid, {})

    rows: list[DataRow] = []
    for o in best.get("observations", []):
        try:
            year = int(str(o.get("date", ""))[:4])
            val = o.get("value")
            val = float(val) if val is not None else None
            rows.append(DataRow(year=year, value=val))
        except (ValueError, TypeError):
            continue
    rows.sort(key=lambda r: r.year)

    dataset = RawDataset(indicator_code=commons_variable,
                         geography=iso3.upper(), rows=rows)

    last_year = max((r.year for r in rows), default=None)
    metadata = RawMetadata(
        indicator_code=commons_variable,
        indicator_name=None,                       # set by caller from the choice label
        unit=meta.get("unit"),                     # <-- Commons GIVES us this (WB didn't)
        source_org=meta.get("importName"),
        methodology_note=meta.get("measurementMethod"),
        time_coverage=(f"{rows[0].year}-{rows[-1].year}" if rows else None),
        geography_coverage=iso3.upper(),           # Commons answer is country-scoped
        license=meta.get("provenanceUrl"),         # provenance URL stands in for license/source
        last_updated=str(last_year) if last_year else None,
    )
    return dataset, metadata, facets_meta


# ===========================================================================
# PHASE 2 (agentic) — evaluate the chosen Commons variable
# ===========================================================================

def _time_filter(dataset: RawDataset, tr) -> RawDataset:
    if not tr:
        return dataset
    lo, hi = tr
    return RawDataset(indicator_code=dataset.indicator_code,
                      geography=dataset.geography,
                      rows=[r for r in dataset.rows if lo <= r.year <= hi])


def evaluate_agentic(
    raw_query: str,
    selected_codes: Optional[list[str]] = None,
    labels: Optional[dict[str, str]] = None,
) -> MultiDatasetReport:
    """
    Deep-evaluate the user's chosen Commons variable(s).
    selected_codes : Commons variable ids the user picked.
    labels         : optional {variable_id: human label} from the search choices.
    """
    try:
        q = parse_concept(raw_query)
    except RuntimeError as exc:
        return MultiDatasetReport(
            query=raw_query, topic="unknown", geography="unknown",
            time_range=None, candidates=[], overall_status="NOT_VIABLE",
            parse_error=f"Could not understand the question: {exc}")

    labels = labels or {}
    if not selected_codes:
        # default: evaluate the top candidate from a fresh search
        choices = find_indicators(q.concept)
        selected_codes = [choices[0].variable_id] if choices else []
        labels = {c.variable_id: c.label for c in choices}

    results: list[CandidateResult] = []
    for code in selected_codes:
        label = labels.get(code, code)
        fetched = _fetch_commons_dataset(code, q.geography)
        if fetched is None:
            results.append(_no_data_result(code, label, q.geography))
            continue
        dataset, metadata, _ = fetched
        metadata = metadata.model_copy(update={"indicator_name": label})
        dataset = _time_filter(dataset, q.time_range)
        if not dataset.rows:
            results.append(_no_data_result(code, label, q.geography))
            continue

        scores = compute_dimension_scores(dataset, metadata)
        years = [r.year for r in dataset.rows]
        info = DatasetInfo(
            indicator_name=label, indicator_code=code, geography=q.geography,
            years_in_data=(min(years), max(years)), row_count=len(dataset.rows),
            non_null_count=sum(1 for r in dataset.rows if r.value is not None),
            source_org=metadata.source_org,
            api_url=OBS_ENDPOINT,    # real callable endpoint (POST — see commons_request())
            last_updated=metadata.last_updated,
        )
        candidate = evaluate_candidate(info, scores)        # base 3-dim verdict

        # 4th dimension: cross-source agreement (reuse the working layer).
        try:
            cs = cross_source_check_commons(code, q.geography)
            dim = to_cross_source_dimension(cs)
            candidate.dimension_scores.cross_source = dim
            candidate.verdict = extended_verdict(candidate.verdict, candidate.dimension_scores)
            if candidate.verdict == "REVIEW":
                candidate.operational_explanation = (
                    "NEEDS HUMAN REVIEW — independent sources disagree on this "
                    f"value (spread {dim.spread_pct}% across {dim.authoritative_count} "
                    "authoritative sources). The data may be sound; a person should "
                    "choose which source to trust. " + candidate.operational_explanation
                )
        except Exception:
            pass

        results.append(candidate)

    usable = any(r.verdict in ("PASS", "REVIEW") for r in results)
    return MultiDatasetReport(
        query=raw_query, topic=q.concept, geography=q.geography,
        time_range=q.time_range, candidates=results,
        overall_status="VIABLE" if (usable and results) else "NOT_VIABLE",
        pivots=[], chain=chain_recommendations(q.concept, q.geography),
    )


def cross_source_check_commons(commons_variable: str, iso3: str):
    """Cross-source check directly on a Commons variable id (not a WB code).
    Mirrors fetch_commons.cross_source_check but skips the WB->Commons map."""
    from .fetch_commons import compare_sources, narrate_conflict
    sources = fetch_commons_facets(commons_variable, iso3)
    result = compare_sources(commons_variable, commons_variable, iso3, sources)
    result.explanation = narrate_conflict(result)
    return result


def _no_data_result(code: str, label: str, iso3: str) -> CandidateResult:
    empty = DimensionScores(
        metadata_completeness=MetadataCompletenessScore(score=0.0, missing_fields=[], present_fields=[]),
        data_quality=DataQualityScore(score=0.0, issues=[]),
        freshness=FreshnessScore(score=0.0, days_since_update=None, note=""),
    )
    return CandidateResult(
        dataset_info=DatasetInfo(indicator_name=label, indicator_code=code, geography=iso3),
        dimension_scores=empty, verdict="REJECT",
        operational_explanation="No observations available from the Commons for "
                                "this variable, country, and time range.",
    )


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "under-5 mortality in Kenya 2018-2022"
    print(f'\nQUERY: {query}\n' + "="*60)

    print("\nPHASE 1 — candidates from the live Commons search:")
    cl = get_candidates_agentic(query)
    if cl.parse_error:
        print("  parse error:", cl.parse_error); sys.exit(1)
    print(f"  concept={cl.topic}  country={cl.geography}  period={cl.time_range}")
    for o in cl.options:
        print(f"    [{o.index}] {o.indicator_name}")
        print(f"        {o.indicator_code}")

    if not cl.options:
        print("  (no candidates)"); sys.exit(0)

    pick = cl.options[0].indicator_code
    label = {o.indicator_code: o.indicator_name for o in cl.options}
    print(f"\nPHASE 2 — evaluating: {label[pick]}  ({pick})")
    report = evaluate_agentic(query, selected_codes=[pick], labels=label)
    for c in report.candidates:
        print(f"\n  Verdict: {c.verdict}")
        s = c.dimension_scores
        print(f"    metadata  {s.metadata_completeness.score:.0%}  "
              f"(missing: {', '.join(s.metadata_completeness.missing_fields) or 'none'})")
        print(f"    quality   {s.data_quality.score:.0%}")
        print(f"    freshness {s.freshness.score:.0%}")
        if s.cross_source:
            print(f"    x-source  {s.cross_source.status}  "
                  f"({s.cross_source.source_count} sources, "
                  f"{s.cross_source.authoritative_count} authoritative)")
    print(f"\n  Overall: {report.overall_status}")
