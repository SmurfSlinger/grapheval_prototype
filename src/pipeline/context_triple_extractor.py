"""Extract subject-relation-object facts from trusted context for KGc."""

from __future__ import annotations

from src.config import (
    PROMPT_CONTEXT_TRIPLE_EXTRACTION,
    PROMPT_CONTEXT_TRIPLE_EXTRACTION_CSV,
)
from src.io_utils import load_prompt
from src.llm.base import LLMProvider
from src.models import KgcFact
from src.pipeline.provider_info import prefers_json_structured_output
from src.pipeline.structured_output import (
    KgcExtractionError,
    StructuredExtractionTrace,
    StructuredOutputError,
    complete_with_trace,
    parse_context_facts_response,
)


class ContextTripleExtractor:
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
        self._csv_template = load_prompt(PROMPT_CONTEXT_TRIPLE_EXTRACTION_CSV)
        self._json_template = load_prompt(PROMPT_CONTEXT_TRIPLE_EXTRACTION)

    def extract(self, context: str) -> list[KgcFact]:
        facts, _trace = self.extract_with_trace(context)
        return facts

    def extract_with_trace(
        self, context: str
    ) -> tuple[list[KgcFact], StructuredExtractionTrace]:
        primary_format = "json" if not self.prefer_csv else "csv"
        primary_template = self._json_template if primary_format == "json" else self._csv_template
        prompt = primary_template.format(context=context)
        alternate_prompt = None
        if primary_format == "csv":
            alternate_prompt = self._json_template.format(context=context)

        facts, trace = complete_with_trace(
            self.provider.complete,
            prompt,
            parse_context_facts_response,
            stage="context_triple_extraction",
            output_format=primary_format,
            alternate_prompt=alternate_prompt,
        )

        if not facts:
            raise KgcExtractionError(
                "Context triple extraction returned zero facts.",
                trace=trace,
            )
        return facts, trace
