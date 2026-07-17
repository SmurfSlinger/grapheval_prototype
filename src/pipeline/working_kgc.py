"""Working KGc state with provenance-aware candidate update scaffold."""

from __future__ import annotations

from src.models import (
    KgcCandidateUpdate,
    KgcClaimLabel,
    KgcEvaluationResult,
    KgcFact,
    KgcProvenanceType,
    Triple,
    WorkingKgcAddition,
)
from src.pipeline.kgc_matching import (
    normalize,
    normalize_relation,
    normalize_subject_for_dedupe,
)


def _fact_key(fact: KgcFact) -> tuple[str, str, str]:
    return (
        normalize_subject_for_dedupe(fact.subject),
        normalize_relation(fact.relation),
        normalize(fact.object),
    )


class WorkingKgcState:
    """Base KGc from context plus focused trusted-context enrichments."""

    def __init__(
        self,
        base_facts: list[KgcFact],
        *,
        auto_promote: bool = False,
    ) -> None:
        self.base_kgc: list[KgcFact] = list(base_facts)
        self.working_kgc: list[KgcFact] = list(base_facts)
        self.candidate_updates: list[KgcCandidateUpdate] = []
        self.focused_additions: list[WorkingKgcAddition] = []
        self.auto_promote = auto_promote
        self._working_keys: set[tuple[str, str, str]] = set()
        self._key_to_canonical_subject: dict[tuple[str, str, str], str] = {}
        for fact in self.working_kgc:
            key = _fact_key(fact)
            self._working_keys.add(key)
            self._key_to_canonical_subject.setdefault(key, fact.subject)

    def facts_for_comparison(self) -> list[KgcFact]:
        return list(self.working_kgc)

    def merge_focused_facts(
        self,
        facts: list[KgcFact],
        *,
        sub_question_id: int,
    ) -> list[KgcFact]:
        """Merge question-directed trusted-context facts; dedupe normalized triples."""
        added: list[KgcFact] = []
        for fact in facts:
            key = _fact_key(fact)
            if key in self._working_keys:
                continue
            self.working_kgc.append(fact)
            self._working_keys.add(key)
            self._key_to_canonical_subject.setdefault(key, fact.subject)
            self.focused_additions.append(
                WorkingKgcAddition(
                    fact=fact,
                    provenance=KgcProvenanceType.TRUSTED_CONTEXT,
                    extraction_scope="sub_question_focused",
                    sub_question_id=sub_question_id,
                )
            )
            added.append(fact)
        return added

    def merge_derived_facts(
        self,
        facts: list[KgcFact],
        *,
        sub_question_id: int,
        derivation_type: str,
        evidence_spans: list[str] | None = None,
        derivation_explanation: str | None = None,
    ) -> list[KgcFact]:
        added: list[KgcFact] = []
        for fact in facts:
            key = _fact_key(fact)
            if key in self._working_keys:
                continue
            self.working_kgc.append(fact)
            self._working_keys.add(key)
            self._key_to_canonical_subject.setdefault(key, fact.subject)
            self.focused_additions.append(
                WorkingKgcAddition(
                    fact=fact,
                    provenance=KgcProvenanceType.DERIVED_FROM_TRUSTED_CONTEXT,
                    extraction_scope="target_fact_derivation",
                    sub_question_id=sub_question_id,
                    derivation_type=derivation_type,
                    evidence_spans=list(evidence_spans or []),
                    derivation_explanation=derivation_explanation,
                )
            )
            added.append(fact)
        return added

    def record_evaluation(
        self,
        evaluation: KgcEvaluationResult,
        *,
        sub_question_id: int | None = None,
        iteration: int | None = None,
    ) -> None:
        """Log candidate updates; promotion requires explicit validation policy."""
        if evaluation.label == KgcClaimLabel.SUPPORTED and evaluation.matched_kgc_fact:
            self._record_candidate(
                evaluation.matched_kgc_fact,
                KgcProvenanceType.SUPPORTED_BY_EXISTING_KGC,
                sub_question_id=sub_question_id,
                iteration=iteration,
                promoted=False,
                rejection_reason="Already present in base/working KGc; no promotion needed.",
            )
            return

        if evaluation.label != KgcClaimLabel.SUPPORTED:
            return

        candidate = KgcFact(
            subject=evaluation.triple.subject,
            relation=evaluation.triple.relation,
            object=evaluation.triple.object,
            evidence=evaluation.source_sentence,
        )
        key = _fact_key(candidate)
        if key in self._working_keys:
            self._record_candidate(
                candidate,
                KgcProvenanceType.SUPPORTED_BY_EXISTING_KGC,
                sub_question_id=sub_question_id,
                iteration=iteration,
                promoted=False,
                rejection_reason="Duplicate of existing working KGc fact.",
            )
            return

        self._record_candidate(
            candidate,
            KgcProvenanceType.DERIVED_FROM_SUPPORTED_FACTS,
            sub_question_id=sub_question_id,
            iteration=iteration,
            promoted=False,
            rejection_reason=(
                "Automatic promotion disabled; supported claim logged as candidate only."
            ),
        )

    def _record_candidate(
        self,
        fact: KgcFact,
        provenance: KgcProvenanceType,
        *,
        sub_question_id: int | None,
        iteration: int | None,
        promoted: bool,
        rejection_reason: str | None,
    ) -> None:
        update = KgcCandidateUpdate(
            fact=fact,
            provenance=provenance,
            sub_question_id=sub_question_id,
            iteration=iteration,
            promoted=promoted,
            rejection_reason=rejection_reason,
        )
        self.candidate_updates.append(update)
        if promoted and self.auto_promote:
            key = _fact_key(fact)
            if key not in self._working_keys:
                self.working_kgc.append(fact)
                self._working_keys.add(key)
                update.promoted = True
                update.rejection_reason = None

    def build_carry_forward_context(
        self,
        resolved: list[tuple[int, str, str]],
    ) -> str:
        """Text context from resolved sub-questions (not auto-inserted as KGc facts)."""
        if not resolved:
            return ""
        lines = ["Previously resolved sub-questions:"]
        for sub_id, question, answer in resolved:
            lines.append(f"{sub_id}. Q: {question}")
            lines.append(f"   A: {answer}")
        return "\n".join(lines)
