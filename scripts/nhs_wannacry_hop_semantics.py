"""Shared NHS WannaCry hop-semantics helpers.

The NHS benchmark distinguishes graph depth from question-required reasoning
depth. These helpers keep anchor detection, shortcut detection, graph distance,
discourse-marker checks, and locality audits consistent between the dataset
builder and the general benchmark validator.
"""

from __future__ import annotations

from collections import defaultdict, deque
import re
from typing import Any


ROOT_ENTITY = "WannaCry attack on the NHS"

ENTITY_ALIASES: dict[str, list[str]] = {
    ROOT_ENTITY: [
        "WannaCry attack on the NHS",
        "May 2017 NHS WannaCry attack",
        "May 2017 NHS WannaCry",
        "NHS WannaCry incident",
        "May 2017 NHS cyber attack",
        "WannaCry attack affecting the NHS",
        "WannaCry incident affecting the NHS",
        "WannaCry attack on NHS England",
        "WannaCry attack",
    ],
    "CareCERT Assure assessments": [
        "CareCERT Assure assessments",
        "CareCERT Assure",
        "on-site CareCERT assessments",
    ],
    "NHS Digital": ["NHS Digital"],
    "Department of Health": ["Department of Health", "the Department of Health"],
    "MS17-010/EternalBlue SMBv1 exploit": [
        "MS17-010/EternalBlue SMBv1 exploit",
        "MS17-010 EternalBlue exploit",
        "EternalBlue",
        "MS17-010",
    ],
    "Microsoft Security Bulletin MS17-010": [
        "Microsoft Security Bulletin MS17-010",
        "MS17-010 bulletin",
        "MS17-010 security bulletin",
    ],
    "Microsoft SMBv1 vulnerability": [
        "Microsoft SMBv1 vulnerability",
        "SMBv1 vulnerability",
    ],
    "Microsoft Windows SMBv1 server": [
        "Microsoft Windows SMBv1 server",
        "Windows SMBv1 server",
        "SMBv1 server",
    ],
    "Supported Microsoft Windows": [
        "Supported Microsoft Windows",
        "supported Microsoft Windows",
    ],
    "Majority unpatched Windows 7 devices": [
        "Majority unpatched Windows 7 devices",
        "unpatched Windows 7 devices",
    ],
    "MS17-010 patch for supported Windows 7": [
        "MS17-010 patch for supported Windows 7",
        "March 2017 Microsoft patch",
    ],
    "CareCERT alert on 17 March 2017": [
        "CareCERT alert on 17 March 2017",
        "17 March CareCERT alert",
    ],
    "CareCERT alert on 28 April 2017": [
        "CareCERT alert on 28 April 2017",
        "28 April CareCERT alert",
    ],
    "WannaCry ransomware": ["WannaCry ransomware"],
    "WannaCry dropper": ["WannaCry dropper"],
    "Windows 7": ["Windows 7"],
    "Barts Health NHS Trust": ["Barts Health NHS Trust", "Barts Health"],
    "Royal London Hospital": ["Royal London Hospital"],
    "Emergency ambulance services": ["Emergency ambulance services"],
    "NHS England stand-down decision": ["NHS England stand-down decision"],
}

AMBIGUOUS_DISCOURSE_TERMS = (
    "that",
    "those",
    "this",
    "same",
    "former",
    "latter",
    "earlier",
    "later",
    "previous",
)

AMBIGUOUS_DISCOURSE_DENYLIST = (
    "those inspections",
    "that failed",
    "the same technical",
    "that hospital",
    "those organisations",
    "those machines",
    "that digital body",
    "that acute-trust",
    "that appointment",
    "those exclusions",
    "those late",
    "the listed",
    "listed trust",
    "listed hospital",
    "listed london",
    "the component",
    "the missing diversion",
    "the same technical sequence",
)


def normalize_entity(value: Any) -> str:
    """Normalize entity labels and prose for case-insensitive matching."""
    return re.sub(r"\s+", " ", str(value).casefold()).strip()


def _alias_pattern(alias: str) -> re.Pattern[str]:
    """Return a punctuation-tolerant whole-phrase regex for an alias."""
    parts = re.findall(r"[a-z0-9]+", alias.casefold())
    if not parts:
        return re.compile(r"(?!x)x")
    separator = r"[\W_]+"
    return re.compile(r"(?<![a-z0-9])" + separator.join(map(re.escape, parts)) + r"(?![a-z0-9])")


def expanded_aliases(
    entities: list[str] | set[str] | tuple[str, ...],
    aliases: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """Return aliases for entities, always including each exact entity label."""
    configured = aliases or ENTITY_ALIASES
    expanded: dict[str, list[str]] = {}
    for entity in sorted(str(item) for item in entities):
        seen: set[str] = set()
        values: list[str] = []
        for alias in [entity, *configured.get(entity, [])]:
            normalized = normalize_entity(alias)
            if normalized and normalized not in seen:
                seen.add(normalized)
                values.append(str(alias))
        expanded[entity] = values
    return expanded


def detect_entities_in_text(
    text: str,
    entities: list[str] | set[str] | tuple[str, ...],
    aliases: dict[str, list[str]] | None = None,
) -> list[str]:
    """Return graph entities whose entity label or alias appears in text."""
    alias_map = expanded_aliases(entities, aliases)
    detected: list[str] = []
    haystack = str(text)
    for entity in sorted(alias_map):
        if any(_alias_pattern(alias).search(haystack.casefold()) for alias in alias_map[entity]):
            detected.append(entity)
    return detected


def matched_aliases_for_entity(
    text: str,
    entity: str,
    aliases: dict[str, list[str]] | None = None,
) -> list[str]:
    """Return aliases for one entity that appear in text."""
    alias_map = expanded_aliases([entity], aliases)
    haystack = str(text).casefold()
    return [
        alias
        for alias in alias_map.get(entity, [])
        if _alias_pattern(alias).search(haystack)
    ]


def detect_ambiguous_discourse(text: str) -> list[str]:
    """Detect discourse markers that can make a question depend on prior text."""
    lowered = str(text).casefold()
    markers: list[str] = []
    for phrase in AMBIGUOUS_DISCOURSE_DENYLIST:
        if re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", lowered):
            markers.append(phrase)
    for term in AMBIGUOUS_DISCOURSE_TERMS:
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lowered):
            markers.append(term)
    return sorted(set(markers))


def select_question_anchors(
    question: str,
    triples: list[tuple[str, str, str]],
    answer: Any,
    hop_count: int,
    graph_entities: list[str] | set[str] | tuple[str, ...],
    aliases: dict[str, list[str]] | None = None,
    *,
    prefer_root: bool = True,
) -> dict[str, Any]:
    """Detect question anchors from wording; never silently fall back to root.

    A valid question anchor is a graph entity that:
    1. is explicitly expressed in the question via label/alias match, and
    2. has shortest directed distance to the answer equal to ``hop_count``.

    When multiple valid anchors exist and ``prefer_root`` is true, the graph
    root is preferred if it qualifies. Otherwise all distance-valid anchors are
    retained. If none qualify, validation/generation must fail.
    """
    detected = detect_entities_in_text(question, graph_entities, aliases)
    distance_valid: list[str] = []
    for entity in detected:
        distance = shortest_directed_distance(triples, [entity], answer)
        if distance == hop_count:
            distance_valid.append(entity)
    if not distance_valid:
        return {
            "question_anchor_entities": [],
            "anchor_detected_from_question": False,
            "anchor_detection_method": "alias_match",
            "matched_aliases": [],
            "detected_entities": detected,
        }
    if prefer_root:
        root_matches = [
            entity
            for entity in distance_valid
            if normalize_entity(entity) == normalize_entity(ROOT_ENTITY)
        ]
        anchors = root_matches or distance_valid
    else:
        anchors = distance_valid
    matched_aliases: list[str] = []
    for anchor in anchors:
        matched_aliases.extend(matched_aliases_for_entity(question, anchor, aliases))
    return {
        "question_anchor_entities": anchors,
        "anchor_detected_from_question": True,
        "anchor_detection_method": "alias_match",
        "matched_aliases": matched_aliases,
        "detected_entities": detected,
    }


def shortest_directed_distance(
    triples: list[tuple[str, str, str]],
    anchors: list[Any],
    answer: Any,
) -> int | None:
    """Return shortest directed edge count from any anchor to the answer."""
    target = normalize_entity(answer)
    if not target:
        return None
    adjacency: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set()
    for subject, _relation, obj in triples:
        subject_key = normalize_entity(subject)
        obj_key = normalize_entity(obj)
        adjacency[subject_key].add(obj_key)
        nodes.add(subject_key)
        nodes.add(obj_key)
    starts = [normalize_entity(anchor) for anchor in anchors if normalize_entity(anchor) in nodes]
    if not starts or target not in nodes:
        return None
    queue: deque[tuple[str, int]] = deque((start, 0) for start in starts)
    seen = set(starts)
    while queue:
        node, distance = queue.popleft()
        if node == target:
            return distance
        for neighbor in sorted(adjacency.get(node, set())):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, distance + 1))
    return None


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", str(text).replace("\n", " "))
        if sentence.strip()
    ]


def _content_tokens(text: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "by",
        "did",
        "during",
        "for",
        "from",
        "had",
        "how",
        "in",
        "into",
        "of",
        "on",
        "or",
        "the",
        "to",
        "was",
        "were",
        "what",
        "when",
        "which",
        "who",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(text).casefold())
        if len(token) > 2 and token not in stopwords
    }


def locality_audit(question: str, answer: str, trusted_context: str) -> dict[str, Any]:
    """Audit whether a single high-overlap context sentence exposes the answer."""
    answer_norm = normalize_entity(answer)
    question_tokens = _content_tokens(question)
    candidates: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(_sentences(trusted_context)):
        if answer_norm and answer_norm in normalize_entity(sentence):
            overlap = len(question_tokens & _content_tokens(sentence))
            candidates.append((overlap, index, sentence))
    if not candidates:
        return {
            "closest_context_sentence": "",
            "answer_present_in_single_sentence": False,
            "locality_warning": False,
            "status": "PASS",
        }
    overlap, _index, closest = max(candidates, key=lambda item: (item[0], -item[1]))
    # Root-only prompts share a few unavoidable domain tokens; higher overlap is
    # a warning that the question may be answerable by local sentence matching.
    locality_warning = overlap >= 5
    return {
        "closest_context_sentence": closest,
        "answer_present_in_single_sentence": True,
        "locality_warning": locality_warning,
        "status": "WARNING" if locality_warning else "PASS",
    }


def shortcut_flags(
    question: str,
    path: list[list[str]] | list[tuple[str, str, str]],
    answer: str,
    aliases: dict[str, list[str]] | None = None,
    *,
    triples: list[tuple[str, str, str]] | None = None,
    question_anchor_entities: list[str] | None = None,
    hop_count: int | None = None,
) -> dict[str, Any]:
    """Return shortcut flags for late entity mentions and answer leakage."""
    if not path:
        return {
            "direct_final_subject_mentioned": False,
            "expected_answer_mentioned": False,
            "late_chain_entity_mentioned": False,
            "one_hop_parent_mentioned": False,
            "shortcut_entities": [],
            "mentioned_entities": [],
        }

    edge_path = [(str(edge[0]), str(edge[1]), str(edge[2])) for edge in path]
    entities = {node for subject, _relation, obj in edge_path for node in (subject, obj)}
    detected = detect_entities_in_text(question, entities, aliases)
    anchor_set = {normalize_entity(anchor) for anchor in (question_anchor_entities or [])}
    final_subject = edge_path[-1][0]
    final_subject_mentioned = final_subject in detected
    answer_mentioned = answer in detected or bool(matched_aliases_for_entity(question, answer, aliases))
    one_hop_parent_mentioned = final_subject_mentioned
    shortcut_entities: list[str] = []

    if triples is not None and hop_count is not None:
        for entity in detected:
            if normalize_entity(entity) in anchor_set:
                continue
            distance = shortest_directed_distance(triples, [entity], answer)
            if distance is not None and distance < hop_count:
                shortcut_entities.append(entity)
    else:
        for entity in detected:
            if normalize_entity(entity) not in anchor_set and entity != answer:
                shortcut_entities.append(entity)

    late_chain_entity_mentioned = any(entity != final_subject for entity in shortcut_entities)
    return {
        "direct_final_subject_mentioned": final_subject_mentioned,
        "expected_answer_mentioned": answer_mentioned,
        "late_chain_entity_mentioned": late_chain_entity_mentioned,
        "one_hop_parent_mentioned": one_hop_parent_mentioned,
        "shortcut_entities": sorted(set(shortcut_entities)),
        "mentioned_entities": detected,
    }
