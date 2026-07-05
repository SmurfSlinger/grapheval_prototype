"""KGc backtracking orchestrator: Answer(0) → KGc → Eval(Answer(n), KGc) → Answer(n+1)."""

from __future__ import annotations

from typing import Any, Literal

from src.llm.base import LLMProvider
from src.models import (
    BacktrackingResult,
    BacktrackingTrace,
    Example,
    KgcClaimLabel,
    RevisionEffect,
    Triple,
)
from src.pipeline.answer_generator import AnswerGenerator
from src.pipeline.backtracking_feedback_builder import (
    BacktrackingFeedbackBuilder,
    backtracking_action_for_label,
)
from src.pipeline.backtracking_reviser import BacktrackingReviser
from src.pipeline.context_triple_extractor import ContextTripleExtractor
from src.pipeline.graph_comparator import GraphComparator
from src.pipeline.kg_answer_generator import KgAnswerGenerator
from src.pipeline.kgc_serializer import serialize_kgc_facts
from src.pipeline.triple_extractor import TripleExtractor, claims_differ
from src.storage.neo4j_store import (
    store_kgc_claims_if_enabled,
    store_kgc_facts_if_enabled,
)

Answer0Mode = Literal["preset", "generated"]

_INCOMPLETE_ANSWER_PHRASES = (
    "not specified",
    "not in kgc",
    "not in the kgc",
    "no matching",
    "does not specify",
    "not available in kgc",
    "cannot determine",
    "no information",
    "do not have enough information",
    "insufficient information",
)


def _resolve_answer_0(
    example: Example,
    answer_0_mode: Answer0Mode,
    answer_generator: AnswerGenerator,
) -> tuple[str, str, Answer0Mode, str | None]:
    """Return answer_0, trace source, effective mode, optional warning."""
    if answer_0_mode == "preset" and example.initial_answer:
        return (
            example.initial_answer,
            "example.initial_answer",
            "preset",
            None,
        )

    warning = None
    effective_mode: Answer0Mode = "generated"
    if answer_0_mode == "preset" and not example.initial_answer:
        warning = (
            "Preset mode was selected but no initial_answer exists; "
            "Answer(0) was generated from raw context instead."
        )

    answer_0 = answer_generator.generate(example.question, example.context)
    return answer_0, "generated_from_raw_context", effective_mode, warning


def _detect_kgc_extraction_notice(
    kgc_reference_answer: str,
) -> str | None:
    answer_lower = kgc_reference_answer.lower()
    if any(phrase in answer_lower for phrase in _INCOMPLETE_ANSWER_PHRASES):
        return (
            "KGc may miss facts from the trusted context. When that happens, "
            "correct claims can be marked no evidence. This is a context-to-graph "
            "extraction issue and part of what the research needs to study."
        )
    return None


def _enrich_evaluations(
    extracted_claims: list[Triple],
    aligned_claims: list[Triple],
    evaluated_answer: str,
    evaluations: list,
) -> None:
    for extracted, aligned, evaluation in zip(
        extracted_claims, aligned_claims, evaluations, strict=True
    ):
        if claims_differ(extracted, aligned):
            evaluation.original_claim = extracted
        evaluation.source_sentence = (
            extracted.source_sentence
            or _line_for_triple(extracted, evaluated_answer)
        )
        evaluation.backtracking_action = backtracking_action_for_label(evaluation.label)


def _count_labels(evaluated_claims: list) -> tuple[int, int, int]:
    supported = sum(
        1 for ev in evaluated_claims if ev.label == KgcClaimLabel.SUPPORTED
    )
    contradicted = sum(
        1 for ev in evaluated_claims if ev.label == KgcClaimLabel.CONTRADICTED
    )
    no_evidence = sum(
        1 for ev in evaluated_claims if ev.label == KgcClaimLabel.NO_EVIDENCE
    )
    return supported, contradicted, no_evidence


class BacktrackingRunner:
    def __init__(self, provider: LLMProvider, *, max_iterations: int = 1) -> None:
        self.provider = provider
        self.max_iterations = max_iterations
        self._answer_generator = AnswerGenerator(provider)
        self._context_extractor = ContextTripleExtractor(provider)
        self._kg_answer_generator = KgAnswerGenerator(provider)
        self._claim_extractor = TripleExtractor(provider)
        self._comparator = GraphComparator()
        self._feedback_builder = BacktrackingFeedbackBuilder()
        self._reviser = BacktrackingReviser(provider)

    def run_example(
        self,
        example: Example,
        *,
        answer_0_mode: Answer0Mode = "preset",
    ) -> BacktrackingResult:
        answer_0, answer_0_source, effective_mode, answer_0_warning = _resolve_answer_0(
            example,
            answer_0_mode,
            self._answer_generator,
        )

        kgc_facts = self._context_extractor.extract(example.context)
        serialized_kgc = serialize_kgc_facts(kgc_facts)
        store_kgc_facts_if_enabled(example.id, kgc_facts)

        kgc_reference_answer = self._kg_answer_generator.generate(
            example.question,
            serialized_kgc,
        )
        kgc_extraction_notice = _detect_kgc_extraction_notice(kgc_reference_answer)

        current_answer = answer_0
        stop_reason: str | None = None
        iteration_history: list[dict[str, Any]] = []

        first_extracted: list[Triple] = []
        first_aligned: list[Triple] = []
        first_evaluated: list = []
        first_feedback: list = []
        first_supported = 0
        first_contradicted = 0
        first_no_evidence = 0

        for n in range(self.max_iterations):
            extracted_claims, aligned_claims = self._claim_extractor.extract_kgc_claims(
                current_answer,
                kgc_facts=kgc_facts,
                question=example.question,
            )
            evaluated_claims = self._comparator.compare_claims(
                aligned_claims, kgc_facts
            )
            _enrich_evaluations(
                extracted_claims,
                aligned_claims,
                current_answer,
                evaluated_claims,
            )

            store_kgc_claims_if_enabled(
                example.id,
                iteration=n,
                evaluations=evaluated_claims,
                answer_stage=f"answer_{n}",
            )

            backtracking_feedback = self._feedback_builder.build(evaluated_claims)
            supported_count, contradicted_count, no_evidence_count = _count_labels(
                evaluated_claims
            )

            iteration_history.append(
                {
                    "iteration": n,
                    "evaluated_answer": current_answer,
                    "answer_stage": f"answer_{n}",
                    "supported_count": supported_count,
                    "contradicted_count": contradicted_count,
                    "no_evidence_count": no_evidence_count,
                }
            )

            if n == 0:
                first_extracted = extracted_claims
                first_aligned = aligned_claims
                first_evaluated = evaluated_claims
                first_feedback = backtracking_feedback
                first_supported = supported_count
                first_contradicted = contradicted_count
                first_no_evidence = no_evidence_count

            if contradicted_count == 0 and no_evidence_count == 0:
                stop_reason = "all_claims_supported"
                current_answer = current_answer
                break

            answer_next = self._reviser.revise(
                example.question,
                serialized_kgc,
                current_answer,
                backtracking_feedback,
            )
            current_answer = answer_next
        else:
            if stop_reason is None:
                stop_reason = "max_iterations_reached"

        final_answer = current_answer
        answer_1 = final_answer

        trace = BacktrackingTrace(
            answer_0_source=answer_0_source,
            answer_0_mode=effective_mode,
            kgc_source="extracted_from_trusted_context",
            answer_n_source="generated_from_question_plus_serialized_kgc",
            kgc_reference_answer_source="generated_from_question_plus_serialized_kgc",
            claim_extraction_source="extracted_from_answer_n",
            revision_source=(
                "generated_from_answer_n_plus_kgc_plus_backtracking_feedback"
            ),
            answer_0_warning=answer_0_warning,
        )

        revision_effect = RevisionEffect(
            preserved_supported_count=first_supported,
            corrected_contradicted_count=first_contradicted,
            removed_or_deferred_no_evidence_count=first_no_evidence,
        )

        return BacktrackingResult(
            example_id=example.id,
            question=example.question,
            context=example.context,
            answer_0=answer_0,
            kgc_facts=kgc_facts,
            serialized_kgc=serialized_kgc,
            kgc_reference_answer=kgc_reference_answer,
            graph_grounded_answer=kgc_reference_answer,
            answer_n=answer_0,
            evaluated_answer=answer_0,
            evaluated_answer_iteration=0,
            iteration=0,
            extracted_claims=first_extracted,
            aligned_claims=first_aligned,
            evaluated_claims=first_evaluated,
            backtracking_feedback=first_feedback,
            answer_1=answer_1,
            answer_n_plus_1=answer_1,
            final_answer=final_answer,
            supported_count=first_supported,
            contradicted_count=first_contradicted,
            no_evidence_count=first_no_evidence,
            max_iterations=self.max_iterations,
            trace=trace,
            revision_effect=revision_effect,
            answer_0_mode=effective_mode,
            answer_0_warning=answer_0_warning,
            kgc_extraction_notice=kgc_extraction_notice,
            stop_reason=stop_reason,
            iteration_history=iteration_history,
        )


def _line_for_triple(triple: Triple, answer: str) -> str | None:
    needle = triple.object.lower()
    for line in answer.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if needle in stripped.lower() or triple.relation.replace("_", " ") in stripped.lower():
            return stripped
    return triple.source_sentence
