"""Orchestrate the full hallucination feedback pipeline."""

from __future__ import annotations

from src.io_utils import save_result
from src.llm.base import LLMProvider
from src.models import Example, PipelineResult, VerificationLabel
from src.pipeline.answer_generator import AnswerGenerator
from src.pipeline.answer_reviser import AnswerReviser
from src.pipeline.feedback_builder import FeedbackBuilder
from src.pipeline.triple_extractor import TripleExtractor
from src.pipeline.triple_verifier import LLMJudgeVerifier, TripleVerifier


class PipelineRunner:
    def __init__(self, provider: LLMProvider) -> None:
        self.answer_generator = AnswerGenerator(provider)
        self.triple_extractor = TripleExtractor(provider)
        self.triple_verifier = TripleVerifier(LLMJudgeVerifier(provider))
        self.feedback_builder = FeedbackBuilder()
        self.answer_reviser = AnswerReviser(provider)

    def run_example(self, example: Example) -> PipelineResult:
        initial_answer = example.initial_answer or self.answer_generator.generate(
            example.question, example.context
        )

        extracted_triples = self.triple_extractor.extract(initial_answer)
        verification_results = self.triple_verifier.verify_all(
            extracted_triples, example.context
        )
        feedback = self.feedback_builder.build(verification_results)

        revised_answer = None
        if feedback:
            revised_answer = self.answer_reviser.revise(
                initial_answer, example.context, feedback
            )

        return PipelineResult(
            example_id=example.id,
            question=example.question,
            context=example.context,
            initial_answer=initial_answer,
            extracted_triples=extracted_triples,
            verification_results=verification_results,
            feedback=feedback,
            revised_answer=revised_answer,
        )

    def run_and_save(self, example: Example) -> PipelineResult:
        result = self.run_example(example)
        save_result(result)
        return result

    @staticmethod
    def print_summary(result: PipelineResult) -> None:
        counts = {label: 0 for label in VerificationLabel}
        for vr in result.verification_results:
            counts[vr.label] += 1

        revision_needed = bool(result.feedback)
        print(f"\n--- {result.example_id} ---")
        print(f"Triples extracted: {len(result.extracted_triples)}")
        print(f"  Supported:       {counts[VerificationLabel.SUPPORTED]}")
        print(f"  Contradicted:    {counts[VerificationLabel.CONTRADICTED]}")
        print(f"  Not enough info: {counts[VerificationLabel.NOT_ENOUGH_INFO]}")
        print(f"Revision needed:   {revision_needed}")
        if result.revised_answer:
            print(f"Revised answer:    {result.revised_answer}")
