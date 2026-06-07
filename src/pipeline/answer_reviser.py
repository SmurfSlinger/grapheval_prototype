"""Revise an answer using structured triple-level feedback."""

from __future__ import annotations

import json

from src.config import PROMPT_ANSWER_REVISION
from src.io_utils import load_prompt
from src.llm.base import LLMProvider
from src.models import FeedbackItem


class AnswerReviser:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._template = load_prompt(PROMPT_ANSWER_REVISION)

    def revise(
        self,
        answer: str,
        context: str,
        feedback: list[FeedbackItem],
    ) -> str:
        feedback_payload = [
            {
                "triple": {
                    "subject": item.triple.subject,
                    "relation": item.triple.relation,
                    "object": item.triple.object,
                },
                "status": item.status.value,
                "instruction": item.instruction,
                "evidence": item.evidence,
            }
            for item in feedback
        ]
        prompt = self._template.format(
            context=context,
            answer=answer,
            feedback=json.dumps(feedback_payload, indent=2),
        )
        return self.provider.complete(prompt).strip()
