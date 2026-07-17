"""Extract subject-relation-object triples from an answer."""

from __future__ import annotations

from src.config import (
    PROMPT_KG_CLAIM_EXTRACTION,
    PROMPT_KG_CLAIM_EXTRACTION_CSV,
    PROMPT_TRIPLE_EXTRACTION,
)
from src.io_utils import load_prompt, parse_json_response
from src.llm.base import LLMProvider
from src.models import KgcFact, Triple
from src.pipeline.kgc_matching import normalize, normalize_relation
from src.pipeline.claim_grounding import ground_claim_objects_in_answer
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema
from src.pipeline.question_target import (
    condition_claims_to_question,
    dedupe_minimal_claims,
    derive_question_target,
)
from src.pipeline.kgc_serializer import serialize_kgc_facts
from src.pipeline.provider_info import prefers_json_structured_output
from src.pipeline.structured_output import (
    StructuredOutputError,
    complete_with_trace,
    parse_claims_response,
)


def _parse_triples(data: dict) -> list[Triple]:
    triples: list[Triple] = []
    for item in data.get("triples", []):
        triples.append(
            Triple(
                subject=item["subject"],
                relation=item["relation"],
                object=item["object"],
                source_sentence=item.get("source_sentence"),
            )
        )
    return triples


def claims_differ(left: Triple, right: Triple) -> bool:
    return (
        normalize(left.subject) != normalize(right.subject)
        or normalize_relation(left.relation) != normalize_relation(right.relation)
        or normalize(left.object) != normalize(right.object)
    )


class TripleExtractor:
    def __init__(
        self,
        provider: LLMProvider,
        *,
        prefer_csv: bool | None = None,
    ) -> None:
        self.provider = provider
        if prefer_csv is None:
            prefer_csv = not prefers_json_structured_output(provider)
        self.prefer_csv = prefer_csv
        self._template = load_prompt(PROMPT_TRIPLE_EXTRACTION)
        self._kg_csv_template = load_prompt(PROMPT_KG_CLAIM_EXTRACTION_CSV)
        self._kg_json_template = load_prompt(PROMPT_KG_CLAIM_EXTRACTION)

    def extract(
        self,
        answer: str,
        kgc_facts: list[KgcFact] | None = None,
        question: str | None = None,
        trusted_context: str | None = None,
    ) -> list[Triple]:
        extracted, aligned = self.extract_kgc_claims(
            answer,
            kgc_facts=kgc_facts,
            question=question,
            trusted_context=trusted_context,
        )
        return aligned if kgc_facts else extracted

    def extract_kgc_claims(
        self,
        answer: str,
        *,
        kgc_facts: list[KgcFact] | None = None,
        question: str | None = None,
        trusted_context: str | None = None,
    ) -> tuple[list[Triple], list[Triple]]:
        if kgc_facts:
            primary_format = "json" if not self.prefer_csv else "csv"
            template = (
                self._kg_json_template if primary_format == "json" else self._kg_csv_template
            )
            prompt = template.format(
                question=question or "",
                kgc_facts=serialize_kgc_facts(kgc_facts),
                answer=answer,
            )
            alternate_prompt = None
            if primary_format == "csv":
                alternate_prompt = self._kg_json_template.format(
                    question=question or "",
                    kgc_facts=serialize_kgc_facts(kgc_facts),
                    answer=answer,
                )
            try:
                extracted, _trace = complete_with_trace(
                    self.provider.complete,
                    prompt,
                    parse_claims_response,
                    stage="kg_claim_extraction",
                    output_format=primary_format,
                    alternate_prompt=alternate_prompt,
                )
            except StructuredOutputError as exc:
                raise ValueError(f"Claim extraction failed: {exc}") from exc
            question_text = question or ""
            target = derive_question_target(
                question_text,
                kgc_facts,
                trusted_context=trusted_context,
            )
            extracted = condition_claims_to_question(
                extracted,
                question_text,
                answer,
                target,
                kgc_facts,
            )
            extracted = ground_claim_objects_in_answer(extracted, answer)
            extracted = dedupe_minimal_claims(extracted, target, answer)
            aligned = align_claims_to_kgc_schema(
                extracted, kgc_facts, question_target=target
            )
            return extracted, aligned

        prompt = self._template.format(answer=answer)
        raw = self.provider.complete(prompt)
        extracted = _parse_triples(parse_json_response(raw))
        return extracted, extracted
