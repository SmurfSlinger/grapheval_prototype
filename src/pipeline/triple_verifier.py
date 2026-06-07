"""Verify triples against trusted context (LLM-as-judge by default)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.config import PROMPT_TRIPLE_VERIFICATION
from src.io_utils import load_prompt, parse_json_response
from src.llm.base import LLMProvider
from src.models import Triple, VerificationLabel, VerificationResult


class TripleVerifierBackend(ABC):
    """Pluggable verification backend (LLM judge now, NLI later)."""

    @abstractmethod
    def verify(self, triple: Triple, context: str) -> VerificationResult:
        ...


class LLMJudgeVerifier(TripleVerifierBackend):
    """Verify each triple with an LLM prompt."""

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_TRIPLE_VERIFICATION)

    def verify(self, triple: Triple, context: str) -> VerificationResult:
        prompt = self._template.format(
            context=context,
            subject=triple.subject,
            relation=triple.relation,
            object=triple.object,
        )
        raw = self.provider.complete(prompt)
        data = parse_json_response(raw)
        label = VerificationLabel(data["label"])
        return VerificationResult(
            triple=triple,
            label=label,
            evidence=data.get("evidence", ""),
            reason=data.get("reason", ""),
        )


class NLIVerifier(TripleVerifierBackend):
    """Placeholder for future NLI-based verification."""

    def verify(self, triple: Triple, context: str) -> VerificationResult:
        raise NotImplementedError(
            "NLI verification is not implemented yet. Use LLMJudgeVerifier for now."
        )


class TripleVerifier:
    """Facade that verifies a list of triples with a chosen backend."""

    def __init__(self, backend: TripleVerifierBackend) -> None:
        self.backend = backend

    def verify_all(self, triples: list[Triple], context: str) -> list[VerificationResult]:
        return [self.backend.verify(triple, context) for triple in triples]
