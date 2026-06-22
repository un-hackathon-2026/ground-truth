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

    if not dataset or not country or not instructions:
        print(json.dumps({"error": "dataset, country, and instructions are required"}))
        sys.exit(1)

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

    memo = resp.choices[0].message.content or ""
    print(json.dumps({"memo": memo}))


if __name__ == "__main__":
    main()
