"""Extract subject-relation-object facts from trusted context for KGc."""

from __future__ import annotations

from src.config import PROMPT_CONTEXT_TRIPLE_EXTRACTION
from src.io_utils import load_prompt, parse_json_response
from src.llm.base import LLMProvider
from src.models import KgcFact


class ContextTripleExtractor:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_CONTEXT_TRIPLE_EXTRACTION)

    def extract(self, context: str) -> list[KgcFact]:
        prompt = self._template.format(context=context)
        raw = self.provider.complete(prompt)
        data = parse_json_response(raw)
        facts: list[KgcFact] = []
        for item in data.get("triples", []):
            facts.append(
                KgcFact(
                    subject=item["subject"],
                    relation=item["relation"],
                    object=item["object"],
                    evidence=item.get("evidence"),
                )
            )
        return facts
