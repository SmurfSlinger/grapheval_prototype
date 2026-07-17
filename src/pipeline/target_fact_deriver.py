"""Derive target-form facts from trusted context when direct facts are insufficient."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.models import KgcFact
from src.pipeline.kgc_matching import (
    EXCLUDED_PRESIDENT_PROXY_RELATIONS,
    INTENT_CANONICAL_RELATIONS,
    normalize,
    normalize_relation,
)
from src.pipeline.question_target import QuestionTarget
from src.pipeline.target_frame_normalizer import (
    build_target_evaluation_facts,
    relation_in_target_family,
)

PRESIDENT_TITLE_PATTERN = re.compile(
    r"\bPresident\s+((?:John\s+F\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    re.IGNORECASE,
)

HISTORICAL_BACKGROUND_MARKERS = (
    "goal set by",
    "national goal",
    "may 1961",
    "before the end of the decade",
    "challenged the united states",
    "fulfilled a national goal",
    "space race",
    "cold war rivalry",
)

MISSION_EVENT_MARKERS = (
    "lunar surface",
    "moonwalk",
    "walk on the moon",
    "telephone",
    "speaking by",
    "planted",
    "collecting",
    "splashdown",
    "lunar orbit",
    "sea of tranquility",
    "descended to the surface",
    "on the lunar surface",
    "on the moon",
)


@dataclass
class DerivedFactCandidate:
    fact: KgcFact
    derivation_type: str
    evidence_spans: list[str] = field(default_factory=list)
    explanation: str = ""
    accepted: bool = False
    rejection_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "fact": {
                "subject": self.fact.subject,
                "relation": self.fact.relation,
                "object": self.fact.object,
                "evidence": self.fact.evidence,
            },
            "derivation_type": self.derivation_type,
            "evidence_spans": self.evidence_spans,
            "explanation": self.explanation,
            "accepted": self.accepted,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class TargetDerivationTrace:
    attempted: bool = False
    derivation_type: str | None = None
    retry_count: int = 0
    accepted: list[DerivedFactCandidate] = field(default_factory=list)
    rejected: list[DerivedFactCandidate] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "attempted": self.attempted,
            "derivation_type": self.derivation_type,
            "retry_count": self.retry_count,
            "accepted": [item.to_dict() for item in self.accepted],
            "rejected": [item.to_dict() for item in self.rejected],
        }


def has_on_target_evaluation_facts(
    kgc_facts: list[KgcFact],
    target: QuestionTarget,
    question: str,
) -> bool:
    if not target.expected_relations:
        return bool(kgc_facts)
    frames = build_target_evaluation_facts(
        kgc_facts,
        intent=target.intent,
        primary_subject=target.primary_subject,
        canonical_relation=target.canonical_relation,
        question=question,
    )
    return len(frames) > 0


def _sentence_spans(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def _span_in_context(span: str, context: str) -> bool:
    return span.strip() in context


def _normalize_president_name(raw: str) -> str:
    name = raw.strip()
    name = re.sub(r"^President\s+", "", name, flags=re.IGNORECASE).strip()
    return name


def _is_historical_background(sentence: str) -> bool:
    lowered = normalize(sentence)
    return any(marker in lowered for marker in HISTORICAL_BACKGROUND_MARKERS)


def _is_mission_event_context(sentence: str) -> bool:
    lowered = normalize(sentence)
    return any(marker in lowered for marker in MISSION_EVENT_MARKERS)


def _derive_president_from_context(
    *,
    trusted_context: str,
    target: QuestionTarget,
    question: str,
) -> list[DerivedFactCandidate]:
    subject = target.primary_subject
    if not subject:
        return []

    canonical = target.canonical_relation or INTENT_CANONICAL_RELATIONS["president_at_time"]
    candidates: list[DerivedFactCandidate] = []
    seen_names: set[str] = set()

    for sentence in _sentence_spans(trusted_context):
        if _is_historical_background(sentence) and not _is_mission_event_context(sentence):
            continue
        if not _is_mission_event_context(sentence) and not any(
            marker in normalize(sentence) for marker in ("telephone", "speaking", "president")
        ):
            continue

        for match in PRESIDENT_TITLE_PATTERN.finditer(sentence):
            president_name = _normalize_president_name(match.group(1))
            if not president_name:
                continue
            if not _span_in_context(sentence, trusted_context):
                candidates.append(
                    DerivedFactCandidate(
                        fact=KgcFact(subject, canonical, president_name, evidence=sentence),
                        derivation_type="event_scoped_explicit_role",
                        evidence_spans=[sentence],
                        explanation="President title in mission-event context sentence.",
                        accepted=False,
                        rejection_reason="Evidence span not grounded in trusted context.",
                    )
                )
                continue
            seen_names.add(normalize(president_name))
            candidates.append(
                DerivedFactCandidate(
                    fact=KgcFact(
                        subject=subject,
                        relation=canonical,
                        object=president_name,
                        evidence=sentence,
                    ),
                    derivation_type="event_scoped_explicit_role",
                    evidence_spans=[sentence],
                    explanation=(
                        "Explicit President title in mission-event trusted-context sentence."
                    ),
                    accepted=True,
                )
            )

    if len({normalize(c.fact.object) for c in candidates if c.accepted}) > 1:
        for candidate in candidates:
            if candidate.accepted:
                candidate.accepted = False
                candidate.rejection_reason = "Multiple ambiguous president candidates in context."
        return candidates

    return [c for c in candidates if c.accepted]


def _derive_president_from_proxy_facts(
    *,
    trusted_context: str,
    target: QuestionTarget,
    kgc_facts: list[KgcFact],
) -> list[DerivedFactCandidate]:
    subject = target.primary_subject
    if not subject:
        return []

    canonical = target.canonical_relation or INTENT_CANONICAL_RELATIONS["president_at_time"]
    accepted: list[DerivedFactCandidate] = []

    for fact in kgc_facts:
        rel = normalize_relation(fact.relation)
        if rel not in EXCLUDED_PRESIDENT_PROXY_RELATIONS:
            continue
        if not fact.object.lower().startswith("president "):
            continue
        evidence = fact.evidence or f"{fact.subject} -- {fact.relation} --> {fact.object}"
        if _is_historical_background(evidence) and not _is_mission_event_context(evidence):
            continue
        if not _is_mission_event_context(evidence) and rel == "fulfilled_goal_set_by":
            continue
        if not _span_in_context(evidence, trusted_context):
            continue

        president_name = _normalize_president_name(fact.object)
        if not president_name:
            continue

        accepted.append(
            DerivedFactCandidate(
                fact=KgcFact(
                    subject=subject,
                    relation=canonical,
                    object=president_name,
                    evidence=evidence,
                ),
                derivation_type="proxy_fact_event_scoped_role",
                evidence_spans=[evidence],
                explanation=(
                    f"Derived target-form president from direct {fact.relation} trusted fact."
                ),
                accepted=True,
            )
        )

    if len({normalize(c.fact.object) for c in accepted}) > 1:
        for candidate in accepted:
            candidate.accepted = False
            candidate.rejection_reason = "Multiple ambiguous president proxy derivations."
        return accepted

    return [c for c in accepted if c.accepted]


class TargetFactDeriver:
    """Propose validated target-form facts from trusted context only."""

    def derive(
        self,
        *,
        question: str,
        trusted_context: str,
        target: QuestionTarget,
        kgc_facts: list[KgcFact],
    ) -> tuple[list[KgcFact], TargetDerivationTrace]:
        trace = TargetDerivationTrace()

        if not target.expected_relations or target.intent == "compound":
            return [], trace

        if has_on_target_evaluation_facts(kgc_facts, target, question):
            return [], trace

        trace.attempted = True
        candidates: list[DerivedFactCandidate] = []

        if target.intent == "president_at_time":
            trace.derivation_type = "president_at_time"
            candidates.extend(
                _derive_president_from_context(
                    trusted_context=trusted_context,
                    target=target,
                    question=question,
                )
            )
            if not any(c.accepted for c in candidates):
                candidates.extend(
                    _derive_president_from_proxy_facts(
                        trusted_context=trusted_context,
                        target=target,
                        kgc_facts=kgc_facts,
                    )
                )
        else:
            # Reusable deterministic bootstrap for known target families when
            # focused LLM extraction did not yield on-target evaluation facts.
            from src.pipeline.trusted_context_bootstrap import bootstrap_facts_from_context

            trace.derivation_type = "trusted_context_bootstrap"
            for fact in bootstrap_facts_from_context(
                trusted_context=trusted_context,
                target=target,
            ):
                candidates.append(
                    DerivedFactCandidate(
                        fact=fact,
                        derivation_type="trusted_context_bootstrap",
                        evidence_spans=[fact.evidence or ""],
                        explanation=(
                            "Deterministic target-form fact bootstrapped from "
                            "trusted context text."
                        ),
                        accepted=True,
                    )
                )

        accepted_facts: list[KgcFact] = []
        for candidate in candidates:
            if not candidate.accepted:
                trace.rejected.append(candidate)
                continue
            if not relation_in_target_family(candidate.fact.relation, target.intent):
                candidate.accepted = False
                candidate.rejection_reason = "Derived relation outside target family."
                trace.rejected.append(candidate)
                continue
            if candidate.evidence_spans and not all(
                _span_in_context(span, trusted_context)
                for span in candidate.evidence_spans
                if span
            ):
                candidate.accepted = False
                candidate.rejection_reason = "Evidence span not grounded in trusted context."
                trace.rejected.append(candidate)
                continue
            trace.accepted.append(candidate)
            accepted_facts.append(candidate.fact)

        return accepted_facts, trace
