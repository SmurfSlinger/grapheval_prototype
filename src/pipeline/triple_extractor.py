"""Extract subject-relation-object triples from an answer."""

from __future__ import annotations

from src.config import PROMPT_TRIPLE_EXTRACTION
from src.io_utils import load_prompt, parse_json_response
from src.llm.base import LLMProvider
from src.models import Triple


class TripleExtractor:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_TRIPLE_EXTRACTION)

    def extract(self, answer: str) -> list[Triple]:
        prompt = self._template.format(answer=answer)
        raw = self.provider.complete(prompt)
        data = parse_json_response(raw)
        triples = []
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
