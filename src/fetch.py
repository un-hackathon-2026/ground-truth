"""
Step 2 — Data + Metadata Fetch (deterministic, single API: World Bank v2).

This step does NO judgment — it fetches raw data and raw metadata only.
All short-circuit conditions (FetchError, 0 rows) are typed and explicit.
"""

from __future__ import annotations

from typing import Optional, Union

import requests

from .schemas import DataRow, FetchError, RawDataset, RawMetadata, StructuredQuery

WB_BASE = "https://api.worldbank.org/v2"
REQUEST_TIMEOUT = 20  # seconds


def fetch_dataset_and_metadata(
    query: StructuredQuery,
) -> Union[tuple[RawDataset, RawMetadata], FetchError]:
    """
    Fetches data and metadata from the World Bank API for the given query.
    Returns (RawDataset, RawMetadata) on success, or FetchError on failure.
    Does NOT raise exceptions — all failures are typed FetchError.
    """
    meta_result = _fetch_metadata(query.indicator_code)
    if isinstance(meta_result, FetchError):
        return meta_result

    data_result = _fetch_data(query)
    if isinstance(data_result, FetchError):
        return data_result

    return data_result, meta_result


def _fetch_metadata(indicator_code: str) -> Union[RawMetadata, FetchError]:
    """Fetch indicator metadata from the WB indicator endpoint."""
    url = f"{WB_BASE}/indicator/{indicator_code}"
    try:
        resp = requests.get(url, params={"format": "json"}, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return FetchError(reason=f"Network error fetching metadata: {exc}")

    if resp.status_code != 200:
        return FetchError(
            reason=f"Metadata endpoint returned HTTP {resp.status_code}.",
            http_status=resp.status_code,
        )

    try:
        payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            return FetchError(reason="Metadata response is empty or malformed.")
        item = payload[1][0]
    except (ValueError, IndexError, KeyError):
        return FetchError(reason="Could not parse metadata JSON response.")

    return RawMetadata(
        indicator_code=indicator_code,
        indicator_name=item.get("name") or None,
        unit=item.get("unit") or None,
        source_org=_nested(item, "sourceOrganization"),
        methodology_note=_nested(item, "sourceNote"),
        # WB API does not expose time_coverage, geography_coverage, or license
        # as discrete fields — scored as absent (honest null, not fabricated).
        time_coverage=None,
        geography_coverage=None,
        license=None,
        # Use the source's last-updated date if available (rarely present in
        # indicator endpoint; the data rows' latest year is a proxy used below).
        last_updated=None,
    )


def _fetch_data(query: StructuredQuery) -> Union[tuple[RawDataset, str], FetchError]:
    """
    Fetch time-series observations. Returns (RawDataset, most_recent_year_str)
    so the caller can set last_updated on metadata if the metadata field is null.
    """
    url = f"{WB_BASE}/country/{query.geography}/indicator/{query.indicator_code}"
    params: dict = {"format": "json", "per_page": 1000}

    if query.time_range:
        start, end = query.time_range
        params["date"] = f"{start}:{end}"

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        return FetchError(reason=f"Network error fetching data: {exc}")

    if resp.status_code != 200:
        return FetchError(
            reason=f"Data endpoint returned HTTP {resp.status_code}.",
            http_status=resp.status_code,
        )

    try:
        payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2:
            return FetchError(reason="Data response is malformed.")
        observations = payload[1] or []
    except ValueError:
        return FetchError(reason="Could not parse data JSON response.")

    rows: list[DataRow] = []
    for obs in observations:
        try:
            year = int(obs["date"])
            raw_val = obs.get("value")
            value = float(raw_val) if raw_val is not None else None
            rows.append(DataRow(year=year, value=value))
        except (KeyError, ValueError, TypeError):
            continue

    rows.sort(key=lambda r: r.year)
    return RawDataset(
        indicator_code=query.indicator_code,
        geography=query.geography,
        rows=rows,
    )


def fetch(query: StructuredQuery) -> Union[tuple[RawDataset, RawMetadata], FetchError]:
    """Legacy single-indicator entry point (kept for backwards compatibility)."""
    return fetch_dataset_and_metadata(query)


def fetch_by_code(
    geography: str,
    indicator_code: str,
    time_range: Optional[tuple[int, int]],
) -> Union[tuple[RawDataset, RawMetadata], FetchError]:
    """
    Public entry point used by the multi-dataset pipeline.
    Fetches one indicator code for a geography and optional time range.
    Patches metadata.last_updated from the most recent data year when absent.
    """
    meta = _fetch_metadata(indicator_code)
    if isinstance(meta, FetchError):
        return meta

    class _Q:
        pass
    q = _Q()
    q.geography = geography          # type: ignore[attr-defined]
    q.indicator_code = indicator_code  # type: ignore[attr-defined]
    q.time_range = time_range          # type: ignore[attr-defined]

    data = _fetch_data(q)  # type: ignore[arg-type]
    if isinstance(data, FetchError):
        return data

    if not meta.last_updated and data.rows:
        latest_year = max(r.year for r in data.rows)
        meta = meta.model_copy(update={"last_updated": str(latest_year)})

    return data, meta


def _nested(obj: dict, key: str) -> str | None:
    val = obj.get(key)
    if not val:
        return None
    if isinstance(val, str):
        return val.strip() or None
    if isinstance(val, dict):
        return val.get("value") or None
    return None
