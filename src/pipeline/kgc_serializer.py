"""Serialize KGc facts into compact structured text for graph-grounded answering."""

from __future__ import annotations

from src.models import KgcFact


def serialize_kgc_facts(facts: list[KgcFact]) -> str:
    if not facts:
        return "KGc facts:\n(none)"
    lines = ["KGc facts:"]
    for fact in facts:
        lines.append(f"- {fact.subject} -- {fact.relation} --> {fact.object}")
    return "\n".join(lines)
