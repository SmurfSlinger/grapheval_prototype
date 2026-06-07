"""Deterministic mock LLM for running the pipeline without API keys."""

from __future__ import annotations

import json

from src.llm.base import LLMProvider


class MockProvider(LLMProvider):
    """Returns placeholder outputs keyed off prompt content."""

    def complete(self, prompt: str) -> str:
        lowered = prompt.lower()

        if "extract factual triples" in lowered or '"triples"' in lowered:
            return self._triple_extraction_response(prompt)
        if "verify whether the triple" in lowered or '"label"' in lowered:
            return self._triple_verification_response(prompt)
        if "revise the answer" in lowered or "feedback (json)" in lowered:
            return self._answer_revision_response()
        if "context:" in lowered and "question:" in lowered:
            return self._answer_generation_response(prompt)

        return "Mock LLM response."

    def _answer_generation_response(self, prompt: str) -> str:
        # Fallback generation: echo context facts in a simple sentence.
        for line in prompt.splitlines():
            if line.strip().startswith("Context:"):
                continue
            if line.strip() and not line.strip().startswith("Question:"):
                if "hyundai" in line.lower():
                    return line.strip()
        return "I do not have enough information to answer."

    def _triple_extraction_response(self, prompt: str) -> str:
        triples = [
            {
                "subject": "2018 Hyundai Sonata SE",
                "relation": "has_engine",
                "object": "2.4L turbo engine",
                "source_sentence": (
                    "The 2018 Hyundai Sonata SE has a 2.4L turbo engine "
                    "and was assembled in Korea."
                ),
            },
            {
                "subject": "2018 Hyundai Sonata SE",
                "relation": "assembled_in",
                "object": "Korea",
                "source_sentence": (
                    "The 2018 Hyundai Sonata SE has a 2.4L turbo engine "
                    "and was assembled in Korea."
                ),
            },
        ]
        return json.dumps({"triples": triples}, indent=2)

    def _triple_verification_response(self, prompt: str) -> str:
        relation = self._extract_field(prompt, "relation")
        obj = self._extract_field(prompt, "object")

        if relation == "has_engine" and "turbo" in obj.lower():
            return json.dumps(
                {
                    "label": "NOT_ENOUGH_INFO",
                    "evidence": "The 2018 Hyundai Sonata SE has a 2.4L engine",
                    "reason": (
                        "Context mentions a 2.4L engine but does not mention turbo; "
                        "adding turbo is unsupported."
                    ),
                },
                indent=2,
            )

        if relation == "assembled_in" and obj.lower() == "korea":
            return json.dumps(
                {
                    "label": "CONTRADICTED",
                    "evidence": "was assembled in Alabama",
                    "reason": "Context states assembly in Alabama, not Korea.",
                },
                indent=2,
            )

        return json.dumps(
            {
                "label": "SUPPORTED",
                "evidence": "Context supports this claim.",
                "reason": "No conflict detected in mock verifier.",
            },
            indent=2,
        )

    def _answer_revision_response(self) -> str:
        return (
            "The 2018 Hyundai Sonata SE has a 2.4L engine "
            "and was assembled in Alabama."
        )

    @staticmethod
    def _extract_field(prompt: str, field_name: str) -> str:
        prefix = f"- {field_name}:"
        for line in prompt.splitlines():
            if line.strip().lower().startswith(prefix):
                return line.split(":", 1)[1].strip()
        return ""
