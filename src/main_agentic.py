"""
main_agentic.py — interactive CLI for the Commons-native agentic pipeline.

Full flow, pause and all:
  1. type a question
  2. see candidate indicators from the live Commons search   (Phase 1)
  3. PAUSE — you choose which one(s)
  4. deep evaluation: 4 dimensions + verdict                 (Phase 2)
  5. if REVIEW (sources conflict): the conflicting sources are shown
     with their values + provenance, so a human can decide INFORMED.

We DETECT and SURFACE conflicts; we do NOT auto-resolve them. A trust tool
should not silently pick which source is "true" — it hands the decision to an
accountable human, with the evidence in front of them. That is the design.

Run from the project root:
  python -X utf8 -m src.main_agentic
"""

from __future__ import annotations

import sys

from .agentic_pipeline import get_candidates_agentic, evaluate_agentic
from .fetch_commons import fetch_commons_facets

SEP = "-" * 70


def _print_candidates(cl) -> None:
    print(f"\n{SEP}")
    print("  CANDIDATE DATASETS  (from the live UN Commons search)")
    print(SEP)
    print(f"  Query   : {cl.query}")
    print(f"  Concept : {cl.topic}")
    print(f"  Country : {cl.geography}")
    if cl.time_range:
        print(f"  Period  : {cl.time_range[0]}-{cl.time_range[1]}")
    print(SEP)
    print("  Which dataset best answers your question?\n")
    for o in cl.options:
        print(f"    [{o.index}] {o.indicator_name}")
        print(f"        {o.indicator_code}")
    print("\n  Enter a number to choose ONE,")
    print("  or several separated by commas (e.g. 1,3),")
    print("  or 'all' to evaluate every candidate,")
    print("  or paste your own Commons variable id if none fit")
    print("     (e.g. sdg/SH_DYN_MORT.AGE--Y0T4 or Count_Person).")


def _show_conflict_sources(variable_id: str, iso3: str) -> None:
    """At a REVIEW, show the conflicting sources so the human can decide."""
    sources = fetch_commons_facets(variable_id, iso3)
    usable = [s for s in sources if s.value is not None]
    if not usable:
        return
    print(f"\n    {'-'*60}")
    print("    SOURCES DISAGREE — you decide which to trust:")
    print(f"    {'-'*60}")
    for s in sorted(usable, key=lambda x: (x.value if x.value is not None else 0)):
        tag = "" if _authoritative(s.source_name) else "  (crowd-sourced)"
        val = f"{s.value:,.0f}" if s.value and s.value > 1000 else f"{s.value}"
        print(f"      • {s.source_name}{tag}")
        print(f"          value: {val}   year: {s.latest_year or '—'}")
        if s.provenance_url:
            print(f"          source: {s.provenance_url}")
    print(f"    {'-'*60}")
    print("    The tool does NOT pick for you — this is a human decision.")


def _authoritative(name: str) -> bool:
    low = (name or "").lower()
    return not ("wikipedia" in low or "wikidata" in low)


def _print_report(report) -> None:
    print(f"\n{SEP}")
    print("  TRUST & VIABILITY REPORT")
    print(SEP)
    print(f"  Overall: {report.overall_status}\n")

    for i, c in enumerate(report.candidates, 1):
        s = c.dimension_scores
        mark = {"PASS": "[PASS]", "REVIEW": "[REVIEW]", "REJECT": "[REJECT]"}[c.verdict]
        print(f"  {mark}  {c.dataset_info.indicator_name}")
        print(f"         {c.dataset_info.indicator_code}")
        if c.dataset_info.source_org:
            print(f"         source: {c.dataset_info.source_org}")
        print(f"         metadata {s.metadata_completeness.score:.0%}  "
              f"quality {s.data_quality.score:.0%}  "
              f"freshness {s.freshness.score:.0%}", end="")
        if s.cross_source:
            print(f"  x-source {s.cross_source.status} "
                  f"({s.cross_source.source_count} src)")
        else:
            print()

        # The differentiator made actionable: at REVIEW, show the conflict.
        if c.verdict == "REVIEW" and s.cross_source and s.cross_source.status == "CONFLICT":
            _show_conflict_sources(c.dataset_info.indicator_code,
                                   c.dataset_info.geography)
        print()

    if report.chain:
        print(f"{SEP}")
        print("  RELATED QUERIES")
        print(SEP)
        for ch in report.chain:
            print(f"  -> {ch.label}")


def main() -> None:
    print("\n  GROUND TRUTH — agentic trust copilot (UN Data Commons)")
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("\n  Ask a development-data question:\n  > ").strip()
    if not query:
        print("  No question entered."); return

    print("\n  Searching the Commons...")
    cl = get_candidates_agentic(query)
    if cl.parse_error:
        print(f"  Could not process: {cl.parse_error}"); return
    if not cl.options:
        print("  No matching indicators found in the Commons."); return

    _print_candidates(cl)

    raw = input("\n  > ").strip()
    label = {o.indicator_code: o.indicator_name for o in cl.options}
    low = raw.lower()
    if low == "all":
        chosen = [o.indicator_code for o in cl.options]
    else:
        picks = []
        is_numeric_choice = all(
            part.strip().isdigit() for part in raw.split(",") if part.strip()
        )
        if is_numeric_choice and raw.strip():
            for part in raw.split(","):
                part = part.strip()
                if part.isdigit():
                    match = next((o for o in cl.options if o.index == int(part)), None)
                    if match:
                        picks.append(match.indicator_code)
        else:
            # user pasted their own Commons variable id (bring-your-own)
            custom = raw.strip()
            if custom:
                picks.append(custom)
                label[custom] = f"(your indicator) {custom}"
        chosen = picks or [cl.options[0].indicator_code]

    print(f"\n  Evaluating {len(chosen)} dataset(s) — checking sources...")
    report = evaluate_agentic(query, selected_codes=chosen, labels=label)
    _print_report(report)


if __name__ == "__main__":
    main()
