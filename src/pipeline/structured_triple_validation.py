"""Validate raw LLM triple items into subject/relation/object strings.

This is the boundary between provider output and structured KgcFact/Triple values.
It must not invent an object when the raw item is malformed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ValidationStatus = Literal["valid", "normalized", "rejected"]


@dataclass
class StructuredTripleAnomaly:
    """Record of a malformed or unsafe structured-triple item."""

    reason: str
    raw_value: Any
    subject: str | None = None
    relation: str | None = None
    object: str | None = None
    source_stage: str = ""
    normalization_applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidatedTriple:
    subject: str
    relation: str
    object: str
    evidence: str | None = None
    source_sentence: str | None = None
    validation_status: ValidationStatus = "valid"
    normalization_applied: list[str] = field(default_factory=list)
    raw_value: Any = None
    provenance: str = ""
    source_stage: str = ""

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "raw_value": self.raw_value,
            "subject": self.subject,
            "relation": self.relation,
            "object": self.object,
            "provenance": self.provenance,
            "validation_status": self.validation_status,
            "normalization_applied": list(self.normalization_applied),
            "source_stage": self.source_stage,
            "evidence": self.evidence,
            "source_sentence": self.source_sentence,
        }


def _as_nonempty_string(value: Any, *, field_name: str) -> tuple[str | None, str | None]:
    """Return (text, error_reason). Reject null, blank, and non-scalar containers."""
    if value is None:
        return None, f"{field_name}_null"
    if isinstance(value, bool):
        return None, f"{field_name}_unsupported_bool"
    if isinstance(value, (int, float)):
        text = str(value).strip()
        if not text:
            return None, f"{field_name}_empty"
        return text, None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None, f"{field_name}_empty"
        # Guard against prior str(None)/str(list) contamination being re-accepted.
        if text == "None":
            return None, f"{field_name}_null_string"
        if (text.startswith("[") and text.endswith("]")) or (
            text.startswith("{") and text.endswith("}")
        ):
            # Only reject when it looks like a Python/JSON container dump.
            if "'" in text or '"' in text or ":" in text or "," in text:
                return None, f"{field_name}_container_repr"
        return text, None
    if isinstance(value, (list, tuple, dict)):
        return None, f"{field_name}_unsupported_{type(value).__name__}"
    return None, f"{field_name}_unsupported_type"


def _dict_field(item: dict[str, Any], *keys: str) -> tuple[Any, str | None]:
    for key in keys:
        if key in item:
            return item[key], key
    return None, None


def coerce_raw_triple_item(
    item: Any,
    *,
    kind: Literal["fact", "claim"] = "fact",
    source_stage: str = "",
    provenance: str = "",
) -> tuple[ValidatedTriple | None, StructuredTripleAnomaly | None]:
    """Validate one raw triple item.

    Safe normalizations (recorded when applied):
    - list/tuple positional [subject, relation, object, optional evidence/source]
    - dictionary aliases predicate→relation, obj/object_value→object
    - strip whitespace

    Unsafe cases are rejected with an anomaly (no invented object).
    """
    normalizations: list[str] = []
    raw_value = item

    subject_raw: Any = None
    relation_raw: Any = None
    object_raw: Any = None
    evidence_raw: Any = None
    source_sentence_raw: Any = None
    object_key_missing = False

    if isinstance(item, (list, tuple)):
        if len(item) < 3:
            return None, StructuredTripleAnomaly(
                reason="malformed_array_too_short",
                raw_value=raw_value,
                source_stage=source_stage,
            )
        if len(item) > 4:
            return None, StructuredTripleAnomaly(
                reason="malformed_array_extra_positional_fields",
                raw_value=raw_value,
                source_stage=source_stage,
            )
        subject_raw, relation_raw, object_raw = item[0], item[1], item[2]
        if len(item) == 4:
            if kind == "fact":
                evidence_raw = item[3]
            else:
                source_sentence_raw = item[3]
        normalizations.append("positional_array")
    elif isinstance(item, dict):
        subject_raw, subject_key = _dict_field(item, "subject", "subj", "s")
        if subject_key and subject_key != "subject":
            normalizations.append(f"alias_{subject_key}_to_subject")

        relation_raw, relation_key = _dict_field(
            item, "relation", "predicate", "pred", "p", "relationship"
        )
        if relation_key and relation_key != "relation":
            normalizations.append(f"alias_{relation_key}_to_relation")

        object_raw, object_key = _dict_field(
            item, "object", "obj", "object_value", "o", "value"
        )
        if object_key and object_key != "object":
            normalizations.append(f"alias_{object_key}_to_object")
        object_key_missing = object_key is None

        if "evidence" in item:
            evidence_raw = item.get("evidence")
        if "source_sentence" in item:
            source_sentence_raw = item.get("source_sentence")

        # Detect swapped-looking positional misuse via unexpected sole keys.
        if subject_key is None and relation_key is None and object_key is None:
            return None, StructuredTripleAnomaly(
                reason="dictionary_missing_triple_keys",
                raw_value=raw_value,
                source_stage=source_stage,
            )
    else:
        return None, StructuredTripleAnomaly(
            reason="unsupported_triple_item_type",
            raw_value=raw_value,
            source_stage=source_stage,
        )

    subject, subject_err = _as_nonempty_string(subject_raw, field_name="subject")
    relation, relation_err = _as_nonempty_string(relation_raw, field_name="relation")
    obj, object_err = _as_nonempty_string(object_raw, field_name="object")

    if subject_err or relation_err or object_err:
        reason = object_err or relation_err or subject_err or "invalid_triple"
        if object_key_missing or (
            isinstance(item, dict) and object_err in {"object_null", "object_empty"}
            and "object" not in item
            and "obj" not in item
            and "object_value" not in item
            and "o" not in item
            and "value" not in item
        ):
            reason = "missing_third_element"
        elif object_err == "object_null":
            reason = "null_object"
        elif object_err == "object_empty":
            reason = "empty_object"
        elif object_err and object_err.startswith("object_unsupported"):
            reason = "object_unsupported_nested_value"
        return None, StructuredTripleAnomaly(
            reason=reason,
            raw_value=raw_value,
            subject=subject,
            relation=relation,
            object=obj,
            source_stage=source_stage,
            normalization_applied=list(normalizations),
        )

    assert subject is not None and relation is not None and obj is not None

    if obj == relation:
        return None, StructuredTripleAnomaly(
            reason="object_copied_from_relation",
            raw_value=raw_value,
            subject=subject,
            relation=relation,
            object=obj,
            source_stage=source_stage,
            normalization_applied=list(normalizations),
        )

    # Detect obvious subject/object swap heuristics only when relation looks like object text.
    if subject == obj and relation.lower() in {subject.lower(), obj.lower()}:
        return None, StructuredTripleAnomaly(
            reason="subject_relation_object_position_swap",
            raw_value=raw_value,
            subject=subject,
            relation=relation,
            object=obj,
            source_stage=source_stage,
            normalization_applied=list(normalizations),
        )

    evidence = None
    if evidence_raw is not None and str(evidence_raw).strip():
        evidence = str(evidence_raw).strip()
    source_sentence = None
    if source_sentence_raw is not None and str(source_sentence_raw).strip():
        source_sentence = str(source_sentence_raw).strip()

    status: ValidationStatus = "normalized" if normalizations else "valid"
    return (
        ValidatedTriple(
            subject=subject,
            relation=relation,
            object=obj,
            evidence=evidence,
            source_sentence=source_sentence,
            validation_status=status,
            normalization_applied=list(normalizations),
            raw_value=raw_value,
            provenance=provenance,
            source_stage=source_stage,
        ),
        None,
    )
