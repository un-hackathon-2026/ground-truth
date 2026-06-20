"""
Query Trust & Viability Assessor — CLI entry point.

Usage:
    python main.py "What's the poverty rate in Kenya over the last 5 years?"
    python main.py --query "GDP per capita in India from 2015 to 2023"
    python main.py  # prompts interactively
"""

from __future__ import annotations

import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from src.pipeline import run
from src.schemas import CandidateResult, MultiDatasetReport

WIDTH = 70
SEP = "─" * WIDTH
SEP_THIN = "·" * WIDTH

STATUS_SYMBOLS = {"VIABLE": "✓ VIABLE", "NOT_VIABLE": "✗ NOT VIABLE"}
VERDICT_SYMBOLS = {"PASS": "  [PASS]", "REJECT": "  [REJECT]"}


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
        print(f"\n  ERROR: {report.parse_error}")
        print()
        print(SEP)
        print()
        return

    overall = report.overall_status
    print(f"\n  Overall Status: {STATUS_SYMBOLS[overall]}")
    if overall == "VIABLE":
        passing = [c for c in report.candidates if c.verdict == "PASS"]
        print(
            f"  {len(passing)} of {len(report.candidates)} candidate dataset(s) passed. "
            "See details below."
        )
    else:
        print(
            f"  All {len(report.candidates)} candidate dataset(s) were rejected. "
            "Actionable pivots are listed at the end."
        )

    # Per-candidate sections
    for i, candidate in enumerate(report.candidates, 1):
        di = candidate.dataset_info
        scores = candidate.dimension_scores
        v = candidate.verdict

        print()
        print(f"  {'═' * 66}")
        verdict_tag = "✓ PASS" if v == "PASS" else "✗ REJECT"
        name = di.indicator_name or di.indicator_code
        print(f"  Dataset {i}: {name}")
        print(f"  Verdict : {verdict_tag}")
        print(f"  {'─' * 66}")

        # Attribution
        print(f"  Code    : {di.indicator_code}")
        print(f"  Source  : {_truncate(di.source_org or 'Not available', 60)}")
        if di.years_in_data:
            print(
                f"  Data    : {di.years_in_data[0]}–{di.years_in_data[1]} "
                f"({di.non_null_count} of {di.row_count} observations have values)"
            )
        if di.last_updated:
            print(f"  Updated : {di.last_updated}")
        print(f"  URL     : {di.api_url}")

        # Dimension scores (compact)
        print()
        mc = scores.metadata_completeness
        dq = scores.data_quality
        fr = scores.freshness
        print(f"  Scores")
        print(f"    Metadata Completeness  {_bar(mc.score)}  {mc.score:.0%}")
        if mc.missing_fields:
            print(f"      Missing: {', '.join(mc.missing_fields)}")
        print(f"    Data Quality           {_bar(dq.score)}  {dq.score:.0%}")
        for issue in dq.issues:
            print(f"      Issue: {issue}")
        print(f"    Freshness              {_bar(fr.score)}  {fr.score:.0%}")
        print(f"      {fr.note}")

        # Operational explanation
        print()
        print(f"  Assessment")
        for line in _wrap(candidate.operational_explanation, WIDTH - 4):
            print(f"    {line}")

    # Pivots (only when all rejected)
    if report.pivots:
        print()
        print(SEP)
        print("  ACTIONABLE PIVOTS")
        print(SEP)
        for i, pivot in enumerate(report.pivots, 1):
            print()
            for line in _wrap(f"{i}. {pivot}", WIDTH - 4):
                print(f"  {line}")

    print()
    print(SEP)
    print()


def _bar(score: float, width: int = 8) -> str:
    filled = round(score * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = f"{current} {word}".strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query Trust & Viability Assessor for development data"
    )
    parser.add_argument("query", nargs="?", help="Natural-language development data query")
    parser.add_argument("--query", "-q", dest="query_flag")
    args = parser.parse_args()

    raw_query = args.query or args.query_flag
    if not raw_query:
        print("Query Trust & Viability Assessor")
        print("Enter a development data question:")
        raw_query = input("> ").strip()
        if not raw_query:
            print("No query provided. Exiting.")
            sys.exit(1)

    print(f"\nAssessing query: \"{raw_query}\" ...\n")
    print("(Evaluating all candidate datasets — this may take a few seconds.)\n")
    report = run(raw_query)
    print_report(report)


if __name__ == "__main__":
    main()
