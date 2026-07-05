"""Revise a graph-grounded answer using backtracking feedback and KGc facts."""

from __future__ import annotations

import json

from src.config import PROMPT_BACKTRACKING_REVISION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider
from src.models import BacktrackingFeedbackItem


class BacktrackingReviser:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_BACKTRACKING_REVISION)

    def revise(
        self,
        question: str,
        serialized_kgc: str,
        answer: str,
        feedback: list[BacktrackingFeedbackItem],
    ) -> str:
        feedback_payload = [
            {
                "triple": {
                    "subject": item.triple.subject,
                    "relation": item.triple.relation,
                    "object": item.triple.object,
                },
                "label": item.label.value,
                "instruction": item.instruction,
                "reason": item.reason,
                "evidence": item.evidence,
                "conflicting_object": item.conflicting_object,
            }
            for item in feedback
            if item.label.value != "SUPPORTED"
        ]
        if not feedback_payload:
            return answer
        prompt = self._template.format(
            question=question,
            kgc_facts=serialized_kgc,
            answer=answer,
            feedback=json.dumps(feedback_payload, indent=2),
        )
        return self.provider.complete(prompt).strip()
