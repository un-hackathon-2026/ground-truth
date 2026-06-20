"""
Step 1 — Query Parsing (LLM + Pydantic).

The LLM classifies the query into ONE topic from TOPIC_GROUPS.
All candidate indicators for that topic are resolved deterministically
from the fixed catalog — the LLM never picks individual indicator codes.
"""

from __future__ import annotations

import json
import os
from typing import Optional

import groq
from pydantic import ValidationError

from .schemas import TOPIC_GROUPS, VALID_ISO3_CODES, StructuredQuery

_CLIENT: Optional[groq.Groq] = None


def _client() -> groq.Groq:
    global _CLIENT
    if _CLIENT is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Copy .env.example to .env and add your key. "
                "Get a free key at https://console.groq.com"
            )
        _CLIENT = groq.Groq(api_key=api_key)
    return _CLIENT


_PARSE_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_query_parameters",
        "description": (
            "Extract structured parameters from a natural-language development-data query. "
            "Return ONLY what is stated or clearly implied — do not invent values."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": (
                        "The development topic this query is about. "
                        f"Must be exactly one of: {sorted(TOPIC_GROUPS.keys())}."
                    ),
                    "enum": sorted(TOPIC_GROUPS.keys()),
                },
                "geography": {
                    "type": "string",
                    "description": (
                        "ISO 3166-1 alpha-3 country code (3 uppercase letters). "
                        "Examples: KEN=Kenya, NGA=Nigeria, IND=India, BRA=Brazil, "
                        "USA=United States, GBR=United Kingdom, DEU=Germany, CHN=China, "
                        "ZAF=South Africa, ETH=Ethiopia, EGY=Egypt, TZA=Tanzania."
                    ),
                },
                "time_range_start": {
                    "type": "integer",
                    "description": "Start year (inclusive) if specified. Omit if not stated.",
                },
                "time_range_end": {
                    "type": "integer",
                    "description": "End year (inclusive) if specified. Omit if not stated.",
                },
                "comparison_requested": {
                    "type": "boolean",
                    "description": (
                        "True if the query implies comparing across time, countries, or sources."
                    ),
                },
            },
            "required": ["topic", "geography", "comparison_requested"],
        },
    },
}

_SYSTEM_PROMPT = (
    "You are a query parameter extractor for a development data system. "
    "Your only job is to call the extract_query_parameters tool with the structured "
    "parameters that represent the user's intent. "
    "Do not add commentary or explanations — only call the tool."
)


def parse_query(raw_query: str) -> StructuredQuery:
    """
    Classify the query into a topic and extract geography/time.
    Raises ValidationError if geography or topic fail validation.
    Raises RuntimeError if the LLM call fails.
    """
    response = _client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=256,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": raw_query},
        ],
        tools=[_PARSE_TOOL],
        tool_choice={"type": "function", "function": {"name": "extract_query_parameters"}},
    )

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise RuntimeError("LLM did not call the extraction tool.")

    params: dict = json.loads(tool_calls[0].function.arguments)

    # Normalise boolean (some models serialise it as a string).
    cr = params.get("comparison_requested", False)
    if isinstance(cr, str):
        params["comparison_requested"] = cr.lower() in ("true", "1", "yes")

    # Resolve time_range from separate start/end fields.
    time_range = None
    start = params.get("time_range_start")
    end = params.get("time_range_end")
    if start is not None and end is not None:
        time_range = [start, end]
    elif start is not None:
        time_range = [start, start]
    elif end is not None:
        time_range = [end, end]

    return StructuredQuery(
        topic=params["topic"],
        geography=params["geography"],
        time_range=time_range,
        comparison_requested=params.get("comparison_requested", False),
    )
