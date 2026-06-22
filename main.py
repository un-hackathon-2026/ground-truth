"""
Query Trust & Viability Assessor — CLI entry point (two-phase).

Flow:
    1. Parse the query and show the candidate datasets.
    2. The USER picks which dataset(s) answer their question
       (or supplies their own indicator code).
    3. The deep pipeline runs ONLY on the chosen dataset(s).

Usage:
    python main.py "child mortality rate in Kenya 2021-2025"
    python main.py --all "..."     # skip the picker, evaluate everything
"""

from __future__ import annotations

import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from src.pipeline import get_candidates, evaluate_selection
from src.schemas import MultiDatasetReport, CandidateList

WIDTH = 70
SEP = "─" * WIDTH

STATUS_SYMBOLS = {"VIABLE": "✓ VIABLE", "NOT_VIABLE": "✗ NOT VIABLE"}


# ---------------------------------------------------------------------------
# Phase 1 display + selection
# ---------------------------------------------------------------------------

def choose_datasets(cl: CandidateList) -> list[str]:
    """Show the candidate datasets and let the user pick. Returns chosen codes."""
    print()
    print(SEP)
    print("  CANDIDATE DATASETS")
    print(SEP)
    print(f"  Query   : {cl.query}")
    print(f"  Topic   : {cl.topic}")
    print(f"  Country : {cl.geography}")
    if cl.time_range:
        print(f"  Period  : {cl.time_range[0]}–{cl.time_range[1]}")
    print(SEP)
    print("  Which dataset best answers your question?\n")
    for o in cl.options:
        print(f"    [{o.index}] {o.indicator_name}   ({o.indicator_code})")
    print()
    print("  Enter a number to choose ONE,")
    print("  or several numbers separated by commas (e.g. 1,3),")
    print("  or 'all' to evaluate every candidate,")
    print("  or paste your own World Bank indicator code (e.g. NY.GDP.PCAP.CD).")
    print()

    raw = input("  > ").strip()
    if not raw or raw.lower() == "all":
        return [o.indicator_code for o in cl.options]

    # custom indicator code (contains a dot, not just digits)
    if any(c.isalpha() for c in raw):
        return [raw.upper()]

    # numbers
    chosen: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part)
            match = next((o for o in cl.options if o.index == idx), None)
            if match:
                chosen.append(match.indicator_code)
    return chosen or [o.indicator_code for o in cl.options]


# ---------------------------------------------------------------------------
# Phase 2 display (the report)
# ---------------------------------------------------------------------------

def print_report(report: MultiDatasetReport) -> None:
    print()
    print(SEP)
    print("  QUERY TRUST & VIABILITY REPORT")
    print(SEP)
    print(f"  Query   : {report.query}")
    print(f"  Topic   : {report.topic}")
    print(f"  Country : {report.geography}")
    if report.time_range:
        print(f"  Period  : {report.time_range[0]}–{report.time_range[1]}")
    print(SEP)

    if report.parse_error:
        print(f"\n  ERROR: {report.parse_error}\n")
        print(SEP)
        return

    overall = report.overall_status
    print(f"\n  Overall Status: {STATUS_SYMBOLS[overall]}")
    usable = [c for c in report.candidates if c.verdict in ("PASS", "REVIEW")]
    print(f"  {len(usable)} of {len(report.candidates)} evaluated dataset(s) usable.")

    for i, candidate in enumerate(report.candidates, 1):
        di = candidate.dataset_info
        scores = candidate.dimension_scores
        v = candidate.verdict
        print()
        print(f"  {'═' * 66}")
        verdict_tag = {"PASS": "✓ PASS", "REVIEW": "⚑ REVIEW", "REJECT": "✗ REJECT"}[v]
        print(f"  Dataset {i}: {di.indicator_name or di.indicator_code}")
        print(f"  Verdict : {verdict_tag}")
        print(f"  {'─' * 66}")
        print(f"  Code    : {di.indicator_code}")
        print(f"  Source  : {_truncate(di.source_org or 'Not available', 60)}")
        if di.years_in_data:
            print(f"  Data    : {di.years_in_data[0]}–{di.years_in_data[1]} "
                  f"({di.non_null_count} of {di.row_count} observations have values)")
        if di.last_updated:
            print(f"  Updated : {di.last_updated}")
        print(f"  URL     : {di.api_url}")

        print()
        mc, dq, fr = scores.metadata_completeness, scores.data_quality, scores.freshness
        print("  Scores")
        print(f"    Metadata Completeness  {_bar(mc.score)}  {mc.score:.0%}")
        if mc.missing_fields:
            print(f"      Missing: {', '.join(mc.missing_fields)}")
        print(f"    Data Quality           {_bar(dq.score)}  {dq.score:.0%}")
        for issue in dq.issues:
            print(f"      Issue: {issue}")
        print(f"    Freshness              {_bar(fr.score)}  {fr.score:.0%}")
        print(f"      {fr.note}")
        cs = scores.cross_source
        if cs:
            print(f"    Cross-Source Agreement {_bar(cs.score)}  {cs.score:.0%}")
            detail = (f"      {cs.status} — {cs.source_count} sources "
                      f"({cs.authoritative_count} authoritative)")
            if cs.spread_pct:
                detail += f", spread {cs.spread_pct}%"
            print(detail)

        print()
        print("  Assessment")
        for line in _wrap(candidate.operational_explanation, WIDTH - 4):
            print(f"    {line}")

    if report.pivots:
        print()
        print(SEP)
        print("  ACTIONABLE PIVOTS")
        print(SEP)
        for i, pivot in enumerate(report.pivots, 1):
            print()
            for line in _wrap(f"{i}. {pivot}", WIDTH - 4):
                print(f"  {line}")

    if report.chain:
        print()
        print(SEP)
        print("  RELATED QUERIES (chain)")
        print(SEP)
        for ch in report.chain:
            print(f"  → {ch.label}")
            for line in _wrap(ch.reason, WIDTH - 8):
                print(f"      {line}")

    print()
    print(SEP)
    print()


def _bar(score: float, width: int = 8) -> str:
    filled = round(score * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"

def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[:max_len - 3] + "..."

def _wrap(text: str, width: int) -> list[str]:
    words = text.split(); lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = f"{current} {word}".strip()
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Query Trust & Viability Assessor")
    parser.add_argument("query", nargs="?", help="Natural-language development data query")
    parser.add_argument("--query", "-q", dest="query_flag")
    parser.add_argument("--all", action="store_true", help="Evaluate all candidates (skip the picker)")
    args = parser.parse_args()

    raw_query = args.query or args.query_flag
    if not raw_query:
        print("Query Trust & Viability Assessor")
        print("Enter a development data question:")
        raw_query = input("> ").strip()
        if not raw_query:
            print("No query provided. Exiting.")
            sys.exit(1)

    # PHASE 1 — get candidates
    print(f"\nFinding candidate datasets for: \"{raw_query}\" ...")
    cl = get_candidates(raw_query)
    if cl.parse_error:
        print(f"\n  ERROR: {cl.parse_error}\n")
        sys.exit(1)

    # PHASE 1b — user selects (unless --all)
    if args.all:
        selected = [o.indicator_code for o in cl.options]
    else:
        selected = choose_datasets(cl)

    # PHASE 2 — deep evaluation on the chosen dataset(s)
    print(f"\nEvaluating your selection ({len(selected)} dataset(s)) — this may take a few seconds.\n")
    report = evaluate_selection(raw_query, selected_codes=selected)
    print_report(report)


if __name__ == "__main__":
    main()
