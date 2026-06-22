"""
Bridge script: generate a policy memo grounded in actual dataset observations.

Stdin:  { "dataset": "...", "country": "...", "name": "...", "instructions": "..." }
Stdout: { "memo": "..." }
"""
import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read())
    dataset = (payload.get("dataset") or "").strip()
    country = (payload.get("country") or "").strip()
    name = (payload.get("name") or dataset).strip()
    instructions = (payload.get("instructions") or "").strip()

    if not dataset or not country:
        print(json.dumps({"error": "dataset and country are required"}))
        sys.exit(1)

    if not instructions:
        instructions = (
            "Write a comprehensive evidence brief for a senior policy audience. "
            "Structure the brief with: EXECUTIVE SUMMARY (2-3 sentences), KEY FINDINGS "
            "(bullet points citing specific years and values), TREND ANALYSIS (describe "
            "the direction and magnitude of change over the observed period), POLICY "
            "IMPLICATIONS (what this data means for decision-makers), and RECOMMENDED "
            "NEXT STEPS (concrete actions or data gaps to address). "
            "Ground every claim in the actual data provided. Be precise and professional."
        )

    from .agentic_pipeline import _fetch_commons_dataset, _client

    # Fetch real observations
    result = _fetch_commons_dataset(dataset, country)

    if result is None:
        data_context = (
            f"Dataset: {name}\n"
            f"Indicator code: {dataset}\n"
            f"Country: {country}\n"
            "Time-series data: No observations were available from the UN Data Commons "
            "for this dataset and country combination."
        )
    else:
        raw_dataset, metadata, _ = result
        rows = [(r.year, r.value) for r in raw_dataset.rows if r.value is not None]

        series_lines = "\n".join(f"  {year}: {value}" for year, value in rows)
        data_context = (
            f"Dataset: {name}\n"
            f"Indicator code: {dataset}\n"
            f"Country: {country}\n"
            f"Source organisation: {metadata.source_org or 'UN Data Commons'}\n"
            f"Unit of measurement: {metadata.unit or 'not specified'}\n"
            f"Time coverage: {metadata.time_coverage or 'not specified'}\n"
            f"Last updated: {metadata.last_updated or 'not specified'}\n"
            f"Number of observations: {len(rows)}\n\n"
            f"Time-series data:\n{series_lines}"
        )

    from . import usage_tracker
    resp = _client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=2000,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior policy analyst at the UN Data Commons Platform. "
                    "Generate a professional policy memorandum that is strictly grounded "
                    "in the actual dataset values provided. "
                    "Cite specific years and numeric values from the time-series in your analysis. "
                    "Do not invent numbers, trends, or data points not present in the dataset. "
                    "Structure the memo with clear headers: EXECUTIVE SUMMARY, KEY FINDINGS, "
                    "TREND ANALYSIS, POLICY IMPLICATIONS, and RECOMMENDED NEXT STEPS. "
                    "If data is limited or absent, say so explicitly and note what additional "
                    "data collection would be needed."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Dataset information:\n{data_context}\n\n"
                    f"Analyst instructions:\n{instructions}"
                ),
            },
        ],
    )

    if resp.usage:
        usage_tracker.record(resp.usage.prompt_tokens, resp.usage.completion_tokens)
    memo = resp.choices[0].message.content or ""

    # Build trust appendix from metadata
    if result is not None:
        raw_dataset, metadata, _ = result
        rows_with_values = [(r.year, r.value) for r in raw_dataset.rows if r.value is not None]
        n_obs = len(rows_with_values)
        year_range = f"{rows_with_values[0][0]}–{rows_with_values[-1][0]}" if rows_with_values else "N/A"
        methodology = metadata.methodology_note or "Not specified"
        provenance = metadata.license or "Not specified"
        freshness_note = (
            f"Last updated: {metadata.last_updated}. "
            "Data may not reflect conditions after this date."
            if metadata.last_updated else "Last update date not recorded."
        )
    else:
        n_obs = 0
        year_range = "N/A"
        methodology = "Not available"
        provenance = "Not available"
        freshness_note = "No observations were available for this dataset and country."

    trust_appendix = f"""
─────────────────────────────────────────────────────────────────
DATA TRUST APPENDIX — UN Data Commons Trust & Viability Copilot
─────────────────────────────────────────────────────────────────

Dataset:          {name}
Indicator code:   {dataset}
Country:          {country}
Observations:     {n_obs} ({year_range})
Methodology:      {methodology}
Source/Provenance:{provenance}
Freshness:        {freshness_note}

IMPORTANT CAVEATS
This document was generated by an AI system using verified UN Data Commons data.
All numerical claims above are derived from the dataset cited. Users should:
  · Verify indicator definitions match their analytical context
  · Not extrapolate beyond the observed time range ({year_range})
  · Treat single-source figures with appropriate caution pending cross-validation
  · Consult the source organisation for sub-national or disaggregated data needs

Classification: UNCLASSIFIED · For Policy Reference Only
Generated by:   UN Data Commons Trust & Viability Copilot""".strip()

    full_memo = memo.strip() + "\n\n" + trust_appendix
    print(json.dumps({"memo": full_memo, "usage": usage_tracker.totals()}))


if __name__ == "__main__":
    main()
