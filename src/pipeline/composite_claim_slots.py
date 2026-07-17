"""Reusable composite claim-slot extraction for multi-attribute atomic answers.

Deterministic parsers only — no case-specific values hard-coded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.models import Triple
from src.pipeline.kgc_matching import normalize


@dataclass(frozen=True)
class ClaimSlot:
    """One attribute slot within a composite question intent."""

    slot_intent: str
    canonical_relation: str
    extractor_name: str


# Composite question intents → ordered claim slots.
COMPOSITE_CLAIM_SLOTS: dict[str, tuple[ClaimSlot, ...]] = {
    "kidney_status": (
        ClaimSlot("disease_stage", "has_ckd_stage", "ckd_stage"),
        ClaimSlot("renal_measurement", "has_egfr", "egfr"),
    ),
    "discontinued_medication_with_reason": (
        ClaimSlot("medication_discontinued", "discontinued_medication", "stopped_med"),
        ClaimSlot("discontinuation_reason", "discontinued_because", "stop_reason"),
    ),
    "active_medication_with_dose": (
        ClaimSlot("active_medication", "active_medication", "active_med"),
        ClaimSlot("medication_dose", "daily_dose", "dose"),
    ),
    "allergy_with_reaction": (
        ClaimSlot("allergy", "allergic_to", "allergen"),
        ClaimSlot("allergic_reaction", "causes_reaction", "reaction"),
    ),
}


def is_composite_intent(intent: str) -> bool:
    return intent in COMPOSITE_CLAIM_SLOTS


def slot_intents_for_composite(intent: str) -> tuple[str, ...]:
    slots = COMPOSITE_CLAIM_SLOTS.get(intent, ())
    return tuple(slot.slot_intent for slot in slots)


def extract_ckd_stage(text: str) -> str | None:
    match = re.search(
        r"\b(?:CKD\s+)?stage\s*([0-9][a-z]?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return f"stage {match.group(1).lower()}"
    match = re.search(r"\bstage\s*([0-9][a-z]?)\b", text, flags=re.IGNORECASE)
    if match:
        return f"stage {match.group(1).lower()}"
    return None


def extract_egfr(text: str) -> str | None:
    match = re.search(
        r"\beGFR\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(mL/?min(?:/1\.73\s*m[²2])?)?",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        unit = match.group(2) or "mL/min/1.73 m²"
        unit = unit.replace("m2", "m²")
        return f"{match.group(1)} {unit}".strip()
    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*mL/?min(?:/1\.73\s*m[²2])?",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(0).replace("m2", "m²")
    return None


def extract_a1c(text: str) -> str | None:
    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*%",
        text,
    )
    if match:
        return f"{match.group(1)}%"
    match = re.search(
        r"(?:A1C|HbA1c|hemoglobin A1C)\s*(?:is\s*|of\s*|:\s*)?(\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return f"{match.group(1)}%"
    return None


def extract_dose(text: str) -> str | None:
    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*mg(?:\s*daily)?\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        phrase = match.group(0).strip()
        if "daily" not in phrase.lower() and re.search(r"\bdaily\b", text, re.I):
            return f"{phrase} daily"
        return phrase
    return None


def extract_stopped_medication(text: str) -> str | None:
    match = re.search(
        r"\b([A-Za-z][A-Za-z0-9\-]*)\s+was\s+discontinued\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)
    match = re.search(
        r"^\s*([A-Za-z][A-Za-z0-9\-]*)\s+(?:because|due to|after|for)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)
    match = re.search(
        r"\b(?:stopped|discontinued|medication stopped)\s*:?\s*([A-Za-z][A-Za-z0-9\-]*)",
        text,
        flags=re.IGNORECASE,
    )
    if match and match.group(1).lower() not in {
        "after",
        "because",
        "due",
        "for",
        "the",
        "a",
        "an",
    }:
        return match.group(1)
    # Single medication token before reason clause
    parts = re.split(r"\s+because\s+|\s+due to\s+", text, maxsplit=1, flags=re.I)
    if parts:
        token = parts[0].strip().rstrip(".")
        if token and " " not in token:
            return token
        # "metformin was discontinued..."
        match = re.search(
            r"\b([A-Za-z][A-Za-z0-9\-]*)\s+was\s+(?:discontinued|stopped)\b",
            token,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1)
        match = re.search(r"\b([A-Za-z][A-Za-z0-9\-]*)\b", token)
        if match and match.group(1).lower() not in {"the", "a", "an", "medication"}:
            return match.group(1)
    return None


def extract_stop_reason(text: str) -> str | None:
    match = re.search(
        r"\b(?:because(?: of)?|due to)\s+(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().rstrip(".")
    match = re.search(
        r"\bafter(?:\s+repeated trials)?(?:\s+caused)?\s+(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        reason = match.group(1).strip().rstrip(".")
        reason = re.sub(
            r"^(?:repeated trials caused|causing|they caused)\s+",
            "",
            reason,
            flags=re.IGNORECASE,
        )
        return reason or None
    return None


_MED_STOPWORDS = frozenset(
    {
        "of",
        "at",
        "a",
        "an",
        "the",
        "dose",
        "daily",
        "current",
        "currently",
        "active",
        "tolerated",
        "medication",
        "is",
        "was",
        "and",
        "with",
        "for",
        "to",
        "in",
        "on",
        "by",
        "after",
        "because",
        "due",
    }
)


def extract_active_medication(text: str) -> str | None:
    # "Empagliflozin 10 mg daily" or "... Empagliflozin ... 10 mg"
    for match in re.finditer(
        r"\b([A-Za-z][A-Za-z0-9\-]*)\s+\d+(?:\.\d+)?\s*mg\b",
        text,
        flags=re.IGNORECASE,
    ):
        token = match.group(1)
        if token.lower() not in _MED_STOPWORDS:
            return token
    match = re.search(
        r"\b([A-Za-z][A-Za-z0-9\-]*)\b(?=\s+is\s+currently\b|\s+remains\s+active\b|\s+is\s+active\b)",
        text,
        flags=re.IGNORECASE,
    )
    if match and match.group(1).lower() not in _MED_STOPWORDS:
        return match.group(1)
    # Prefer leading medication name before dose / end
    match = re.search(
        r"^\s*([A-Za-z][A-Za-z0-9\-]*)\b(?:\s+\d|\s*$)",
        text.strip(),
    )
    if match and match.group(1).lower() not in _MED_STOPWORDS:
        return match.group(1)
    return None


def extract_allergen(text: str) -> str | None:
    match = re.search(
        r"^\s*([A-Za-z][A-Za-z0-9\-]*)\s+(?:causing|cause[sd]?|with|causes)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)
    match = re.search(
        r"\ballergic to\s+([A-Za-z][A-Za-z0-9\-]*)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)
    match = re.search(
        r"\b([A-Za-z][A-Za-z0-9\-]*)\s+causes?\s+",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)
    parts = re.split(r"\s+causing\s+", text, maxsplit=1, flags=re.I)
    if parts:
        token = parts[0].strip()
        if token:
            return token.split()[0]
    return None


def extract_reaction(text: str) -> str | None:
    match = re.search(
        r"\b(?:causing|causes|caused)\s+(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().rstrip(".")
    return None


_EXTRACTORS = {
    "ckd_stage": extract_ckd_stage,
    "egfr": extract_egfr,
    "a1c": extract_a1c,
    "dose": extract_dose,
    "stopped_med": extract_stopped_medication,
    "stop_reason": extract_stop_reason,
    "active_med": extract_active_medication,
    "allergen": extract_allergen,
    "reaction": extract_reaction,
}


def extract_slot_value(answer: str, extractor_name: str) -> str | None:
    fn = _EXTRACTORS.get(extractor_name)
    if not fn:
        return None
    return fn(answer)


def build_composite_claims(
    *,
    answer: str,
    subject: str,
    intent: str,
) -> list[Triple]:
    slots = COMPOSITE_CLAIM_SLOTS.get(intent)
    if not slots:
        return []
    claims: list[Triple] = []
    for slot in slots:
        value = extract_slot_value(answer, slot.extractor_name)
        if not value:
            continue
        claims.append(
            Triple(
                subject=subject,
                relation=slot.canonical_relation,
                object=value,
                source_sentence=value,
            )
        )
    return claims


def lab_values_equivalent(left: str, right: str) -> bool:
    """Compare numeric lab-like values ignoring unit formatting."""
    left_nums = re.findall(r"\d+(?:\.\d+)?", left)
    right_nums = re.findall(r"\d+(?:\.\d+)?", right)
    if not left_nums or not right_nums:
        return normalize(left) == normalize(right)
    return left_nums[0] == right_nums[0]


def stages_equivalent(left: str, right: str) -> bool:
    left_m = re.search(r"stage\s*([0-9][a-z]?)", left, re.I)
    right_m = re.search(r"stage\s*([0-9][a-z]?)", right, re.I)
    if left_m and right_m:
        return left_m.group(1).lower() == right_m.group(1).lower()
    return normalize(left) == normalize(right)


def doses_equivalent(left: str, right: str) -> bool:
    left_m = re.search(r"(\d+(?:\.\d+)?)\s*mg", left, re.I)
    right_m = re.search(r"(\d+(?:\.\d+)?)\s*mg", right, re.I)
    if left_m and right_m:
        return left_m.group(1) == right_m.group(1)
    return normalize(left) == normalize(right)


def medication_names_equivalent(left: str, right: str) -> bool:
    return normalize(left) == normalize(right)


def reactions_equivalent(left: str, right: str) -> bool:
    return normalize(left) == normalize(right)
