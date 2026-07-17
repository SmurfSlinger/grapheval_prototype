"""Extract question-relevant trusted-context facts for working KGc enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.config import PROMPT_RELEVANT_CONTEXT_EXTRACTION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider
from src.models import KgcFact
from src.pipeline.kgc_serializer import serialize_kgc_facts
from src.pipeline.provider_info import prefers_json_structured_output
from src.pipeline.question_target import (
    derive_question_target,
    filter_minimal_focused_facts,
)
from src.pipeline.structured_output import complete_with_trace, parse_context_facts_response
from src.pipeline.trusted_context_bootstrap import bootstrap_facts_from_context
from src.pipeline.kgc_matching import normalize, normalize_relation, normalize_subject_for_dedupe


@dataclass
class FocusedExtractionTrace:
    retry_count: int = 0
    format_used: str = "json"
    raw_focused_facts: list[KgcFact] = field(default_factory=list)
    filtered_focused_facts: list[KgcFact] = field(default_factory=list)

    def to_dict(self) -> dict:
        from dataclasses import asdict

        return {
            "retry_count": self.retry_count,
            "format_used": self.format_used,
            "raw_focused_facts": [asdict(f) for f in self.raw_focused_facts],
            "filtered_focused_facts": [asdict(f) for f in self.filtered_focused_facts],
        }


class RelevantContextFactExtractor:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_RELEVANT_CONTEXT_EXTRACTION)
        self.prefer_csv = not prefers_json_structured_output(provider)

    def extract(
        self,
        question: str,
        trusted_context: str,
        existing_kgc_facts: list[KgcFact] | None = None,
    ) -> list[KgcFact]:
        facts, _trace = self.extract_with_trace(
            question,
            trusted_context,
            existing_kgc_facts=existing_kgc_facts,
        )
        return facts

    def extract_with_trace(
        self,
        question: str,
        trusted_context: str,
        *,
        existing_kgc_facts: list[KgcFact] | None = None,
    ) -> tuple[list[KgcFact], FocusedExtractionTrace]:
        existing = serialize_kgc_facts(existing_kgc_facts or [])
        prompt = self._template.format(
            question=question.strip(),
            context=trusted_context.strip(),
            existing_kgc_facts=existing,
        )
        facts, trace = complete_with_trace(
            self.provider.complete,
            prompt,
            parse_context_facts_response,
            stage="relevant_context_extraction",
            output_format="json",
        )
        target = derive_question_target(
            question,
            existing_kgc_facts or [],
            trusted_context=trusted_context,
        )
        raw_facts = list(facts)
        bootstrapped = bootstrap_facts_from_context(
            trusted_context=trusted_context,
            target=target,
        )
        # Prefer deterministic bootstrap facts over free-form LLM extractions when
        # both cover the same target slot — bootstrap uses canonical relations.
        merged = _merge_unique_facts(bootstrapped + raw_facts)
        merged = _normalize_fact_subjects(merged, target)
        filtered = filter_minimal_focused_facts(merged, target)
        focused_trace = FocusedExtractionTrace(
            retry_count=trace.retry_count,
            format_used=getattr(trace, "format_used", "json"),
            raw_focused_facts=raw_facts + bootstrapped,
            filtered_focused_facts=filtered,
        )
        return filtered, focused_trace


def _normalize_fact_subjects(
    facts: list[KgcFact],
    target,
) -> list[KgcFact]:
    primary = getattr(target, "primary_subject", None)
    if not primary:
        return facts
    weak = {
        "chart",
        "the chart",
        "patient",
        "the patient",
        "context",
        "record",
        "the record",
        "note",
        "documentation",
    }
    normalized: list[KgcFact] = []
    for fact in facts:
        if normalize(fact.subject) in weak:
            normalized.append(
                KgcFact(
                    subject=primary,
                    relation=fact.relation,
                    object=fact.object,
                    evidence=fact.evidence,
                )
            )
        else:
            normalized.append(fact)
    return normalized


def _merge_unique_facts(facts: list[KgcFact]) -> list[KgcFact]:
    unique: list[KgcFact] = []
    seen: set[tuple[str, str, str]] = set()
    for fact in facts:
        key = (
            normalize_subject_for_dedupe(fact.subject),
            normalize_relation(fact.relation),
            normalize(fact.object),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(fact)
    return unique
