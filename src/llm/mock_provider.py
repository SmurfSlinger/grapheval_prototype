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

        if (
            "extract factual triples from the graph-grounded answer" in lowered
            or ("kgc facts" in lowered and "canonical" in lowered)
        ):
            return self._kg_claim_extraction_response(prompt)
        if "extract factual triples from the trusted context" in lowered:
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
        if "context:" in lowered and "question:" in lowered:
            return self._answer_generation_response(prompt)

        return "Mock LLM response."

    def _match_profile_from_context(self, prompt: str) -> dict[str, Any] | None:
        if "Context:" in prompt:
            context = prompt.split("Context:", 1)[1].split("JSON:", 1)[0].strip()
            return self._match_profile(context)
        return None

    def _kg_claim_extraction_response(self, prompt: str) -> str:
        answer = _extract_answer_from_prompt(prompt)
        profile = self._match_profile(answer) or self._match_profile(prompt)
        if profile:
            source = self._claim_triples_source(answer, profile)
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

    def _claim_triples_source(self, answer: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
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
        return profile.get("triples", profile.get("answer_0_claim_triples", []))

    def _context_triple_extraction_response(self, prompt: str) -> str:
        profile = self._match_profile_from_context(prompt)
        if profile and "context_facts" in profile:
            return json.dumps({"triples": profile["context_facts"]}, indent=2)
        return json.dumps({"triples": []}, indent=2)

    def _kg_answer_generation_response(self, prompt: str) -> str:
        profile = self._match_profile(prompt)
        if profile and "kg_grounded_answer" in profile:
            return profile["kg_grounded_answer"]
        if "kgc facts:" in prompt.lower():
            facts_block = prompt.split("KGc facts:", 1)[1].split("Question:", 1)[0]
            return facts_block.strip()
        return "I do not have enough information in the KGc to answer."

    def _backtracking_revision_response(self, prompt: str) -> str:
        if "Backtracking feedback (JSON):" in prompt:
            fb_block = prompt.split("Backtracking feedback (JSON):", 1)[1]
            for stop in ("Return only", "Revised answer:"):
                if stop in fb_block:
                    fb_block = fb_block.split(stop, 1)[0]
            if fb_block.strip() == "[]":
                return _extract_answer_from_prompt(prompt)

        answer = _extract_answer_from_prompt(prompt)
        profile = self._match_profile(answer) or self._match_profile(prompt)
        if profile:
            return profile.get("revised", profile.get("kg_grounded_answer", answer))
        return answer or "Revised answer unavailable in mock mode."

    def _match_profile(self, text: str) -> dict[str, Any] | None:
        lowered = text.lower()
        for key, profile in self.PROFILES.items():
            if key in lowered:
                return profile
        return None

    def _answer_generation_response(self, prompt: str) -> str:
        for line in prompt.splitlines():
            stripped = line.strip()
            if stripped.startswith("Context:"):
                context = stripped.removeprefix("Context:").strip()
                if context:
                    return context
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
