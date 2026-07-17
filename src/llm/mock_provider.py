"""Deterministic mock LLM for running the pipeline without API keys."""

from __future__ import annotations

import json
import re
from typing import Any

from src.llm.base import LLMProvider


def _extract_answer_from_prompt(prompt: str) -> str:
    """Pull the answer text from extraction or verification prompts."""
    marker = "\nAnswer:\n"
    idx = prompt.rfind(marker)
    if idx != -1:
        rest = prompt[idx + len(marker) :]
        if "\nJSON:" in rest:
            return rest.split("\nJSON:", 1)[0].strip()
        return rest.strip()
    if "Original answer:" in prompt:
        text = prompt.split("Original answer:", 1)[1]
        for stop in ("Feedback", "Revise the answer", "Return only"):
            if stop in text:
                text = text.split(stop, 1)[0]
        return text.strip()
    if "Graph-grounded answer (Answer n):" in prompt:
        text = prompt.split("Graph-grounded answer (Answer n):", 1)[1]
        for stop in ("Backtracking feedback", "Return only"):
            if stop in text:
                text = text.split(stop, 1)[0]
        return text.strip()
    return ""


class MockProvider(LLMProvider):
    """Returns placeholder outputs keyed off answer content in the prompt."""

    QUESTION_SPLITS: dict[str, list[dict[str, Any]]] = {
        "what rocket launched apollo 11": [
            {"id": 1, "question": "What rocket launched Apollo 11?"},
            {
                "id": 2,
                "question": "What engines powered the first stage of Apollo 11's launch vehicle?",
            },
            {"id": 3, "question": "Where did Apollo 11 launch from?"},
            {"id": 4, "question": "What mission goal did Apollo 11 accomplish?"},
        ],
        "when was the apollo 11 mission": [
            {"id": 1, "question": "When was the Apollo 11 mission?"},
            {"id": 2, "question": "Who were the astronauts on the Apollo 11 mission?"},
            {"id": 3, "question": "Where was Apollo 11 launched from?"},
            {"id": 4, "question": "Who was the president at the time of Apollo 11?"},
            {
                "id": 5,
                "question": "How much lunar material did Apollo 11 collect?",
            },
        ],
        "what diabetes diagnosis is documented for patient case d-314": [
            {
                "id": 1,
                "question": "What diabetes diagnosis is documented for Patient Case D-314?",
            },
            {"id": 2, "question": "What is the latest A1C?"},
            {
                "id": 3,
                "question": (
                    "What CKD stage is documented and what is the current eGFR?"
                ),
            },
            {
                "id": 4,
                "question": (
                    "Which diabetes medication was discontinued and why?"
                ),
            },
            {
                "id": 5,
                "question": (
                    "Which diabetes medication is currently active and tolerated, "
                    "and at what dose?"
                ),
            },
            {
                "id": 6,
                "question": (
                    "Which medication was discussed but has not been started?"
                ),
            },
            {
                "id": 7,
                "question": (
                    "What antibiotic allergy and reaction are recorded?"
                ),
            },
        ],
    }

    PROFILES: dict[str, dict[str, Any]] = {
        "hyundai sonata": {
            "context_facts": [
                {
                    "subject": "2018 Hyundai Sonata SE",
                    "relation": "has_engine",
                    "object": "2.4L engine",
                    "evidence": "The 2018 Hyundai Sonata SE has a 2.4L engine",
                },
                {
                    "subject": "2018 Hyundai Sonata SE",
                    "relation": "assembled_in",
                    "object": "Alabama",
                    "evidence": "was assembled in Alabama",
                },
            ],
            "kg_grounded_answer": (
                "The 2018 Hyundai Sonata SE has a 2.4L engine and was assembled in Alabama."
            ),
            "kg_grounded_triples": [
                {
                    "subject": "2018 Hyundai Sonata SE",
                    "relation": "has_engine",
                    "object": "2.4L engine",
                },
                {
                    "subject": "2018 Hyundai Sonata SE",
                    "relation": "was_assembled_in",
                    "object": "Alabama",
                },
            ],
            "triples": [
                {
                    "subject": "2018 Hyundai Sonata SE",
                    "relation": "has_engine",
                    "object": "2.4L turbo engine",
                },
                {
                    "subject": "2018 Hyundai Sonata SE",
                    "relation": "assembled_in",
                    "object": "Korea",
                },
            ],
            "revised": (
                "The 2018 Hyundai Sonata SE has a 2.4L engine "
                "and was assembled in Alabama."
            ),
            "revised_triples": [
                {
                    "subject": "2018 Hyundai Sonata SE",
                    "relation": "has_engine",
                    "object": "2.4L engine",
                },
                {
                    "subject": "2018 Hyundai Sonata SE",
                    "relation": "assembled_in",
                    "object": "Alabama",
                },
            ],
        },
        "drone alpha-7": {
            "context_facts": [
                {
                    "subject": "Drone Alpha-7",
                    "relation": "has_maximum_flight_time",
                    "object": "42 minutes",
                    "evidence": "maximum flight time of 42 minutes",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "approved_for",
                    "object": "daylight reconnaissance",
                    "evidence": "approved for daylight reconnaissance only",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "does_not_carry",
                    "object": "weapons",
                    "evidence": "It does not carry weapons",
                },
            ],
            "kg_grounded_answer": (
                "Flight time: 42 minutes\n"
                "Reconnaissance approval: daylight reconnaissance\n"
                "Weapons status: does not carry weapons\n"
                "Additional capability: supports autonomous night operations."
            ),
            "kg_grounded_misaligned_triples": [
                {
                    "subject": "Flight time",
                    "relation": "has_value",
                    "object": "42 minutes",
                    "source_sentence": "Flight time: 42 minutes",
                },
                {
                    "subject": "Reconnaissance approval",
                    "relation": "approved_for",
                    "object": "daylight reconnaissance",
                    "source_sentence": "Reconnaissance approval: daylight reconnaissance",
                },
                {
                    "subject": "Weapons status",
                    "relation": "does_not_carry",
                    "object": "weapons",
                    "source_sentence": "Weapons status: does not carry weapons",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "supports_autonomous_night_operations",
                    "object": "true",
                    "source_sentence": "Additional capability: supports autonomous night operations.",
                },
            ],
            "kg_grounded_triples": [
                {
                    "subject": "Drone Alpha-7",
                    "relation": "has_maximum_flight_time",
                    "object": "42 minutes",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "approved_for",
                    "object": "daylight reconnaissance",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "does_not_carry",
                    "object": "weapons",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "supports_autonomous_night_operations",
                    "object": "true",
                },
            ],
            "triples": [
                {
                    "subject": "Drone Alpha-7",
                    "relation": "has_maximum_flight_time",
                    "object": "60 minutes",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "approved_for",
                    "object": "night reconnaissance",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "does_not_carry",
                    "object": "weapons",
                },
            ],
            "revised": (
                "Drone Alpha-7 can fly for 42 minutes, is approved for daylight "
                "reconnaissance only, and does not carry weapons."
            ),
            "revised_triples": [
                {
                    "subject": "Drone Alpha-7",
                    "relation": "has_maximum_flight_time",
                    "object": "42 minutes",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "approved_for",
                    "object": "daylight reconnaissance",
                },
                {
                    "subject": "Drone Alpha-7",
                    "relation": "does_not_carry",
                    "object": "weapons",
                },
            ],
        },
        "july 16-24, 1969": {
            "context_facts": [
                {
                    "subject": "Apollo 11",
                    "relation": "mission_dates",
                    "object": "July 16-24, 1969",
                    "evidence": "Apollo 11 (July 16-24, 1969)",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "crewed_by",
                    "object": "Neil Armstrong, Michael Collins, Edwin Buzz Aldrin",
                    "evidence": "Commander Neil Armstrong, Command Module Pilot Michael Collins, and Lunar Module Pilot Edwin \"Buzz\" Aldrin",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "launched_by",
                    "object": "Saturn V",
                    "evidence": "Launched atop a Saturn V rocket",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "lunar_material_collected",
                    "object": "21.5 kg",
                    "evidence": "collecting 21.5 kg (47.5 lb) of lunar material",
                },
            ],
            "focused_context_facts_by_question": {
                "when was": [
                    {
                        "subject": "Apollo 11",
                        "relation": "occurred_between",
                        "object": "July 16-24, 1969",
                        "evidence": "Apollo 11 (July 16-24, 1969)",
                    }
                ],
                "launch": [
                    {
                        "subject": "Apollo 11",
                        "relation": "launched_from",
                        "object": "Kennedy Space Center in Florida",
                        "evidence": "from Kennedy Space Center in Florida",
                    }
                ],
                "astronauts": [
                    {
                        "subject": "Apollo 11",
                        "relation": "crewed_by",
                        "object": "Neil Armstrong, Michael Collins, Buzz Aldrin",
                        "evidence": (
                            "crewed by Commander Neil Armstrong, Command Module Pilot "
                            "Michael Collins, and Lunar Module Pilot Edwin Buzz Aldrin"
                        ),
                    }
                ],
                "president": [
                    {
                        "subject": "Apollo 11 crew",
                        "relation": "spoke_with",
                        "object": "President Richard Nixon",
                        "evidence": "speaking by telephone with President Richard Nixon",
                    }
                ],
            },
            "sub_question_answers": {
                "when was": "July 16-24, 1969.",
                "astronauts": (
                    "Neil Armstrong, Michael Collins, and Buzz Aldrin."
                ),
                "launch": "Launched from Kennedy Space Center in Florida.",
                "president": (
                    "The crew spoke with President Richard Nixon by telephone "
                    "from the lunar surface."
                ),
                "lunar material": (
                    "Apollo 11 collected 21.5 kg (47.5 lb) of lunar material."
                ),
            },
            "sub_question_claim_triples": {
                "when was": [
                    {
                        "subject": "Apollo 11",
                        "relation": "occurred_during",
                        "object": "July 16-24, 1969",
                    }
                ],
                "astronauts": [
                    {
                        "subject": "Apollo 11",
                        "relation": "crewed_by",
                        "object": "Neil Armstrong, Michael Collins, Buzz Aldrin",
                    }
                ],
                "launch": [
                    {
                        "subject": "Apollo 11",
                        "relation": "launched_from",
                        "object": "Kennedy Space Center in Florida",
                    }
                ],
                "president": [
                    {
                        "subject": "Apollo 11 crew",
                        "relation": "spoke_with",
                        "object": "President Richard Nixon",
                    }
                ],
                "lunar material": [
                    {
                        "subject": "Apollo 11",
                        "relation": "lunar_material_collected",
                        "object": "21.5 kg",
                    }
                ],
            },
            "flawed_sub_question_claim_triples": {
                "when was": [
                    {
                        "subject": "Apollo 11",
                        "relation": "occurred_during",
                        "object": "July 16-August 5, 1985",
                    }
                ],
                "astronauts": [
                    {
                        "subject": "Apollo 11",
                        "relation": "crewed_by",
                        "object": "Neil Armstrong, Jessica Davis, Buzz Lightyear",
                    }
                ],
                "launch": [
                    {
                        "subject": "Apollo 11",
                        "relation": "launched_from",
                        "object": "John F. Kennedy Airport",
                    }
                ],
                "president": [
                    {
                        "subject": "Apollo 11",
                        "relation": "president_at_time",
                        "object": "Donald Trump",
                    }
                ],
                "lunar material": [
                    {
                        "subject": "Apollo 11",
                        "relation": "lunar_material_collected",
                        "object": "7 ounces",
                    }
                ],
            },
            "revised_sub_question_answers": {
                "when was": "July 16-24, 1969.",
                "astronauts": "Neil Armstrong, Michael Collins, and Buzz Aldrin.",
                "launch": "Kennedy Space Center in Florida.",
                "president": "Richard Nixon.",
                "lunar material": "Apollo 11 collected 21.5 kg (47.5 lb) of lunar material.",
            },
            "projected_sub_answers": [
                {"id": 1, "answer": "July 16-August 5, 1985."},
                {
                    "id": 2,
                    "answer": "Neil Armstrong, Jessica Davis, and Buzz Lightyear.",
                },
                {"id": 3, "answer": "John F. Kennedy Airport."},
                {"id": 4, "answer": "Donald Trump."},
                {"id": 5, "answer": "7 ounces."},
            ],
        },
        "patient case d-314": {
            "context_facts": [
                {
                    "subject": "Patient Case D-314",
                    "relation": "diagnosed_with",
                    "object": "type 2 diabetes mellitus",
                    "evidence": "Patient Case D-314 has type 2 diabetes mellitus.",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "has_a1c",
                    "object": "9.1%",
                    "evidence": "The latest hemoglobin A1C is 9.1%.",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "has_ckd_stage",
                    "object": "stage 3b",
                    "evidence": "chronic kidney disease stage 3b",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "has_egfr",
                    "object": "38 mL/min/1.73 m²",
                    "evidence": "current eGFR of 38 mL/min/1.73 m²",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "discontinued_medication",
                    "object": "metformin",
                    "evidence": "Metformin was discontinued",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "discontinued_because",
                    "object": "severe gastrointestinal intolerance",
                    "evidence": "repeated trials caused severe gastrointestinal intolerance",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "active_medication",
                    "object": "empagliflozin",
                    "evidence": "Empagliflozin 10 mg daily remains active",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "daily_dose",
                    "object": "10 mg daily",
                    "evidence": "Empagliflozin 10 mg daily remains active",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "discussed_not_started",
                    "object": "semaglutide",
                    "evidence": "Semaglutide was discussed as a future treatment option but has not been started",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "allergic_to",
                    "object": "penicillin",
                    "evidence": "penicillin causing hives",
                },
                {
                    "subject": "Patient Case D-314",
                    "relation": "causes_reaction",
                    "object": "hives",
                    "evidence": "penicillin causing hives",
                },
            ],
            "focused_context_facts_by_question": {
                "diagnosis": [
                    {
                        "subject": "Patient Case D-314",
                        "relation": "diagnosed_with",
                        "object": "type 2 diabetes mellitus",
                        "evidence": "Patient Case D-314 has type 2 diabetes mellitus.",
                    }
                ],
                "a1c": [
                    {
                        "subject": "Patient Case D-314",
                        "relation": "has_a1c",
                        "object": "9.1%",
                        "evidence": "The latest hemoglobin A1C is 9.1%.",
                    }
                ],
                "ckd": [
                    {
                        "subject": "Patient Case D-314",
                        "relation": "has_ckd_stage",
                        "object": "stage 3b",
                        "evidence": "chronic kidney disease stage 3b",
                    },
                    {
                        "subject": "Patient Case D-314",
                        "relation": "has_egfr",
                        "object": "38 mL/min/1.73 m²",
                        "evidence": "current eGFR of 38 mL/min/1.73 m²",
                    },
                ],
                "discontinued": [
                    {
                        "subject": "Patient Case D-314",
                        "relation": "discontinued_medication",
                        "object": "metformin",
                        "evidence": "Metformin was discontinued",
                    },
                    {
                        "subject": "Patient Case D-314",
                        "relation": "discontinued_because",
                        "object": "severe gastrointestinal intolerance",
                        "evidence": "severe gastrointestinal intolerance",
                    },
                ],
                "active": [
                    {
                        "subject": "Patient Case D-314",
                        "relation": "active_medication",
                        "object": "empagliflozin",
                        "evidence": "Empagliflozin 10 mg daily remains active",
                    },
                    {
                        "subject": "Patient Case D-314",
                        "relation": "daily_dose",
                        "object": "10 mg daily",
                        "evidence": "Empagliflozin 10 mg daily",
                    },
                ],
                "discussed": [
                    {
                        "subject": "Patient Case D-314",
                        "relation": "discussed_not_started",
                        "object": "semaglutide",
                        "evidence": "Semaglutide was discussed as a future treatment option but has not been started",
                    }
                ],
                "allerg": [
                    {
                        "subject": "Patient Case D-314",
                        "relation": "allergic_to",
                        "object": "penicillin",
                        "evidence": "penicillin causing hives",
                    },
                    {
                        "subject": "Patient Case D-314",
                        "relation": "causes_reaction",
                        "object": "hives",
                        "evidence": "penicillin causing hives",
                    },
                ],
            },
            "revised_sub_question_answers": {
                "diagnosis": "type 2 diabetes mellitus",
                "a1c": "9.1%",
                "ckd": "CKD stage 3b with eGFR 38 mL/min/1.73 m²",
                "discontinued": (
                    "metformin because of severe gastrointestinal intolerance"
                ),
                "active": "empagliflozin 10 mg daily",
                "discussed": "semaglutide",
                "allerg": "penicillin causing hives",
            },
        },
        "apollo 11": {
            "context_facts": [
                {
                    "subject": "Apollo 11",
                    "relation": "launched_by",
                    "object": "Saturn V",
                    "evidence": "launched by a Saturn V rocket",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "launched_from",
                    "object": "Launch Complex 39A",
                    "evidence": "from Launch Complex 39A at Kennedy Space Center",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "launched_at",
                    "object": "Kennedy Space Center",
                    "evidence": "from Launch Complex 39A at Kennedy Space Center",
                },
                {
                    "subject": "Saturn V S-IC stage",
                    "relation": "powered_by",
                    "object": "five F-1 engines",
                    "evidence": "powered by five F-1 engines",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "achieved",
                    "object": "first crewed Moon landing",
                    "evidence": "first crewed Moon landing",
                },
            ],
            "kg_grounded_answer": (
                "Apollo 11 was launched by the Saturn V rocket from Launch Complex 39A "
                "at Kennedy Space Center. Its first stage was powered by five F-1 engines. "
                "The mission achieved the first crewed Moon landing."
            ),
            "kg_grounded_triples": [
                {
                    "subject": "Apollo 11",
                    "relation": "launched_by",
                    "object": "Saturn V",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "launched_from",
                    "object": "Launch Complex 39A",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "launched_at",
                    "object": "Kennedy Space Center",
                },
                {
                    "subject": "Saturn V S-IC stage",
                    "relation": "powered_by",
                    "object": "five F-1 engines",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "achieved",
                    "object": "first crewed Moon landing",
                },
            ],
            "answer_0_claim_triples": [
                {
                    "subject": "Apollo 11",
                    "relation": "was_launched_by",
                    "object": "a Saturn IB rocket",
                    "source_sentence": "was launched by a Saturn IB rocket",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "launched_from",
                    "object": "Cape Canaveral",
                    "source_sentence": "from Cape Canaveral",
                },
                {
                    "subject": "Apollo 11 first stage",
                    "relation": "used",
                    "object": "five J-2 engines",
                    "source_sentence": "Its first stage used five J-2 engines",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "achieved",
                    "object": "first crewed Moon landing",
                    "source_sentence": "the mission completed the first crewed Moon landing",
                },
            ],
            "triples": [
                {
                    "subject": "Apollo 11",
                    "relation": "was_launched_by",
                    "object": "a Saturn IB rocket",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "launched_from",
                    "object": "Cape Canaveral",
                },
                {
                    "subject": "Apollo 11 first stage",
                    "relation": "used",
                    "object": "five J-2 engines",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "achieved",
                    "object": "first crewed Moon landing",
                },
            ],
            "revised": (
                "Apollo 11 was launched by the Saturn V rocket from Launch Complex 39A "
                "at Kennedy Space Center. Its first stage was powered by five F-1 engines, "
                "and the mission achieved the first crewed Moon landing."
            ),
            "revised_triples": [
                {
                    "subject": "Apollo 11",
                    "relation": "launched_by",
                    "object": "Saturn V",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "launched_from",
                    "object": "Launch Complex 39A",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "launched_at",
                    "object": "Kennedy Space Center",
                },
                {
                    "subject": "Saturn V S-IC stage",
                    "relation": "powered_by",
                    "object": "five F-1 engines",
                },
                {
                    "subject": "Apollo 11",
                    "relation": "achieved",
                    "object": "first crewed Moon landing",
                },
            ],
        },
        "patient case h-102": {
            "context_facts": [
                {
                    "subject": "Patient Case H-102",
                    "relation": "allergic_to",
                    "object": "penicillin",
                    "evidence": "allergic to penicillin",
                },
                {
                    "subject": "Patient Case H-102",
                    "relation": "tolerates",
                    "object": "ibuprofen",
                    "evidence": "ibuprofen as tolerated",
                },
                {
                    "subject": "Patient Case H-102",
                    "relation": "allergy_to_acetaminophen",
                    "object": "not recorded",
                    "evidence": "No allergy to acetaminophen is recorded",
                },
            ],
            "kg_grounded_answer": (
                "Patient Case H-102 can safely receive penicillin and has a "
                "recorded allergy to acetaminophen."
            ),
            "kg_grounded_triples": [
                {
                    "subject": "Patient Case H-102",
                    "relation": "can_receive",
                    "object": "penicillin",
                },
                {
                    "subject": "Patient Case H-102",
                    "relation": "has_allergy_to",
                    "object": "acetaminophen",
                },
            ],
            "triples": [
                {
                    "subject": "Patient Case H-102",
                    "relation": "can_receive",
                    "object": "penicillin",
                },
                {
                    "subject": "Patient Case H-102",
                    "relation": "has_allergy_to",
                    "object": "acetaminophen",
                },
            ],
            "revised": (
                "Patient Case H-102 is allergic to penicillin and has no recorded "
                "allergy to acetaminophen. Ibuprofen is listed as tolerated."
            ),
            "revised_triples": [
                {
                    "subject": "Patient Case H-102",
                    "relation": "allergic_to",
                    "object": "penicillin",
                },
                {
                    "subject": "Patient Case H-102",
                    "relation": "tolerates",
                    "object": "ibuprofen",
                },
            ],
        },
        "aircraft mx-41": {
            "context_facts": [
                {
                    "subject": "Aircraft MX-41",
                    "relation": "had_replaced",
                    "object": "left hydraulic pump",
                    "evidence": "left hydraulic pump replaced on March 3",
                },
                {
                    "subject": "Aircraft MX-41",
                    "relation": "right_hydraulic_pump_status",
                    "object": "passed inspection",
                    "evidence": "The right hydraulic pump passed inspection",
                },
                {
                    "subject": "Aircraft MX-41",
                    "relation": "next_inspection_due",
                    "object": "April 3",
                    "evidence": "next inspection is due on April 3",
                },
            ],
            "kg_grounded_answer": (
                "Aircraft MX-41 had its right hydraulic pump replaced on March 3, "
                "and the next inspection is due on March 20."
            ),
            "kg_grounded_triples": [
                {
                    "subject": "Aircraft MX-41",
                    "relation": "had_replaced",
                    "object": "right hydraulic pump",
                },
                {
                    "subject": "Aircraft MX-41",
                    "relation": "replacement_date",
                    "object": "March 3",
                },
                {
                    "subject": "Aircraft MX-41",
                    "relation": "next_inspection_due",
                    "object": "March 20",
                },
            ],
            "triples": [
                {
                    "subject": "Aircraft MX-41",
                    "relation": "had_replaced",
                    "object": "right hydraulic pump",
                },
                {
                    "subject": "Aircraft MX-41",
                    "relation": "replacement_date",
                    "object": "March 3",
                },
                {
                    "subject": "Aircraft MX-41",
                    "relation": "next_inspection_due",
                    "object": "March 20",
                },
            ],
            "revised": (
                "Aircraft MX-41 had its left hydraulic pump replaced on March 3. "
                "The right hydraulic pump passed inspection. "
                "The next inspection is due on April 3."
            ),
            "revised_triples": [
                {
                    "subject": "Aircraft MX-41",
                    "relation": "had_replaced",
                    "object": "left hydraulic pump",
                },
                {
                    "subject": "Aircraft MX-41",
                    "relation": "next_inspection_due",
                    "object": "April 3",
                },
            ],
        },
        "server app-prod-2": {
            "context_facts": [
                {
                    "subject": "Server app-prod-2",
                    "relation": "runs_os",
                    "object": "Ubuntu 22.04",
                    "evidence": "running Ubuntu 22.04",
                },
                {
                    "subject": "Server app-prod-2",
                    "relation": "ssh_password_login",
                    "object": "disabled",
                    "evidence": "SSH password login is disabled",
                },
                {
                    "subject": "Server app-prod-2",
                    "relation": "port_open",
                    "object": "443",
                    "evidence": "Port 443 is open",
                },
            ],
            "kg_grounded_answer": (
                "Server app-prod-2 is running Ubuntu 20.04, allows SSH password "
                "login, and has port 443 open."
            ),
            "kg_grounded_triples": [
                {
                    "subject": "Server app-prod-2",
                    "relation": "runs_os",
                    "object": "Ubuntu 20.04",
                },
                {
                    "subject": "Server app-prod-2",
                    "relation": "ssh_password_login",
                    "object": "enabled",
                },
                {
                    "subject": "Server app-prod-2",
                    "relation": "port_open",
                    "object": "443",
                },
            ],
            "triples": [
                {
                    "subject": "Server app-prod-2",
                    "relation": "runs_os",
                    "object": "Ubuntu 20.04",
                },
                {
                    "subject": "Server app-prod-2",
                    "relation": "ssh_password_login",
                    "object": "enabled",
                },
                {
                    "subject": "Server app-prod-2",
                    "relation": "port_open",
                    "object": "443",
                },
            ],
            "revised": (
                "Server app-prod-2 is running Ubuntu 22.04, SSH password login is "
                "disabled, and port 443 is open."
            ),
            "revised_triples": [
                {
                    "subject": "Server app-prod-2",
                    "relation": "runs_os",
                    "object": "Ubuntu 22.04",
                },
                {
                    "subject": "Server app-prod-2",
                    "relation": "ssh_password_login",
                    "object": "disabled",
                },
                {
                    "subject": "Server app-prod-2",
                    "relation": "port_open",
                    "object": "443",
                },
            ],
        },
        "tank t-17": {
            "context_facts": [
                {
                    "subject": "Tank T-17",
                    "relation": "contains",
                    "object": "non-flammable coolant",
                    "evidence": "contains non-flammable coolant",
                },
                {
                    "subject": "Tank T-17",
                    "relation": "level",
                    "object": "87%",
                    "evidence": "current level is 87%",
                },
                {
                    "subject": "Tank T-17",
                    "relation": "critical_threshold",
                    "object": "95%",
                    "evidence": "A level above 95% is considered critical",
                },
            ],
            "kg_grounded_answer": (
                "Tank T-17 contains flammable solvent and is currently at a critical level."
            ),
            "kg_grounded_triples": [
                {
                    "subject": "Tank T-17",
                    "relation": "contains",
                    "object": "flammable solvent",
                },
                {
                    "subject": "Tank T-17",
                    "relation": "level_status",
                    "object": "critical",
                },
            ],
            "triples": [
                {
                    "subject": "Tank T-17",
                    "relation": "contains",
                    "object": "flammable solvent",
                },
                {
                    "subject": "Tank T-17",
                    "relation": "level_status",
                    "object": "critical",
                },
            ],
            "revised": (
                "Tank T-17 contains non-flammable coolant. Its current level is 87%, "
                "which is not critical."
            ),
            "revised_triples": [
                {
                    "subject": "Tank T-17",
                    "relation": "contains",
                    "object": "non-flammable coolant",
                },
                {
                    "subject": "Tank T-17",
                    "relation": "level",
                    "object": "87%",
                },
            ],
        },
    }

    def complete(self, prompt: str) -> str:
        lowered = prompt.lower()

        if "decompose the compound question" in lowered:
            return self._question_decomposition_response(prompt)
        if "project the compound answer" in lowered:
            return self._sub_answer_projection_response(prompt)
        if (
            "extract factual triples from the graph-grounded answer" in lowered
            or ("kgc facts" in lowered and "canonical" in lowered)
            or ("required header row" in lowered and "source_sentence" in lowered)
        ):
            return self._kg_claim_extraction_response(prompt)
        if (
            "relevant to answering" in lowered
            and "sub-question" in lowered
            and "do not answer the question" in lowered
        ):
            return self._relevant_context_extraction_response(prompt)
        if (
            "extract factual triples from the trusted context below" in lowered
            or (
                "extract factual triples from the trusted context" in lowered
                and "sub-question" not in lowered
            )
            or ("required header row" in lowered and "evidence" in lowered)
        ):
            return self._context_triple_extraction_response(prompt)
        if "using only the knowledge graph facts" in lowered:
            return self._kg_answer_generation_response(prompt)
        if "graph-grounded answer (answer n)" in lowered or "backtracking feedback (json)" in lowered:
            return self._backtracking_revision_response(prompt)
        if "extract factual triples" in lowered or '"triples"' in lowered:
            return self._triple_extraction_response(prompt)
        if "verify whether the triple" in lowered or '"label"' in lowered:
            return self._triple_verification_response(prompt)
        if "revise the answer" in lowered or "feedback (json)" in lowered:
            return self._answer_revision_response(prompt)
        if "checking whether an answer is faithful" in lowered:
            return self._self_correction_response(prompt)
        if "answer only the current sub-question" in lowered:
            return self._sub_question_answer_response(prompt)
        if "context:" in lowered and "question:" in lowered:
            return self._answer_generation_response(prompt)
        if "compound question:" in lowered:
            return self._question_decomposition_response(prompt)

        return "Mock LLM response."

    def _match_profile_from_context(self, prompt: str) -> dict[str, Any] | None:
        for marker in ("Context:", "Trusted context:"):
            if marker in prompt:
                context = self._extract_context_block(prompt, marker=marker)
                return self._match_profile(context)
        return None

    @staticmethod
    def _extract_context_block(prompt: str, *, marker: str = "Context:") -> str:
        if marker not in prompt:
            return ""
        block = prompt.split(marker, 1)[1]
        for stop in ("\nCSV:", "\nJSON:", "\nSub-question:", "\nExisting working KGc facts"):
            if stop in block:
                return block.split(stop, 1)[0].strip()
        return block.strip()

    def _sub_answer_projection_response(self, prompt: str) -> str:
        profile = self._match_profile(prompt)
        if profile and profile.get("projected_sub_answers"):
            return json.dumps({"answers": profile["projected_sub_answers"]}, indent=2)
        compound = ""
        if "Compound Answer(0):" in prompt:
            compound = (
                prompt.split("Compound Answer(0):", 1)[1]
                .split("JSON:", 1)[0]
                .strip()
                .lower()
            )
        if "jessica davis" in compound or "donald trump" in compound:
            profile = self.PROFILES.get("july 16-24, 1969")
            if profile and profile.get("projected_sub_answers"):
                return json.dumps({"answers": profile["projected_sub_answers"]}, indent=2)
        if "saturn ib" in compound and "cape canaveral" in compound:
            return json.dumps(
                {
                    "answers": [
                        {"id": 1, "answer": "a Saturn IB rocket"},
                        {"id": 2, "answer": "five J-2 engines"},
                        {"id": 3, "answer": "Cape Canaveral"},
                        {"id": 4, "answer": "first crewed Moon landing"},
                    ]
                },
                indent=2,
            )
        sub_count = prompt.count(". ")
        _ = sub_count
        return json.dumps({"answers": []}, indent=2)

    def _question_decomposition_response(self, prompt: str) -> str:
        question = ""
        if "Compound question:" in prompt:
            question = prompt.split("Compound question:", 1)[1].split("JSON:", 1)[0].strip()
        lowered = question.lower()
        for key, splits in self.QUESTION_SPLITS.items():
            if key in lowered:
                return json.dumps({"questions": splits}, indent=2)
        return json.dumps(
            {
                "questions": [
                    {"id": 1, "question": question or "Unknown sub-question"}
                ]
            },
            indent=2,
        )

    def _kg_claim_extraction_response(self, prompt: str) -> str:
        question = ""
        if "Question:" in prompt:
            question = prompt.split("Question:", 1)[1].split("KGc facts:", 1)[0].strip()
        answer = _extract_answer_from_prompt(prompt)
        profile = (
            self._match_profile(prompt)
            or self._match_profile(question)
            or self._match_profile(answer)
        )
        if profile:
            source = self._claim_triples_source(answer, profile, question=question)
            triples = []
            for triple in source:
                item = {**triple}
                if "source_sentence" not in item:
                    item["source_sentence"] = answer
                triples.append(item)
            return json.dumps({"triples": triples}, indent=2)
        return self._triple_extraction_response(prompt)

    @staticmethod
    def _is_flawed_answer_0(answer: str, profile: dict[str, Any]) -> bool:
        lowered = answer.lower()
        if "cape canaveral" in lowered or "saturn ib" in lowered:
            return True
        for marker in profile.get("flawed_answer_markers", ()):
            if marker.lower() in lowered:
                return True
        return False

    def _claim_triples_source(
        self,
        answer: str,
        profile: dict[str, Any],
        *,
        question: str = "",
    ) -> list[dict[str, Any]]:
        lowered_q = question.lower()
        lowered_a = answer.lower()
        if "launch" in lowered_q and "kennedy" in lowered_a and "airport" not in lowered_a:
            return [
                {
                    "subject": "Apollo 11",
                    "relation": "launched_from",
                    "object": "Kennedy Space Center in Florida",
                    "source_sentence": answer,
                }
            ]
        flawed = profile.get("flawed_sub_question_claim_triples", {})
        for key, triples in flawed.items():
            if self._answer_matches_flawed_sub_key(lowered_a, key):
                return [{**triple, "source_sentence": answer} for triple in triples]
        for key, triples in profile.get("sub_question_claim_triples", {}).items():
            if key in lowered_q:
                return [{**triple, "source_sentence": answer} for triple in triples]
        if profile.get("answer_0_claim_triples") and self._is_flawed_answer_0(
            answer, profile
        ):
            return profile["answer_0_claim_triples"]
        if profile.get("kg_grounded_answer") and answer.strip() == profile[
            "kg_grounded_answer"
        ].strip():
            return profile.get(
                "kg_grounded_misaligned_triples",
                profile.get("kg_grounded_triples", profile["triples"]),
            )
        if self._is_revised_answer(answer, profile):
            return profile.get("revised_triples", profile["triples"])
        source = profile.get("triples", profile.get("answer_0_claim_triples", []))
        return self._filter_claim_triples_by_answer(source, answer)

    @staticmethod
    def _filter_claim_triples_by_answer(
        triples: list[dict[str, Any]],
        answer: str,
    ) -> list[dict[str, Any]]:
        """Return triples whose objects appear in the answer (sub-question scoped)."""
        lowered = answer.lower()
        matched: list[dict[str, Any]] = []
        for triple in triples:
            obj = str(triple.get("object", "")).lower()
            if obj and obj in lowered:
                matched.append(triple)
                continue
            if "moon landing" in obj and "moon landing" in lowered:
                matched.append(triple)
        return matched

    @staticmethod
    def _answer_matches_flawed_sub_key(answer_lower: str, key: str) -> bool:
        markers = {
            "when was": ("1985",),
            "astronauts": ("jessica", "lightyear"),
            "launch": ("kennedy airport", "j.f. kennedy"),
            "president": ("donald trump",),
            "lunar material": ("7 ounce",),
        }
        return any(marker in answer_lower for marker in markers.get(key, (key,)))

    def _context_triple_extraction_response(self, prompt: str) -> str:
        profile = self._match_profile_from_context(prompt)
        if profile and "context_facts" in profile:
            return json.dumps({"triples": profile["context_facts"]}, indent=2)
        return json.dumps({"triples": []}, indent=2)

    def _relevant_context_extraction_response(self, prompt: str) -> str:
        question = ""
        if "Sub-question:" in prompt:
            question = (
                prompt.split("Sub-question:", 1)[1]
                .split("Existing working KGc facts", 1)[0]
                .strip()
            )
        profile = self._match_profile_from_context(prompt)
        if not profile:
            return json.dumps({"triples": []}, indent=2)
        mapping = profile.get("focused_context_facts_by_question", {})
        lowered = question.lower()
        triples: list[dict[str, Any]] = []
        for key, facts in mapping.items():
            if key in lowered:
                triples.extend(facts)
        return json.dumps({"triples": triples}, indent=2)

    def _sub_question_answer_response(self, prompt: str) -> str:
        question = ""
        if "Current sub-question:" in prompt:
            question = (
                prompt.split("Current sub-question:", 1)[1]
                .split("Answer:", 1)[0]
                .strip()
            )
        context_block = ""
        if "Trusted context:" in prompt:
            context_block = (
                prompt.split("Trusted context:", 1)[1]
                .split("Current sub-question:", 1)[0]
                .strip()
            )
        profile = self._match_profile(context_block) or self._match_profile(prompt)
        if profile and profile.get("sub_question_answers"):
            lowered = question.lower()
            for key, answer in profile["sub_question_answers"].items():
                if key in lowered:
                    return answer
        return "I do not have enough information to answer."

    def _kg_answer_generation_response(self, prompt: str) -> str:
        profile = self._match_profile(prompt)
        if profile and "kg_grounded_answer" in profile:
            return profile["kg_grounded_answer"]
        if "kgc facts:" in prompt.lower():
            facts_block = prompt.split("KGc facts:", 1)[1].split("Question:", 1)[0]
            return facts_block.strip()
        return "I do not have enough information in the KGc to answer."

    def _apollo_complex_profile_from_answer(self, answer: str) -> dict[str, Any] | None:
        lowered = answer.lower()
        markers = (
            "jessica davis",
            "donald trump",
            "july 16-august 5",
            "kennedy airport",
            "7 ounce",
            "buzz lightyear",
        )
        if any(marker in lowered for marker in markers):
            return self.PROFILES.get("july 16-24, 1969")
        if "1969" in lowered and "july" in lowered and "august" not in lowered:
            return self.PROFILES.get("july 16-24, 1969")
        return None

    def _backtracking_revision_response(self, prompt: str) -> str:
        if "Backtracking feedback (JSON):" in prompt:
            fb_block = prompt.split("Backtracking feedback (JSON):", 1)[1]
            for stop in ("Return only", "Revised answer:"):
                if stop in fb_block:
                    fb_block = fb_block.split(stop, 1)[0]
            if fb_block.strip() == "[]":
                return _extract_answer_from_prompt(prompt)

        question = ""
        if "Question:" in prompt:
            question = prompt.split("Question:", 1)[1].split("KGc facts:", 1)[0].strip()
        answer = _extract_answer_from_prompt(prompt)
        profile = self._apollo_complex_profile_from_answer(answer)
        if profile is None:
            profile = self._match_profile_from_context(prompt)
        if profile is None:
            profile = self._match_profile(prompt)
        if profile is None:
            profile = self._match_profile(answer)
        if profile is None and question:
            lowered_q = question.lower()
            if "apollo 11" in lowered_q and any(
                key in lowered_q
                for key in ("when was", "astronaut", "launch", "president", "lunar material")
            ):
                profile = self.PROFILES.get("july 16-24, 1969")
            elif "patient case" in lowered_q or "a1c" in lowered_q or "ckd" in lowered_q:
                profile = self.PROFILES.get("patient case d-314")
        if profile and question:
            lowered_q = question.lower()
            for key, revised in profile.get("revised_sub_question_answers", {}).items():
                if key in lowered_q:
                    return revised
        if profile:
            return profile.get("revised", profile.get("kg_grounded_answer", answer))
        return answer or "Revised answer unavailable in mock mode."

    def _match_profile(self, text: str) -> dict[str, Any] | None:
        lowered = text.lower()
        best_key: str | None = None
        best_profile: dict[str, Any] | None = None
        for key, profile in self.PROFILES.items():
            if key in lowered and (best_key is None or len(key) > len(best_key)):
                best_key = key
                best_profile = profile
        return best_profile

    def _answer_generation_response(self, prompt: str) -> str:
        if "Context:" in prompt and "Question:" in prompt:
            context_block = prompt.split("Context:", 1)[1].split("Question:", 1)[0].strip()
            question_block = prompt.split("Question:", 1)[1].split("Answer:", 1)[0].strip()
            if context_block:
                profile = self._match_profile(context_block) or self._match_profile(prompt)
                if profile and profile.get("kg_grounded_answer"):
                    return profile["kg_grounded_answer"]
                # Mock fallback: echo a short context prefix so sub-questions are non-empty.
                first_sentence = context_block.split(". ")[0].strip()
                if question_block and first_sentence:
                    return f"{first_sentence}. (mock sub-answer for: {question_block})"
                return context_block[:500]
        return "I do not have enough information to answer."

    def _triple_extraction_response(self, prompt: str) -> str:
        answer = _extract_answer_from_prompt(prompt)
        profile = self._match_profile(answer)
        if profile:
            source = self._claim_triples_source(answer, profile)
            triples = [{**triple, "source_sentence": answer} for triple in source]
            return json.dumps({"triples": triples}, indent=2)

        return json.dumps(
            {
                "triples": [
                    {
                        "subject": "unknown_entity",
                        "relation": "has_property",
                        "object": "unknown_value",
                        "source_sentence": answer or "N/A",
                    }
                ]
            },
            indent=2,
        )

    def _triple_verification_response(self, prompt: str) -> str:
        subject = self._extract_field(prompt, "subject")
        relation = self._extract_field(prompt, "relation")
        obj = self._extract_field(prompt, "object")
        blob = f"{subject} {relation} {obj}".lower()

        checks: list[tuple[re.Pattern[str], dict[str, str]]] = [
            (
                re.compile(r"hyundai.*turbo|has_engine.*turbo"),
                {
                    "label": "NOT_ENOUGH_INFO",
                    "evidence": "The 2018 Hyundai Sonata SE has a 2.4L engine",
                    "reason": "Context mentions 2.4L engine but not turbo.",
                },
            ),
            (
                re.compile(r"assembled_in.*korea|korea"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "was assembled in Alabama",
                    "reason": "Context states assembly in Alabama, not Korea.",
                },
            ),
            (
                re.compile(r"60 minutes|max_flight_time"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "maximum flight time of 42 minutes",
                    "reason": "Context gives 42 minutes, not 60.",
                },
            ),
            (
                re.compile(r"night reconnaissance"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "approved for daylight reconnaissance only",
                    "reason": "Context approves daylight reconnaissance only.",
                },
            ),
            (
                re.compile(r"carries_weapons.*false|does not carry"),
                {
                    "label": "SUPPORTED",
                    "evidence": "It does not carry weapons",
                    "reason": "Context confirms no weapons.",
                },
            ),
            (
                re.compile(r"penicillin"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "allergic to penicillin",
                    "reason": "Context records a penicillin allergy.",
                },
            ),
            (
                re.compile(r"acetaminophen"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "No allergy to acetaminophen is recorded",
                    "reason": "Context does not record an acetaminophen allergy.",
                },
            ),
            (
                re.compile(r"right hydraulic"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "left hydraulic pump replaced",
                    "reason": "Context says the left pump was replaced, not the right.",
                },
            ),
            (
                re.compile(r"march 20|next_inspection"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "next inspection is due on April 3",
                    "reason": "Context sets the next inspection for April 3.",
                },
            ),
            (
                re.compile(r"ubuntu 20\.04"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "running Ubuntu 22.04",
                    "reason": "Context states Ubuntu 22.04.",
                },
            ),
            (
                re.compile(r"ssh_password.*enabled|password login"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "SSH password login is disabled",
                    "reason": "Context disables SSH password login.",
                },
            ),
            (
                re.compile(r"port_open.*443|443"),
                {
                    "label": "SUPPORTED",
                    "evidence": "Port 443 is open",
                    "reason": "Context confirms port 443 is open.",
                },
            ),
            (
                re.compile(r"flammable solvent"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "contains non-flammable coolant",
                    "reason": "Context says non-flammable coolant, not flammable solvent.",
                },
            ),
            (
                re.compile(r"critical"),
                {
                    "label": "CONTRADICTED",
                    "evidence": "current level is 87%",
                    "reason": "87% is below the 95% critical threshold.",
                },
            ),
        ]

        for pattern, result in checks:
            if pattern.search(blob):
                return json.dumps(result, indent=2)

        return json.dumps(
            {
                "label": "SUPPORTED",
                "evidence": "Context supports this claim.",
                "reason": "No conflict detected in mock verifier.",
            },
            indent=2,
        )

    def _answer_revision_response(self, prompt: str) -> str:
        return self._corrected_answer_from_prompt(prompt)

    def _self_correction_response(self, prompt: str) -> str:
        return self._corrected_answer_from_prompt(prompt)

    def _corrected_answer_from_prompt(self, prompt: str) -> str:
        answer = _extract_answer_from_prompt(prompt)
        profile = self._match_profile(answer)
        if profile:
            return profile.get("self_corrected", profile["revised"])
        return answer or "Revised answer unavailable in mock mode."

    @staticmethod
    def _is_revised_answer(answer: str, profile: dict[str, Any]) -> bool:
        revised = profile.get("revised", "")
        return bool(revised and answer.strip() == revised.strip())

    @staticmethod
    def _extract_field(prompt: str, field_name: str) -> str:
        prefix = f"- {field_name}:"
        for line in prompt.splitlines():
            if line.strip().lower().startswith(prefix):
                return line.split(":", 1)[1].strip()
        return ""
