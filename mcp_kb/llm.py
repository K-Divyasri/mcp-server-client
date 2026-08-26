"""Deciding which MCP tool to call: an offline keyword router (no key, no
network) and, behind --real, the actual Claude API.

The teaching point here mirrors ai/11-function-calling-assistant's agent
loop, but with one crucial difference: FakeRouter.decide() is handed the
tool list DISCOVERED FROM THE SERVER over MCP, not a hardcoded schema. Swap
the server for a different one and the router (badly) adapts to whatever
tools show up -- that adaptability, not the router's intelligence, is what
MCP buys you.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from mcp_kb.weather import OFFLINE_WEATHER

DEFAULT_MODEL = os.environ.get("MCP_KB_MODEL", "claude-haiku-4-5")


def has_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


@dataclass
class Decision:
    tool_name: str | None
    arguments: dict
    final_answer: str | None = None


def _extract_city(question: str) -> str:
    q = question.lower()
    for city in OFFLINE_WEATHER:
        if city in q:
            return city
    match = re.search(r"\b(?:in|for|at)\s+([a-zA-Z ]+?)(?:[?.!]|$)", q)
    if match:
        return match.group(1).strip()
    return question.strip()


_SEARCH_STOPWORDS = {
    "search",
    "find",
    "notes",
    "note",
    "about",
    "for",
    "on",
    "my",
    "of",
    "what",
    "do",
    "i",
    "know",
    "have",
    "any",
}


def _extract_query(question: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", question.lower())
    kept = [w for w in words if w not in _SEARCH_STOPWORDS]
    return " ".join(kept) if kept else question.strip()


class FakeRouter:
    """Deterministic, keyword-only tool selection. Brittle on purpose -- see
    knowledge/06_offline_vs_real.md for why a real model does better."""

    def decide(self, question: str, tool_names: list[str]) -> Decision:
        q = question.lower()

        if "weather" in q and "get_weather" in tool_names:
            return Decision("get_weather", {"city": _extract_city(question)})

        if ("tag" in q or "tags" in q) and "list_tags" in tool_names:
            return Decision("list_tags", {})

        if any(w in q for w in ("remember this", "save this", "add a note", "note that")) and "add_note" in tool_names:
            title = question.strip().rstrip("?.!")[:50]
            return Decision("add_note", {"title": title, "body": question.strip(), "tags": ""})

        if "search_notes" in tool_names:
            return Decision("search_notes", {"query": _extract_query(question)})

        return Decision(None, {}, final_answer="I don't have a tool that can answer that.")


def call_claude(model: str, messages: list[dict], tools: list[dict], max_tokens: int = 1024):
    """Thin wrapper so agent.py doesn't import anthropic directly -- makes
    it obvious this is the ONLY place a real network call to Claude happens."""
    import anthropic

    client = anthropic.Anthropic()
    return client.messages.create(model=model, max_tokens=max_tokens, tools=tools, messages=messages)
