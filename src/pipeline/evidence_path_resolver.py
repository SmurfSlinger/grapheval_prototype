"""Deterministic trusted evidence-path resolution for nested answers.

Given only the question, current answer, terminal answer claim, question target,
and trusted FACTS for the current execution, build an ordered path from the
question root to the terminal claim. CLAIMS are never used as evidence. Paths
are validated entirely in Python against the trusted FACT list.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field

from src.models import KgcFact, Triple
from src.pipeline.kgc_matching import normalize, normalize_relation
from src.pipeline.question_target import QuestionTarget, relation_matches_target
from src.pipeline.trusted_context_bootstrap import infer_primary_subject_from_context

_MAX_DEPTH = 10

# Proper-name spans mentioned in the question ("Mission Alpha", "Apollo 11").
# Reject sentence-initial wh-words so "What CKD stage ..." is not a root.
_QUESTION_NAME_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9]+(?:\s+(?:[A-Z][A-Za-z0-9]+|\d+))+)\b"
)
_QUESTION_NAME_LEAD_STOP = frozenset(
    {
        "what",
        "which",
        "where",
        "when",
        "who",
        "whom",
        "whose",
        "how",
        "the",
        "a",
        "an",
        "in",
        "on",
        "at",
        "from",
        "of",
        "to",
    }
)


@dataclass(frozen=True)
class PathEdge:
    subject: str
    relation: str
    object: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class EvidencePathResult:
    start_entity: str | None
    terminal_claim: dict[str, str] | None
    evidence_path: list[PathEdge] = field(default_factory=list)
    path_length: int = 0
    complete: bool = False
    ambiguity: str | None = None
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "start_entity": self.start_entity,
            "terminal_claim": self.terminal_claim,
            "evidence_path": [edge.to_dict() for edge in self.evidence_path],
            "path_length": self.path_length,
            "complete": self.complete,
            "ambiguity": self.ambiguity,
            "failure_reason": self.failure_reason,
        }


def resolve_evidence_path(
    *,
    question: str,
    current_answer: str,
    answer_claim: Triple | None,
    question_target: QuestionTarget | None,
    trusted_facts: list[KgcFact],
) -> EvidencePathResult:
    """Search trusted FACTS for a path from the question root to the terminal claim."""
    if answer_claim is None:
        return EvidencePathResult(
            start_entity=None,
            terminal_claim=None,
            failure_reason="missing_terminal_claim",
        )

    terminal = {
        "subject": answer_claim.subject,
        "relation": answer_claim.relation,
        "object": answer_claim.object,
    }
    terminal_edge = PathEdge(
        subject=answer_claim.subject,
        relation=answer_claim.relation,
        object=answer_claim.object,
    )

    if not _edge_in_facts(terminal_edge, trusted_facts):
        return EvidencePathResult(
            start_entity=None,
            terminal_claim=terminal,
            failure_reason="terminal_claim_not_a_trusted_fact",
        )

    start = identify_question_root(
        question,
        trusted_facts,
        question_target=question_target,
        terminal_claim=answer_claim,
    )
    if not start:
        return EvidencePathResult(
            start_entity=None,
            terminal_claim=terminal,
            failure_reason="missing_start_entity",
        )

    # Depth-1: the root is the terminal claim subject.
    if _names_match(start, answer_claim.subject):
        # When the terminal claim answers the typed question target, prefer a
        # unique source→subject prefix so multi-hop on-target paths are not
        # collapsed to a depth-1 self-root.
        if _is_target_claim(answer_claim, question_target):
            source_paths, ambiguity = _find_source_paths_to(
                end_entity=answer_claim.subject,
                trusted_facts=trusted_facts,
                max_depth=_MAX_DEPTH - 1,
            )
            if ambiguity:
                return EvidencePathResult(
                    start_entity=start,
                    terminal_claim=terminal,
                    ambiguity=ambiguity,
                    failure_reason="ambiguous_branch",
                )
            if source_paths:
                full_path = list(source_paths[0]) + [terminal_edge]
                source_start = full_path[0].subject
                if _has_cycle(full_path):
                    return EvidencePathResult(
                        start_entity=source_start,
                        terminal_claim=terminal,
                        evidence_path=full_path,
                        path_length=len(full_path),
                        failure_reason="cycle_detected",
                    )
                if len(full_path) <= _MAX_DEPTH:
                    return EvidencePathResult(
                        start_entity=source_start,
                        terminal_claim=terminal,
                        evidence_path=full_path,
                        path_length=len(full_path),
                        complete=True,
                    )
                return EvidencePathResult(
                    start_entity=source_start,
                    terminal_claim=terminal,
                    evidence_path=full_path,
                    path_length=len(full_path),
                    failure_reason="path_exceeds_max_depth",
                )
        return EvidencePathResult(
            start_entity=start,
            terminal_claim=terminal,
            evidence_path=[terminal_edge],
            path_length=1,
            complete=True,
        )

    prefix_paths, ambiguity = _find_paths(
        start_entity=start,
        end_entity=answer_claim.subject,
        trusted_facts=trusted_facts,
        max_depth=_MAX_DEPTH - 1,
    )
    if ambiguity:
        return EvidencePathResult(
            start_entity=start,
            terminal_claim=terminal,
            ambiguity=ambiguity,
            failure_reason="ambiguous_branch",
        )
    if not prefix_paths:
        return EvidencePathResult(
            start_entity=start,
            terminal_claim=terminal,
            failure_reason="missing_intermediate_edge",
        )

    # Prefer the unique shortest path; append the terminal claim.
    prefix = prefix_paths[0]
    full_path = list(prefix) + [terminal_edge]
    if _has_cycle(full_path):
        return EvidencePathResult(
            start_entity=start,
            terminal_claim=terminal,
            evidence_path=full_path,
            path_length=len(full_path),
            failure_reason="cycle_detected",
        )
    if len(full_path) > _MAX_DEPTH:
        return EvidencePathResult(
            start_entity=start,
            terminal_claim=terminal,
            evidence_path=full_path,
            path_length=len(full_path),
            failure_reason="path_exceeds_max_depth",
        )
    return EvidencePathResult(
        start_entity=start,
        terminal_claim=terminal,
        evidence_path=full_path,
        path_length=len(full_path),
        complete=True,
    )


def identify_question_root(
    question: str,
    trusted_facts: list[KgcFact],
    *,
    question_target: QuestionTarget | None = None,
    terminal_claim: Triple | None = None,
) -> str | None:
    """Pick the question's root entity from mentions that appear in trusted FACTS.

    Named entities mentioned in the question but absent from this execution's
    FACTS still count as the root — the path is then incomplete rather than a
    spurious depth-1 resolution from an intermediate node.
    """
    from_context = infer_primary_subject_from_context("", question)
    if from_context:
        return from_context

    entities = _entities_from_facts(trusted_facts)
    q_norm = normalize(question)
    mentioned = [
        entity
        for entity in entities
        if normalize(entity) in q_norm
    ]
    question_names = _question_named_entities(question)
    terminal_subject = terminal_claim.subject if terminal_claim else None
    terminal_object = terminal_claim.object if terminal_claim else None

    # Question-mentioned names that are not the terminal edge endpoints are
    # preferred roots even when missing from the current execution's FACTS.
    external_roots = [
        name
        for name in question_names
        if not (
            (terminal_subject and _names_match(name, terminal_subject))
            or (terminal_object and _names_match(name, terminal_object))
        )
    ]
    if external_roots and not any(
        any(_names_match(name, entity) for entity in mentioned)
        for name in external_roots
    ):
        # Earliest question mention wins when none are in local FACTS.
        return min(external_roots, key=lambda name: q_norm.find(normalize(name)))

    if not mentioned:
        if external_roots:
            return min(external_roots, key=lambda name: q_norm.find(normalize(name)))
        # Fall back to the most frequent FACT subject that isn't the terminal.
        counts: dict[str, int] = defaultdict(int)
        for fact in trusted_facts:
            counts[fact.subject] += 1
        if terminal_claim:
            counts.pop(terminal_claim.subject, None)
            counts.pop(terminal_claim.object, None)
        if counts:
            return max(counts, key=counts.get)
        return question_target.primary_subject if question_target else None

    # Prefer the mentioned entity that is farthest from the terminal subject
    # (true multi-hop root), breaking ties by earliest mention in the question.
    if terminal_subject:
        distances = {
            entity: _shortest_distance(entity, terminal_subject, trusted_facts)
            for entity in mentioned
        }
        reachable = {
            entity: distance
            for entity, distance in distances.items()
            if distance is not None and not _names_match(entity, terminal_subject)
        }
        if reachable:
            best_distance = max(reachable.values())
            candidates = [
                entity
                for entity, distance in reachable.items()
                if distance == best_distance
            ]
            return min(candidates, key=lambda entity: q_norm.find(normalize(entity)))

    return min(mentioned, key=lambda entity: q_norm.find(normalize(entity)))


def _question_named_entities(question: str) -> list[str]:
    names: list[str] = []
    for match in _QUESTION_NAME_PATTERN.finditer(question):
        name = match.group(1)
        lead = name.split()[0].lower()
        if lead in _QUESTION_NAME_LEAD_STOP:
            continue
        names.append(name)
    return names


def _find_paths(
    *,
    start_entity: str,
    end_entity: str,
    trusted_facts: list[KgcFact],
    max_depth: int,
) -> tuple[list[list[PathEdge]], str | None]:
    """Return shortest simple paths from start to end over trusted FACT edges."""
    adjacency: dict[str, list[PathEdge]] = defaultdict(list)
    for fact in trusted_facts:
        edge = PathEdge(fact.subject, fact.relation, fact.object)
        adjacency[normalize(fact.subject)].append(edge)

    start_key = normalize(start_entity)
    end_key = normalize(end_entity)
    queue: deque[tuple[str, list[PathEdge], set[str]]] = deque(
        [(start_key, [], {start_key})]
    )
    shortest: list[list[PathEdge]] = []
    shortest_len: int | None = None
    sibling_branch_hits = 0

    while queue:
        node, path, seen = queue.popleft()
        if shortest_len is not None and len(path) > shortest_len:
            continue
        if node == end_key and path:
            if shortest_len is None:
                shortest_len = len(path)
            if len(path) == shortest_len:
                shortest.append(path)
            continue
        if len(path) >= max_depth:
            continue
        edges = adjacency.get(node, [])
        if len(edges) > 1 and path:
            # Multiple outgoing edges from an intermediate node: sibling branch.
            sibling_branch_hits += 1
        for edge in edges:
            next_key = normalize(edge.object)
            if next_key in seen:
                continue
            queue.append((next_key, path + [edge], seen | {next_key}))

    if not shortest:
        return [], None
    if len(shortest) > 1:
        # Distinct intermediates at equal length ⇒ ambiguous sibling branches.
        signatures = {
            tuple(
                (normalize(edge.subject), normalize_relation(edge.relation), normalize(edge.object))
                for edge in path
            )
            for path in shortest
        }
        if len(signatures) > 1:
            return [], "sibling_branch_ambiguity"
    return [shortest[0]], None


def _find_source_paths_to(
    *,
    end_entity: str,
    trusted_facts: list[KgcFact],
    max_depth: int,
) -> tuple[list[list[PathEdge]], str | None]:
    """Return a unique shortest path from a directed graph source to end_entity."""
    end_key = normalize(end_entity)
    incoming = {normalize(fact.object) for fact in trusted_facts}
    sources: list[str] = []
    seen_sources: set[str] = set()
    for fact in trusted_facts:
        key = normalize(fact.subject)
        if not key or key == end_key or key in incoming or key in seen_sources:
            continue
        sources.append(fact.subject)
        seen_sources.add(key)

    paths: list[list[PathEdge]] = []
    for source in sources:
        source_paths, ambiguity = _find_paths(
            start_entity=source,
            end_entity=end_entity,
            trusted_facts=trusted_facts,
            max_depth=max_depth,
        )
        if ambiguity:
            return [], ambiguity
        paths.extend(source_paths)

    if not paths:
        return [], None

    shortest_len = min(len(path) for path in paths)
    shortest = [path for path in paths if len(path) == shortest_len]
    signatures = {
        tuple(
            (normalize(edge.subject), normalize_relation(edge.relation), normalize(edge.object))
            for edge in path
        )
        for path in shortest
    }
    if len(signatures) > 1:
        return [], "sibling_branch_ambiguity"
    return [shortest[0]], None


def _shortest_distance(
    start: str,
    end: str,
    trusted_facts: list[KgcFact],
) -> int | None:
    if _names_match(start, end):
        return 0
    adjacency: dict[str, list[str]] = defaultdict(list)
    for fact in trusted_facts:
        adjacency[normalize(fact.subject)].append(normalize(fact.object))
    start_key = normalize(start)
    end_key = normalize(end)
    queue: deque[tuple[str, int]] = deque([(start_key, 0)])
    seen = {start_key}
    while queue:
        node, distance = queue.popleft()
        for nxt in adjacency.get(node, []):
            if nxt in seen:
                continue
            if nxt == end_key:
                return distance + 1
            if distance + 1 >= _MAX_DEPTH:
                continue
            seen.add(nxt)
            queue.append((nxt, distance + 1))
    return None


def _edge_in_facts(edge: PathEdge, trusted_facts: list[KgcFact]) -> bool:
    return any(
        _names_match(fact.subject, edge.subject)
        and normalize_relation(fact.relation) == normalize_relation(edge.relation)
        and _names_match(fact.object, edge.object)
        for fact in trusted_facts
    )


def _entities_from_facts(trusted_facts: list[KgcFact]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for fact in trusted_facts:
        for name in (fact.subject, fact.object):
            key = normalize(name)
            if not key or key in seen:
                continue
            seen.add(key)
            ordered.append(name)
    return ordered


def _is_target_claim(
    claim: Triple,
    question_target: QuestionTarget | None,
) -> bool:
    return bool(
        question_target
        and question_target.expected_relations
        and relation_matches_target(claim.relation, question_target)
    )


def _has_cycle(path: list[PathEdge]) -> bool:
    seen = {normalize(path[0].subject)} if path else set()
    for edge in path:
        obj = normalize(edge.object)
        if obj in seen:
            return True
        seen.add(obj)
    return False


def _names_match(left: str, right: str) -> bool:
    return normalize(left) == normalize(right)
