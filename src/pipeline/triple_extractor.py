"""Extract subject-relation-object triples from an answer."""

from __future__ import annotations

from src.config import PROMPT_KG_CLAIM_EXTRACTION, PROMPT_TRIPLE_EXTRACTION
from src.io_utils import load_prompt, parse_json_response
from src.llm.base import LLMProvider
from src.models import KgcFact, Triple
from src.pipeline.kgc_matching import normalize, normalize_relation
from src.pipeline.kgc_schema_aligner import align_claims_to_kgc_schema
from src.pipeline.kgc_serializer import serialize_kgc_facts


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
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_TRIPLE_EXTRACTION)
        self._kg_template = load_prompt(PROMPT_KG_CLAIM_EXTRACTION)

    def extract(
        self,
        answer: str,
        kgc_facts: list[KgcFact] | None = None,
        question: str | None = None,
    ) -> list[Triple]:
        extracted, aligned = self.extract_kgc_claims(
            answer,
            kgc_facts=kgc_facts,
            question=question,
        )
        return aligned if kgc_facts else extracted

    def extract_kgc_claims(
        self,
        answer: str,
        *,
        kgc_facts: list[KgcFact] | None = None,
        question: str | None = None,
    ) -> tuple[list[Triple], list[Triple]]:
        if kgc_facts:
            prompt = self._kg_template.format(
                question=question or "",
                kgc_facts=serialize_kgc_facts(kgc_facts),
                answer=answer,
            )
        else:
            prompt = self._template.format(answer=answer)
        raw = self.provider.complete(prompt)
        extracted = _parse_triples(parse_json_response(raw))
        if not kgc_facts:
            return extracted, extracted
        aligned = align_claims_to_kgc_schema(extracted, kgc_facts)
        return extracted, aligned
