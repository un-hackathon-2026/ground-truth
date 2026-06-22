"""
commons_search.py — Agentic indicator discovery via the UN Commons.

Two stages, both agentic:
  1. SEARCH  — ask the Commons `search_indicators` MCP tool which statistical
               variables match a plain-language concept (no hardcoded table).
  2. GROUP   — an LLM reads the raw matches and organises them into the
               meaningful choices a *person* would pick from: clean labels,
               variants tucked under their parent, rate vs. count separated,
               irrelevant hits dropped.

This is the agentic core: the user asks anything, the Commons finds candidates,
and the model reasons about what the user actually wants.

Confirmed endpoints (live):
  MCP search : https://dc-un-dev-dc-datacommons-service-72utkhfqvq-uc.a.run.app/mcp
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import requests

MCP_URL = "https://dc-un-dev-dc-datacommons-service-72utkhfqvq-uc.a.run.app/mcp"
REQUEST_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

class RawHit:
    """One raw variable the Commons search returned."""
    def __init__(self, variable_id: str, description: str, topic: str):
        self.variable_id = variable_id
        self.description = description
        self.topic = topic
    def to_dict(self):
        return {"variable_id": self.variable_id,
                "description": self.description, "topic": self.topic}


class GroupedChoice:
    """A clean, human-facing choice the user can pick."""
    def __init__(self, label: str, variable_id: str,
                 measure: str = "", variants: Optional[list] = None):
        self.label = label              # e.g. "Under-5 mortality rate"
        self.variable_id = variable_id  # the headline/default variable to evaluate
        self.measure = measure          # "rate" | "count" | "" (helps the user)
        self.variants = variants or []  # [{label, variable_id}] breakdowns (sex/age)
    def to_dict(self):
        return {"label": self.label, "variable_id": self.variable_id,
                "measure": self.measure, "variants": self.variants}
    def __repr__(self):
        v = f" (+{len(self.variants)} breakdowns)" if self.variants else ""
        return f"{self.label} [{self.measure}] -> {self.variable_id}{v}"


# ---------------------------------------------------------------------------
# Stage 1 — Commons search (MCP)
# ---------------------------------------------------------------------------

def _clean_text(s: str) -> str:
    """Fix mojibake (e.g. 'Underâ5' -> 'Under-5') and tidy whitespace."""
    if not s:
        return s
    # common UTF-8-as-latin1 artefacts
    s = (s.replace("â\x80\x91", "-").replace("â\x80\x93", "-")
           .replace("â\x80\x94", "-").replace("â", "-"))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_sse(text: str) -> dict:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            return json.loads(line[len("data:"):].strip())
    return json.loads(text)


def search_raw(concept: str, cap: int = 25) -> list[RawHit]:
    """Stage 1: raw Commons matches for a concept. Empty list on failure."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "search_indicators",
                       "arguments": {"query": concept}}}
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    try:
        resp = requests.post(MCP_URL, json=body, headers=headers,
                             timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        payload = _parse_sse(resp.text)
        inner = payload["result"]["content"][0]["text"]
        result = json.loads(inner)
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return []

    hits: list[RawHit] = []
    for topic in result.get("topics", []):
        topic_id = topic.get("dcid", "")
        descs = topic.get("alternate_descriptions", [])
        label = _clean_text(descs[0]) if descs else topic_id
        for var in topic.get("member_variables", []):
            hits.append(RawHit(var, label, topic_id))
    return hits[:cap]


# ---------------------------------------------------------------------------
# Stage 2 — LLM grouping
# ---------------------------------------------------------------------------

GROUP_SYSTEM = (
    "You organise UN statistical indicators into the clear choices a non-expert "
    "would pick from. You are given a user's question and a list of raw variables "
    "(each: variable_id + description). Group them by MEANING, not by string. "
    "Rules:\n"
    "- One group per distinct real-world measure. Put sex/age/urbanisation "
    "breakdowns of the SAME measure as 'variants' under one parent, not as "
    "separate groups.\n"
    "- Keep RATE and COUNT as separate groups (a 'rate per 1,000' and a 'number "
    "of deaths' answer different questions). IDs ending in extra 'N' or starting "
    "with 'Count_' are usually counts.\n"
    "- Drop variables that don't actually fit the user's question.\n"
    "- For each group pick the best 'headline' variable_id: the aggregate/total "
    "with no sex/age breakdown.\n"
    "- Give each group a short plain-English label a 14-year-old understands.\n"
    "Return STRICT JSON only, no prose, of the form:\n"
    '{"choices":[{"label":"...","variable_id":"...","measure":"rate|count|",'
    '"variants":[{"label":"...","variable_id":"..."}]}]}'
)


def _llm_group(concept: str, hits: list[RawHit]) -> Optional[list[GroupedChoice]]:
    """Ask the LLM to group raw hits. Returns None if no LLM available/failed."""
    raw = [h.to_dict() for h in hits]
    user_msg = (f'User question: "{concept}"\n\n'
                f'Raw variables:\n{json.dumps(raw, indent=2)}\n\n'
                "Group them now. STRICT JSON only.")

    # Try Anthropic (Claude) first if a key is present, else Groq.
    text = _call_anthropic(user_msg) or _call_groq(user_msg)
    if not text:
        return None
    try:
        # strip any ```json fences
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
        data = json.loads(text)
        out = []
        for c in data.get("choices", []):
            out.append(GroupedChoice(
                label=_clean_text(c.get("label", "")),
                variable_id=c.get("variable_id", ""),
                measure=c.get("measure", ""),
                variants=c.get("variants", []),
            ))
        return out or None
    except (ValueError, KeyError):
        return None


def _call_anthropic(user_msg: str) -> Optional[str]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1500,
                  "system": GROUP_SYSTEM,
                  "messages": [{"role": "user", "content": user_msg}]},
            timeout=40)
        if r.status_code != 200:
            return None
        blocks = r.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except requests.RequestException:
        return None


def _call_groq(user_msg: str) -> Optional[str]:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "system", "content": GROUP_SYSTEM},
                               {"role": "user", "content": user_msg}],
                  "temperature": 0, "max_tokens": 1500},
            timeout=40)
        if r.status_code != 200:
            return None
        return r.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError):
        return None


# ---------------------------------------------------------------------------
# Deterministic fallback (no LLM key, or LLM failed)
# ---------------------------------------------------------------------------

def _dedupe_fallback(hits: list[RawHit]) -> list[GroupedChoice]:
    """Group by base id + rate/count, no LLM. Best-effort string parsing."""
    groups: dict[tuple, dict] = {}
    for h in hits:
        vid = h.variable_id
        base = re.split(r"__|\.", vid)[0]              # strip breakdowns
        is_count = vid.endswith("N") or "MORTN" in vid or vid.startswith("Count_")
        measure = "count" if is_count else "rate"
        is_breakdown = ("__SEX--" in vid) or ("__AGE--" in vid) or vid.endswith("--F") or vid.endswith("--M")
        key = (base, measure)
        g = groups.setdefault(key, {"headline": None, "label": h.description,
                                    "measure": measure, "variants": []})
        if is_breakdown:
            g["variants"].append({"label": vid.split("__")[-1], "variable_id": vid})
        elif g["headline"] is None:
            g["headline"] = vid
    out = []
    for (base, measure), g in groups.items():
        headline = g["headline"] or (g["variants"][0]["variable_id"] if g["variants"] else base)
        lbl = g["label"] + (" — number of deaths" if measure == "count" else "")
        out.append(GroupedChoice(_clean_text(lbl), headline, measure, g["variants"]))
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def find_indicators(concept: str) -> list[GroupedChoice]:
    """
    Full agentic discovery: search the Commons, then group intelligently.
    Falls back to deterministic grouping if no LLM key is configured.
    """
    hits = search_raw(concept)
    if not hits:
        return []
    grouped = _llm_group(concept, hits)
    if grouped is None:                 # no LLM or it failed -> deterministic
        grouped = _dedupe_fallback(hits)
    return grouped


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "child mortality in Kenya"
    print(f'Finding indicators for: "{q}"\n')
    choices = find_indicators(q)
    if not choices:
        print("No matches (or service unreachable).")
    for i, c in enumerate(choices, 1):
        m = f"  ·  {c.measure}" if c.measure else ""
        print(f"  [{i}] {c.label}{m}")
        print(f"      {c.variable_id}")
        if c.variants:
            print(f"      ↳ {len(c.variants)} breakdowns available "
                  f"({', '.join(v['label'] for v in c.variants[:4])}...)")
        print()
