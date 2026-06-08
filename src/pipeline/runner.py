"""Orchestrate the full hallucination feedback pipeline."""

from __future__ import annotations

from src.evaluation.metrics import build_metrics
from src.io_utils import save_result
from src.llm.base import LLMProvider
from src.models import Example, PipelineResult, VerificationLabel
from src.pipeline.answer_generator import AnswerGenerator
from src.pipeline.answer_reviser import AnswerReviser
from src.pipeline.feedback_builder import FeedbackBuilder
from src.pipeline.self_corrector import SelfCorrector
from src.pipeline.triple_extractor import TripleExtractor
from src.pipeline.triple_verifier import LLMJudgeVerifier, TripleVerifier


class PipelineRunner:
    def __init__(self, provider: LLMProvider) -> None:
        self.answer_generator = AnswerGenerator(provider)
        self.self_corrector = SelfCorrector(provider)
        self.triple_extractor = TripleExtractor(provider)
        self.triple_verifier = TripleVerifier(LLMJudgeVerifier(provider))
        self.feedback_builder = FeedbackBuilder()
        self.answer_reviser = AnswerReviser(provider)

    def run_example(self, example: Example) -> PipelineResult:
        initial_answer = example.initial_answer or self.answer_generator.generate(
            example.question, example.context
        )

        self_corrected_answer = self.self_corrector.correct(
            initial_answer, example.context
        )

        extracted_triples = self.triple_extractor.extract(initial_answer)
        verification_results = self.triple_verifier.verify_all(
            extracted_triples, example.context
        )
        feedback = self.feedback_builder.build(verification_results)

        graph_feedback_revised_answer = None
        graph_revised_triples = []
        graph_revised_verification_results = []

        if feedback:
            graph_feedback_revised_answer = self.answer_reviser.revise(
                initial_answer, example.context, feedback
            )
            graph_revised_triples = self.triple_extractor.extract(
                graph_feedback_revised_answer
            )
            graph_revised_verification_results = self.triple_verifier.verify_all(
                graph_revised_triples, example.context
            )

        metrics = build_metrics(
            initial_verification=verification_results,
            graph_revision_needed=bool(feedback),
            revised_verification=graph_revised_verification_results or None,
        )

        return PipelineResult(
            example_id=example.id,
            question=example.question,
            context=example.context,
            initial_answer=initial_answer,
            extracted_triples=extracted_triples,
            verification_results=verification_results,
            feedback=feedback,
            revised_answer=graph_feedback_revised_answer,
            self_corrected_answer=self_corrected_answer,
            graph_feedback_revised_answer=graph_feedback_revised_answer,
            graph_revised_triples=graph_revised_triples,
            graph_revised_verification_results=graph_revised_verification_results,
            metrics=metrics,
        )

    def run_and_save(
        self,
        example: Example,
        *,
        filename: str | None = None,
    ) -> PipelineResult:
        result = self.run_example(example)
        save_result(result, filename=filename)
        return result

    @staticmethod
    def print_summary(result: PipelineResult) -> None:
        m = result.metrics
        print(f"\n--- {result.example_id} ---")
        print(f"Initial triples:   {m.initial_total_triples}")
        print(f"  Supported:       {m.initial_supported_count}")
        print(f"  Contradicted:    {m.initial_contradicted_count}")
        print(f"  Not enough info: {m.initial_not_enough_info_count}")
        print(f"Graph revision needed: {m.graph_revision_needed}")
        if result.self_corrected_answer:
            print(f"Self-corrected:    {result.self_corrected_answer}")
        if result.graph_feedback_revised_answer:
            print(f"Graph-feedback:    {result.graph_feedback_revised_answer}")
            if m.graph_revised_contradicted_count is not None:
                print(
                    "After graph revision — "
                    f"contradicted: {m.graph_revised_contradicted_count}, "
                    f"not enough info: {m.graph_revised_not_enough_info_count}"
                )
