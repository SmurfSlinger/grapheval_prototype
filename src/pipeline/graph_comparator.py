"""Compare answer claims against KGc facts using normalized matching."""

from __future__ import annotations

from src.models import KgcClaimLabel, KgcEvaluationResult, KgcFact, Triple
from src.pipeline.kgc_matching import (
    is_engine_object,
    is_engine_power_relation,
    is_negated_relation,
    is_schema_aligned_claim,
    normalize,
    normalize_relation,
    relations_equivalent_for_engine_claim,
    subjects_compatible_first_stage,
)


def _fact_evidence(fact: KgcFact) -> str:
    return fact.evidence or f"{fact.subject} -- {fact.relation} --> {fact.object}"


class GraphComparator:
    def compare_claims(
        self,
        claims: list[Triple],
        kgc_facts: list[KgcFact],
    ) -> list[KgcEvaluationResult]:
        exact_index: dict[tuple[str, str, str], KgcFact] = {}
        relation_index: dict[tuple[str, str], list[KgcFact]] = {}

        for fact in kgc_facts:
            subject = normalize(fact.subject)
            relation = normalize_relation(fact.relation)
            obj = normalize(fact.object)
            exact_index[(subject, relation, obj)] = fact
            relation_index.setdefault((subject, relation), []).append(fact)

        return [
            self._evaluate_claim(claim, exact_index, relation_index, kgc_facts)
            for claim in claims
        ]

    def _evaluate_claim(
        self,
        claim: Triple,
        exact_index: dict[tuple[str, str, str], KgcFact],
        relation_index: dict[tuple[str, str], list[KgcFact]],
        kgc_facts: list[KgcFact],
    ) -> KgcEvaluationResult:
        subject = normalize(claim.subject)
        relation = normalize_relation(claim.relation)
        obj = normalize(claim.object)
        full_key = (subject, relation, obj)

        if full_key in exact_index:
            fact = exact_index[full_key]
            if is_schema_aligned_claim(claim.source_sentence):
                reason = (
                    "Claim aligned to matching KGc fact using canonical KGc subject/relation."
                )
            elif (
                normalize_relation(claim.relation) == normalize_relation(fact.relation)
                and claim.relation.strip() == fact.relation.strip()
            ):
                reason = "Claim matches a KGc fact."
            else:
                reason = "Claim matches KGc fact after relation normalization."
            return KgcEvaluationResult(
                triple=claim,
                label=KgcClaimLabel.SUPPORTED,
                reason=reason,
                evidence=_fact_evidence(fact),
                matched_kgc_fact=fact,
            )

        rel_key = (subject, relation)
        if rel_key in relation_index:
            conflicting = relation_index[rel_key][0]
            return KgcEvaluationResult(
                triple=claim,
                label=KgcClaimLabel.CONTRADICTED,
                reason=(
                    f"Claim object '{claim.object}' conflicts with KGc fact "
                    f"'{conflicting.object}' for relation '{claim.relation}'."
                ),
                evidence=_fact_evidence(conflicting),
                conflicting_object=conflicting.object,
                conflicting_fact=conflicting,
            )

        polarity_conflict = self._find_polarity_conflict(subject, obj, relation, kgc_facts)
        if polarity_conflict is not None:
            return KgcEvaluationResult(
                triple=claim,
                label=KgcClaimLabel.CONTRADICTED,
                reason=(
                    f"Claim relation '{claim.relation}' conflicts with KGc relation "
                    f"'{polarity_conflict.relation}' for the same subject and object "
                    f"(negation polarity mismatch)."
                ),
                evidence=_fact_evidence(polarity_conflict),
                conflicting_object=polarity_conflict.object,
                conflicting_fact=polarity_conflict,
            )

        engine_conflict = self._find_engine_power_conflict(
            claim, subject, relation, obj, kgc_facts
        )
        if engine_conflict is not None:
            return KgcEvaluationResult(
                triple=claim,
                label=KgcClaimLabel.CONTRADICTED,
                reason=(
                    f"Claim object '{claim.object}' conflicts with KGc fact "
                    f"'{engine_conflict.object}' for engine power relation "
                    f"'{claim.relation}'."
                ),
                evidence=_fact_evidence(engine_conflict),
                conflicting_object=engine_conflict.object,
                conflicting_fact=engine_conflict,
            )

        return KgcEvaluationResult(
            triple=claim,
            label=KgcClaimLabel.NO_EVIDENCE,
            reason="KGc has no matching fact for this claim.",
            evidence="No supporting KGc fact found.",
        )

    @staticmethod
    def _find_polarity_conflict(
        subject: str,
        obj: str,
        relation: str,
        kgc_facts: list[KgcFact],
    ) -> KgcFact | None:
        claim_negated = is_negated_relation(relation)
        for fact in kgc_facts:
            if normalize(fact.subject) != subject or normalize(fact.object) != obj:
                continue
            if normalize_relation(fact.relation) == relation:
                continue
            if is_negated_relation(fact.relation) != claim_negated:
                return fact
        return None

    @staticmethod
    def _find_engine_power_conflict(
        claim: Triple,
        subject: str,
        relation: str,
        obj: str,
        kgc_facts: list[KgcFact],
    ) -> KgcFact | None:
        if not is_engine_object(claim.object) or not is_engine_power_relation(
            claim.relation
        ):
            return None

        for fact in kgc_facts:
            if not is_engine_power_relation(fact.relation):
                continue
            if not relations_equivalent_for_engine_claim(claim.relation, fact.relation):
                continue
            if not subjects_compatible_first_stage(claim.subject, fact.subject):
                continue
            if normalize(fact.object) == obj:
                continue
            return fact
        return None
