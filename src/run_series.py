"""
Bridge script: fetch a time-series for one dataset + country.

Stdin:  { "dataset": "<indicator_code>", "country": "<ISO3>" }
Stdout: { "rows": [{"year": ..., "value": ...}],
           "unit": "...", "source_org": "...", "time_coverage": "..." }
"""
import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read())
    dataset = (payload.get("dataset") or "").strip()
    country = (payload.get("country") or "").strip()

    if not dataset or not country:
        print(json.dumps({"error": "dataset and country are required"}))
        sys.exit(1)

    from .agentic_pipeline import _fetch_commons_dataset

    result = _fetch_commons_dataset(dataset, country)
    if result is None:
        print(json.dumps({"error": f"No data found for {dataset} in {country}"}))
        return

    raw_dataset, metadata, _ = result

    rows = [
        {"year": r.year, "value": r.value}
        for r in raw_dataset.rows
        if r.value is not None
    ]

    print(json.dumps({
        "rows": rows,
        "unit": metadata.unit,
        "source_org": metadata.source_org,
        "time_coverage": metadata.time_coverage,
    }))


if __name__ == "__main__":
    main()
