#!/usr/bin/env python3
"""Generate a hop-semantics-valid NHS WannaCry multihop benchmark."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

try:
    from scripts.nhs_wannacry_hop_semantics import (
        ENTITY_ALIASES,
        detect_ambiguous_discourse,
        detect_entities_in_text,
        expanded_aliases,
        locality_audit,
        normalize_entity,
        select_question_anchors,
        shortest_directed_distance,
        shortcut_flags,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution.
    from nhs_wannacry_hop_semantics import (
        ENTITY_ALIASES,
        detect_ambiguous_discourse,
        detect_entities_in_text,
        expanded_aliases,
        locality_audit,
        normalize_entity,
        select_question_anchors,
        shortest_directed_distance,
        shortcut_flags,
    )

ROOT = Path(__file__).resolve().parents[1]
DATASET_OUT = ROOT / "data" / "test_sets" / "nhs_wannacry_multihop_50.json"
AUDIT_OUT = ROOT / "data" / "test_sets" / "nhs_wannacry_multihop_50.audit.json"
AUDIT_MD_OUT = ROOT / "docs" / "NHS_WANNACRY_HOP_AUDIT.md"
HUMAN_REVIEW_OUT = ROOT / "data" / "test_sets" / "nhs_wannacry_human_review.json"
INVENTORY_OUT = ROOT / "data" / "sources" / "nhs_wannacry" / "fact_inventory.json"

ROOT_ENTITY = "WannaCry attack on the NHS"
DOMAIN = "NHS WannaCry ransomware incident (England, May 2017)"
DATASET_ID = "nhs_wannacry_multihop_50"

NAO = "nao_wannacry_2018"
NAO_SUMMARY = "nao_wannacry_summary_2018"
DHSC = "dhsc_lessons_2018"
CISA = "cisa_ta17_132a_2017"
MS = "microsoft_ms17_010_2017"

HOP_DEFINITION = (
    "hop_count = minimum number of trusted directed graph edges needed to derive "
    "the expected answer from the question's question_anchor_entities, under "
    "allowed alias normalization, without outside knowledge."
)


@dataclass(frozen=True)
class EdgeSpec:
    subject: str
    relation: str
    object: str
    source_id: str
    page: int | str
    section: str
    evidence: str

    def triple(self) -> tuple[str, str, str]:
        return self.subject, self.relation, self.object


@dataclass(frozen=True)
class Fact:
    fact_id: str
    subject: str
    relation: str
    object: str
    fact_kind: str
    source_id: str
    page: int | str
    section: str
    evidence: str
    derivation_rule: str | None = None
    parent_fact_ids: list[str] | None = None

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["parent_fact_ids"] = data["parent_fact_ids"] or []
        return data


def E(
    subject: str,
    relation: str,
    obj: str,
    source_id: str,
    page: int | str,
    section: str,
    evidence: str,
) -> EdgeSpec:
    return EdgeSpec(subject, relation, obj, source_id, page, section, evidence)


def chain_specs() -> dict[str, list[EdgeSpec]]:
    """Return five mostly-linear source-grounded branches of length ten."""

    R = ROOT_ENTITY
    return {
        "technical exploit and patch": [
            E(
                R,
                "caused_by",
                "WannaCry ransomware",
                NAO_SUMMARY,
                4,
                "Summary, paragraph 1",
                "NAO describes the 12 May 2017 incident as a global ransomware attack known as WannaCry that affected the NHS.",
            ),
            E(
                "WannaCry ransomware",
                "includes",
                "WannaCry dropper",
                CISA,
                1,
                "Technical analysis",
                "CISA describes the first WannaCry file as a dropper that contains and runs the ransomware.",
            ),
            E(
                "WannaCry dropper",
                "used",
                "MS17-010/EternalBlue SMBv1 exploit",
                CISA,
                1,
                "Technical analysis",
                "CISA says the dropper propagated via the MS17-010/EternalBlue SMBv1.0 exploit.",
            ),
            E(
                "MS17-010/EternalBlue SMBv1 exploit",
                "affected",
                "Microsoft SMBv1 vulnerability",
                CISA,
                1,
                "Technical analysis",
                "CISA states the malware propagated by exploiting the SMBv1 vulnerability documented by Microsoft bulletin MS17-010.",
            ),
            E(
                "Microsoft SMBv1 vulnerability",
                "affected",
                "Microsoft Windows SMBv1 server",
                MS,
                "HTML",
                "Executive Summary",
                "Microsoft says the vulnerabilities involved Microsoft Server Message Block 1.0 server.",
            ),
            E(
                "Microsoft Windows SMBv1 server",
                "status_was",
                "Vulnerable to remote code execution",
                MS,
                "HTML",
                "Executive Summary",
                "Microsoft states the most severe vulnerability could allow remote code execution.",
            ),
            E(
                "Vulnerable to remote code execution",
                "caused_by",
                "Specially crafted SMBv1 messages",
                MS,
                "HTML",
                "Executive Summary",
                "Remote code execution could occur if an attacker sent specially crafted messages to an SMBv1 server.",
            ),
            E(
                "Specially crafted SMBv1 messages",
                "affected",
                "SMBv1 crafted-request handling",
                MS,
                "HTML",
                "Executive Summary",
                "Microsoft says the update corrected how SMBv1 handles specially crafted requests.",
            ),
            E(
                "SMBv1 crafted-request handling",
                "addressed_by",
                "Corrected SMBv1 request handling",
                MS,
                "HTML",
                "Executive Summary",
                "The security update addresses the vulnerabilities by correcting SMBv1 handling of crafted requests.",
            ),
            E(
                "Corrected SMBv1 request handling",
                "addressed_by",
                "Microsoft Security Bulletin MS17-010",
                MS,
                "HTML",
                "Executive Summary",
                "Microsoft Security Bulletin MS17-010 is the security update that resolves the SMBv1 vulnerabilities.",
            ),
        ],
        "supported Windows patching": [
            E(
                R,
                "affected",
                "Majority unpatched Windows 7 devices",
                NAO_SUMMARY,
                10,
                "Lessons learned, paragraph 12",
                "NHS Digital told NAO the majority of infected NHS devices were unpatched but on supported Microsoft Windows 7.",
            ),
            E(
                "Majority unpatched Windows 7 devices",
                "status_was",
                "Supported Microsoft Windows",
                NAO_SUMMARY,
                10,
                "Lessons learned, paragraph 12",
                "The majority of infected NHS devices were on supported Microsoft Windows rather than unsupported Windows XP.",
            ),
            E(
                "Supported Microsoft Windows",
                "addressed_by",
                "MS17-010 patch for supported Windows 7",
                NAO,
                18,
                "Part Two, paragraph 2.5",
                "Trusts using Windows 7 could have protected themselves by applying the March 2017 Microsoft patch.",
            ),
            E(
                "MS17-010 patch for supported Windows 7",
                "published_on",
                "14 March 2017",
                MS,
                "HTML",
                "Publication metadata",
                "The Microsoft bulletin states it was published on March 14, 2017.",
            ),
            E(
                "14 March 2017",
                "followed_by",
                "CareCERT alert on 17 March 2017",
                NAO,
                18,
                "Part Two, paragraph 2.5",
                "NAO records that NHS Digital issued a CareCERT alert on 17 March asking organisations to apply the patch.",
            ),
            E(
                "CareCERT alert on 17 March 2017",
                "followed_by",
                "CareCERT alert on 28 April 2017",
                NAO,
                18,
                "Part Two, paragraph 2.5",
                "NAO records a second CareCERT alert on 28 April asking organisations to apply the patch.",
            ),
            E(
                "CareCERT alert on 28 April 2017",
                "warned_to_apply",
                "Patch systems to prevent WannaCry",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "NHS Digital issued critical alerts in March and April 2017 warning organisations to patch systems to prevent WannaCry.",
            ),
            E(
                "Patch systems to prevent WannaCry",
                "warned_to_apply",
                "Local NHS organisations",
                NAO,
                21,
                "Part Three, paragraph 3.1",
                "Local health organisations were responsible for managing their cyber-security and implementing advice.",
            ),
            E(
                "Local NHS organisations",
                "status_was",
                "Local implementation of CareCERT patch advice",
                NAO_SUMMARY,
                10,
                "Lessons learned, paragraph 14",
                "Post-incident assurance focused on whether organisations had implemented critical CareCERT patch alerts.",
            ),
            E(
                "Local implementation of CareCERT patch advice",
                "status_was",
                "Not all organisations implemented critical patch advice before attack",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "NAO found there had been no formal mechanism to assess whether local organisations complied with cyber advice before 12 May.",
            ),
        ],
        "trust impact and diversions": [
            E(
                R,
                "affected",
                "At least 80 of 236 trusts",
                NAO,
                11,
                "Part One, paragraph 1.2",
                "NHS England data analysed by NAO showed at least 80 of 236 trusts across England were affected.",
            ),
            E(
                "At least 80 of 236 trusts",
                "includes",
                "34 infected and locked-out trusts",
                NAO,
                11,
                "Part One, paragraph 1.2",
                "Of the 80 affected trusts, 34 were infected and locked out of devices.",
            ),
            E(
                "34 infected and locked-out trusts",
                "includes",
                "25 infected acute trusts",
                NAO,
                11,
                "Part One, paragraph 1.2",
                "The 34 infected locked-out trusts included 25 acute trusts.",
            ),
            E(
                "25 infected acute trusts",
                "affected",
                "Five acute trusts diverting emergency ambulances",
                NAO,
                13,
                "Part One, paragraph 1.7",
                "Of the 25 infected acute trusts, five had to divert emergency ambulance services.",
            ),
            E(
                "Five acute trusts diverting emergency ambulances",
                "includes",
                "Barts Health NHS Trust",
                NAO,
                13,
                "Part One, paragraph 1.7",
                "Barts Health NHS Trust is one of the five listed diverting trusts.",
            ),
            E(
                "Barts Health NHS Trust",
                "affected",
                "Royal London Hospital",
                NAO,
                13,
                "Part One, paragraph 1.7",
                "NAO lists Barts Health NHS Trust with Royal London Hospital.",
            ),
            E(
                "Royal London Hospital",
                "affected",
                "Emergency ambulance services",
                NAO,
                13,
                "Part One, paragraph 1.7",
                "Royal London Hospital was one of the listed hospitals diverting emergency ambulance services.",
            ),
            E(
                "Emergency ambulance services",
                "caused_by",
                "Patients travelling further for emergency care",
                NAO,
                14,
                "Part One, paragraph 1.10",
                "Some patients had to travel further because five hospitals diverted services.",
            ),
            E(
                "Patients travelling further for emergency care",
                "status_was",
                "Number of diverted ambulances and patients not collected",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "NHS England did not collect data on how many ambulances and patients were diverted.",
            ),
            E(
                "Number of diverted ambulances and patients not collected",
                "status_was",
                "Department and NHS England did not know full diversion count",
                NAO_SUMMARY,
                8,
                "Key findings, paragraph 6",
                "NAO says neither the Department nor NHS England knew how many ambulances and patients were diverted.",
            ),
        ],
        "cancelled appointments": [
            E(
                R,
                "affected",
                "6912 identified cancelled appointments",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "NHS England identified 6,912 cancelled appointments during its incident data collection.",
            ),
            E(
                "6912 identified cancelled appointments",
                "counted_as",
                "NHS England identified cancellations",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "NHS England identified that 6,912 appointments had been cancelled.",
            ),
            E(
                "NHS England identified cancellations",
                "estimated_as",
                "About 19494 estimated cancellations",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "NHS England estimated the total number of cancelled appointments as around 19,494.",
            ),
            E(
                "About 19494 estimated cancellations",
                "based_on",
                "Normal follow-up-to-first appointment rate",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "The estimate was based on the normal rate of follow-up appointments to first appointments.",
            ),
            E(
                "Normal follow-up-to-first appointment rate",
                "includes",
                "Repeat outpatient appointments",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "NAO says the initial 6,912 figure did not include repeat outpatient appointments.",
            ),
            E(
                "Repeat outpatient appointments",
                "status_was",
                "Excluded from initial 6912 collection",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "Repeat outpatient appointments were excluded from the initial 6,912 count.",
            ),
            E(
                "Excluded from initial 6912 collection",
                "includes",
                "Cancellations identified after 18 May",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "The initial 6,912 figure also excluded cancellations identified after 18 May.",
            ),
            E(
                "Cancellations identified after 18 May",
                "contributed_to",
                "Incomplete national cancellation total",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "Because later cancellations were omitted, the initial collection did not capture the complete national total.",
            ),
            E(
                "Incomplete national cancellation total",
                "counted_as",
                "Actual cancelled-appointment number",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "NAO records that the actual number of cancelled appointments was not established from the initial collection.",
            ),
            E(
                "Actual cancelled-appointment number",
                "status_was",
                "Not planned for identification by NHS England",
                NAO,
                14,
                "Part One, paragraph 1.8",
                "NHS England told NAO it did not plan to identify the actual cancellation number.",
            ),
        ],
        "primary-care recovery": [
            E(
                R,
                "infected",
                "603 primary care and other NHS organisations",
                NAO_SUMMARY,
                4,
                "Summary, paragraph 2",
                "NAO reports that a further 603 primary care and other NHS organisations were infected.",
            ),
            E(
                "603 primary care and other NHS organisations",
                "includes",
                "595 GP practices",
                NAO_SUMMARY,
                4,
                "Summary, paragraph 2",
                "The 603 infected primary care and other organisations included 595 GP practices.",
            ),
            E(
                "595 GP practices",
                "affected",
                "Machines rebuilt before patching",
                DHSC,
                12,
                "Incident chronology, paragraph 2.14",
                "The DHSC review says 595 infected practices needed machines rebuilt before they were patched.",
            ),
            E(
                "Machines rebuilt before patching",
                "addressed_by",
                "Re-installation and patching by IT delivery partners",
                DHSC,
                12,
                "Incident chronology, paragraph 2.14",
                "Commissioning Support Units and other IT delivery partners worked to re-install and patch primary-care systems.",
            ),
            E(
                "Re-installation and patching by IT delivery partners",
                "status_was",
                "95 percent complete by 17 May 2017",
                DHSC,
                12,
                "Incident chronology, paragraph 2.14",
                "The DHSC review says 95% of infected practices were re-installed and patched by 17 May.",
            ),
            E(
                "95 percent complete by 17 May 2017",
                "status_was",
                "Remaining 5 percent completed by Friday 19 May 2017",
                DHSC,
                12,
                "Incident chronology, paragraph 2.14",
                "The remaining 5% were completed by Friday 19 May when the incident was stood down.",
            ),
            E(
                "Remaining 5 percent completed by Friday 19 May 2017",
                "occurred_on",
                "Incident stood down at 5:30 pm",
                NAO,
                15,
                "Part One, paragraph 1.13 and Figure 2",
                "NAO Figure 2 records the incident being stood down at 5:30 pm on Friday 19 May.",
            ),
            E(
                "Incident stood down at 5:30 pm",
                "coordinated_by",
                "NHS England stand-down decision",
                NAO,
                15,
                "Part One, paragraph 1.13 and Figure 2",
                "NAO records NHS England standing down the incident on Friday 19 May.",
            ),
            E(
                "NHS England stand-down decision",
                "counted_as",
                "One-week incident period from 12 May to 19 May 2017",
                DHSC,
                10,
                "Incident chronology, paragraph 2.7",
                "The DHSC review says the incident lasted a week, from 16:00 on 12 May to 17:30 on 19 May.",
            ),
            E(
                "One-week incident period from 12 May to 19 May 2017",
                "status_was",
                "One-week NHS cyber incident",
                DHSC,
                10,
                "Incident chronology, paragraph 2.7",
                "The DHSC review describes the incident period as lasting from 12 May to 19 May 2017.",
            ),
        ],
        "preparedness and CareCERT": [
            E(
                R,
                "prepared_gap",
                "Department of Health",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "NAO says the Department had no formal mechanism before 12 May to assess local compliance with its cyber advice.",
            ),
            E(
                "Department of Health",
                "lacked_before_attack",
                "Formal local cyber-compliance assessment mechanism",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "Before 12 May, the Department had no formal mechanism for assessing local compliance with its advice and guidance.",
            ),
            E(
                "Formal local cyber-compliance assessment mechanism",
                "assessed",
                "CareCERT alert compliance assurance",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "The missing mechanism would have assessed whether organisations complied with cyber advice and guidance such as CareCERT alerts.",
            ),
            E(
                "CareCERT alert compliance assurance",
                "includes",
                "CareCERT alerts of March and April 2017",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "The relevant advice included NHS Digital's March and April 2017 CareCERT patch alerts.",
            ),
            E(
                "CareCERT alerts of March and April 2017",
                "issued_by",
                "NHS Digital",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "NHS Digital issued critical alerts in March and April 2017 warning organisations to patch systems.",
            ),
            E(
                "NHS Digital",
                "lacked_before_attack",
                "Power to mandate local remedial action",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "NAO says NHS Digital cannot mandate a local body to take remedial action.",
            ),
            E(
                "Power to mandate local remedial action",
                "assessed",
                "CareCERT Assure assessments",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "Before the attack, NHS Digital had instead conducted on-site cyber-security assessments for trusts.",
            ),
            E(
                "CareCERT Assure assessments",
                "counted_as",
                "88 of 236 trusts",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "By 12 May, NHS Digital had inspected 88 of 236 trusts.",
            ),
            E(
                "88 of 236 trusts",
                "status_was",
                "None passed",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "NAO says none of the 88 inspected trusts had passed.",
            ),
            E(
                "None passed",
                "counted_as",
                "Before 12 May 2017",
                NAO_SUMMARY,
                6,
                "Key findings, paragraph 4",
                "The none-passed result refers to assessments completed before 12 May 2017.",
            ),
        ],
    }


def extra_fact_specs() -> list[EdgeSpec]:
    """Safe side-branch facts that enrich grounding without shortening QA paths."""

    R = ROOT_ENTITY
    return [
        E(
            R,
            "affected",
            "Unsupported Windows XP minority issues",
            NAO_SUMMARY,
            10,
            "Lessons learned, paragraph 12",
            "NAO records that unsupported XP devices were in the minority of identified infection issues.",
        ),
        E(
            "Unsupported Windows XP minority issues",
            "counted_as",
            "About 5 percent of NHS IT estate on 12 May 2017",
            NAO,
            18,
            "Part Two, paragraph 2.7",
            "The Department told NAO that about 5% of the NHS IT estate still used Windows XP on 12 May 2017.",
        ),
        E(
            "About 5 percent of NHS IT estate on 12 May 2017",
            "includes",
            "Computers and medical equipment",
            NAO,
            18,
            "Part Two, paragraph 2.7",
            "The 5% Windows XP estate included computers and medical equipment.",
        ),
        E(
            "Computers and medical equipment",
            "includes",
            "MRI scanners",
            NAO,
            18,
            "Part Two, paragraph 2.6",
            "NAO cites medical equipment such as MRI scanners with Windows XP embedded.",
        ),
        E(
            "MRI scanners",
            "addressed_by",
            "Isolating devices from the network",
            NAO,
            18,
            "Part Two, paragraph 2.6",
            "Trusts running Windows XP medical equipment could have protected themselves by isolating devices from the rest of the network.",
        ),
        E(
            "Isolating devices from the network",
            "affected",
            "Manual workarounds",
            NAO,
            18,
            "Part Two, paragraph 2.6",
            "NAO notes that isolating Windows XP medical equipment may necessitate manual workarounds.",
        ),
        E(
            "Manual workarounds",
            "includes",
            "Pen and paper records",
            NAO,
            12,
            "Part One, paragraph 1.5",
            "Some disrupted trusts used manual workarounds and recorded information using pen and paper.",
        ),
        E(
            R,
            "affected",
            "46 disrupted but not infected trusts",
            NAO,
            11,
            "Part One, paragraph 1.2",
            "NAO separately counts 46 trusts that were not infected but reported disruption.",
        ),
        E(
            "46 disrupted but not infected trusts",
            "status_was",
            "Not infected",
            NAO,
            11,
            "Part One, paragraph 1.2",
            "NAO explicitly distinguishes the 46 trusts as not infected but reporting disruption.",
        ),
        E(
            "46 disrupted but not infected trusts",
            "affected",
            "Shutting down devices as a precaution",
            NAO_SUMMARY,
            7,
            "Key findings, paragraph 5",
            "The 46 non-infected disrupted trusts included organisations that shut down devices or systems as a precaution.",
        ),
        E(
            R,
            "status_was",
            "No spread via NHSmail",
            NAO_SUMMARY,
            10,
            "Lessons learned, paragraph 12",
            "NHS Digital confirmed there were no instances of the ransomware spreading via NHSmail.",
        ),
        E(
            "No spread via NHSmail",
            "includes",
            "NHSmail",
            NAO_SUMMARY,
            10,
            "Lessons learned, paragraph 12",
            "NAO says there were no instances of WannaCry spreading via NHSmail, the NHS email system.",
        ),
        E(
            "NHSmail",
            "status_was",
            "NHS email system",
            NAO_SUMMARY,
            10,
            "Lessons learned, paragraph 12",
            "NAO identifies NHSmail as the NHS email system.",
        ),
        E(
            R,
            "addressed_by",
            "NHS England major incident response",
            NAO_SUMMARY,
            4,
            "Summary, paragraph 1",
            "At 4 pm on 12 May, NHS England declared the cyber attack a major incident and implemented emergency arrangements.",
        ),
        E(
            "NHS England major incident response",
            "occurred_on",
            "4:00 pm on 12 May 2017",
            NAO_SUMMARY,
            4,
            "Summary, paragraph 1",
            "At 4 pm on 12 May, NHS England declared the cyber attack a major incident.",
        ),
        E(
            "NHS England major incident response",
            "coordinated_by",
            "Emergency Preparedness Resilience and Response plans",
            NAO_SUMMARY,
            9,
            "Key findings, paragraph 10",
            "NAO says NHS England initiated EPRR plans at 6:45 pm to act as the single point of coordination.",
        ),
        E(
            "Emergency Preparedness Resilience and Response plans",
            "occurred_on",
            "6:45 pm on 12 May 2017",
            NAO_SUMMARY,
            9,
            "Key findings, paragraph 10",
            "NAO records NHS England initiating EPRR plans at 6:45 pm on 12 May.",
        ),
        E(
            R,
            "addressed_by",
            "WannaCry kill-switch",
            NAO_SUMMARY,
            4,
            "Summary, paragraph 1",
            "On the evening of 12 May a cyber-security researcher activated a kill-switch so WannaCry stopped locking devices.",
        ),
        E(
            "WannaCry kill-switch",
            "caused_by",
            "Cyber-security researcher",
            NAO_SUMMARY,
            8,
            "Key findings, paragraph 8",
            "NAO says a cyber-security researcher activated the kill-switch.",
        ),
        E(
            "WannaCry kill-switch",
            "status_was",
            "Activated evening of 12 May 2017",
            NAO_SUMMARY,
            4,
            "Summary, paragraph 1",
            "A cyber-security researcher activated the kill-switch on the evening of 12 May.",
        ),
        E(
            "WannaCry kill-switch",
            "addressed_by",
            "Further WannaCry device locking",
            NAO_SUMMARY,
            4,
            "Summary, paragraph 1",
            "The kill-switch meant WannaCry stopped locking devices.",
        ),
        E(
            "WannaCry dropper",
            "used",
            "UDP 137-138 and TCP 139/445 scanning",
            CISA,
            1,
            "Technical analysis",
            "CISA reports the dropper attempts connections using UDP 137 and 138 and TCP 139 and 445.",
        ),
        E(
            R,
            "addressed_by",
            "CISA TA17-132A alert",
            CISA,
            1,
            "Alert metadata",
            "The CISA/US-CERT TA17-132A alert addressed the WannaCry ransomware campaign on 12 May 2017.",
        ),
        E(
            "CISA TA17-132A alert",
            "published_on",
            "12 May 2017",
            CISA,
            1,
            "Alert metadata",
            "The CISA/US-CERT alert is the 12 May 2017 TA17-132A WannaCry alert.",
        ),
        E(
            "CISA TA17-132A alert",
            "warned_to_apply",
            "Apply Microsoft patch for MS17-010",
            CISA,
            1,
            "Recommended Steps for Prevention",
            "CISA recommends applying the Microsoft patch for the MS17-010 SMB vulnerability dated March 14, 2017.",
        ),
        E(
            "CISA TA17-132A alert",
            "warned_to_apply",
            "Disable SMBv1 if patch cannot be applied",
            CISA,
            1,
            "Recommendations for Network Protection",
            "CISA recommends considering disabling SMBv1 if the patch cannot be applied.",
        ),
        E(
            "CISA TA17-132A alert",
            "warned_to_apply",
            "Block SMB at the network boundary",
            CISA,
            1,
            "Recommendations for Network Protection",
            "CISA recommends blocking SMB at the network boundary if patching cannot be applied.",
        ),
    ]


QUESTION_TEXT: dict[str, list[str]] = {
    "technical exploit and patch": [
        "During the WannaCry attack on the NHS, what malicious software drove the incident?",
        "During the WannaCry attack on the NHS, along the technical malware-propagation chain, what dropper-style component contained and ran the ransomware?",
        "During the WannaCry attack on the NHS, along the technical malware-propagation chain, what exploit enabled network spread of the ransomware?",
        "During the WannaCry attack on the NHS, along the technical malware-propagation chain, what Microsoft network-service vulnerability was targeted?",
        "During the WannaCry attack on the NHS, along the technical malware-propagation chain, what Microsoft server component was exposed?",
        "During the WannaCry attack on the NHS, along the technical malware-propagation chain, what severe security consequence could result from the exposed service?",
        "During the WannaCry attack on the NHS, along the technical malware-propagation chain, what crafted attacker input could trigger remote code execution on the exposed service?",
        "During the WannaCry attack on the NHS, along the technical malware-propagation chain, what request-handling area did crafted attacker input expose?",
        "During the WannaCry attack on the NHS, along the technical malware-propagation chain, what correction fixed crafted-request handling?",
        "In the May 2017 NHS WannaCry attack, along the technical malware-propagation chain, which Microsoft security bulletin supplied the final fix?",
    ],
    "supported Windows patching": [
        "During the WannaCry attack on the NHS, what operating-system pattern described most infected devices?",
        "During the WannaCry attack on the NHS, along the infected-device operating-system chain, what support category did the majority fall into?",
        "During the WannaCry attack on the NHS, along the infected-device operating-system chain, what March Microsoft update could have protected the estate?",
        "During the WannaCry attack on the NHS, along the infected-device operating-system chain, what date was attached to the protective update?",
        "During the WannaCry attack on the NHS, along the infected-device operating-system chain, what first NHS cyber alert followed the publication date?",
        "During the WannaCry attack on the NHS, along the infected-device operating-system chain, what second NHS cyber alert reinforced the warning before the incident?",
        "During the WannaCry attack on the NHS, along the infected-device operating-system chain, what patching action did the alert sequence urge?",
        "During the WannaCry attack on the NHS, along the infected-device operating-system chain, which local bodies were responsible for carrying out the patch advice?",
        "During the WannaCry attack on the NHS, along the infected-device operating-system chain, what implementation state followed after local bodies received the patch advice?",
        "In the May 2017 NHS WannaCry attack, along the infected-device operating-system chain, what unresolved compliance finding remained after local patch-advice implementation?",
    ],
    "trust impact and diversions": [
        "During the WannaCry attack on the NHS, what was the documented minimum count of affected NHS trusts?",
        "During the WannaCry attack on the NHS, along the trust-impact diversion chain, what infected-and-locked-out subset was counted?",
        "During the WannaCry attack on the NHS, along the trust-impact diversion chain, what acute-trust subset came from the locked-out trust group?",
        "During the WannaCry attack on the NHS, along the trust-impact diversion chain, what emergency-transport outcome was recorded among acute trusts?",
        "During the WannaCry attack on the NHS, along the trust-impact diversion chain, which London trust appeared in the ambulance-diversion sequence?",
        "During the WannaCry attack on the NHS, along the trust-impact diversion chain, which hospital was tied to the London trust in the ambulance-diversion sequence?",
        "During the WannaCry attack on the NHS, along the trust-impact diversion chain, what service line was disrupted at the London hospital in the ambulance-diversion sequence?",
        "During the WannaCry attack on the NHS, along the trust-impact diversion chain, what patient consequence followed from emergency-ambulance disruption?",
        "During the WannaCry attack on the NHS, along the trust-impact diversion chain, what diversion-count data was missing from the national record after emergency-ambulance disruption?",
        "In the May 2017 NHS WannaCry attack, along the trust-impact diversion chain, what did the missing national diversion-count data mean for national bodies?",
    ],
    "cancelled appointments": [
        "During the WannaCry attack on the NHS, what initial cancelled-appointment count did NHS England identify?",
        "During the WannaCry attack on the NHS, along the appointment-disruption accounting chain, how was the initial appointment count classified in the collection?",
        "During the WannaCry attack on the NHS, along the appointment-disruption accounting chain, what total cancellation estimate came from the initial count?",
        "During the WannaCry attack on the NHS, along the appointment-disruption accounting chain, what normal-rate assumption supported the cancellation estimate?",
        "During the WannaCry attack on the NHS, along the appointment-disruption accounting chain, which appointment category was excluded from the initial collection?",
        "During the WannaCry attack on the NHS, along the appointment-disruption accounting chain, how was the excluded appointment category treated in the initial collection?",
        "During the WannaCry attack on the NHS, along the appointment-disruption accounting chain, what additional cancellations were omitted after the initial collection cutoff?",
        "During the WannaCry attack on the NHS, along the appointment-disruption accounting chain, what national picture resulted from omitted cancellation records?",
        "During the WannaCry attack on the NHS, along the appointment-disruption accounting chain, what actual total did the incomplete national collection leave unresolved?",
        "In the May 2017 NHS WannaCry attack, along the appointment-disruption accounting chain, what was NHS England's position on identifying the actual cancellation total?",
    ],
    "primary-care recovery": [
        "During the WannaCry attack on the NHS, how many primary-care and other NHS organisations were infected?",
        "During the WannaCry attack on the NHS, along the primary-care recovery chain, how many GP practices were part of the infected primary-care group?",
        "During the WannaCry attack on the NHS, along the primary-care recovery chain, what remediation prerequisite applied before patching?",
        "During the WannaCry attack on the NHS, along the primary-care recovery chain, what IT-partner work addressed the remediation prerequisite?",
        "During the WannaCry attack on the NHS, along the primary-care recovery chain, what completion level had the recovery work reached at the recorded midweek checkpoint?",
        "During the WannaCry attack on the NHS, along the primary-care recovery chain, what completion milestone followed for the remaining recovery work?",
        "During the WannaCry attack on the NHS, along the primary-care recovery chain, what incident-status event occurred once primary-care recovery was complete?",
        "During the WannaCry attack on the NHS, along the primary-care recovery chain, which national decision coordinated the stand-down event?",
        "During the WannaCry attack on the NHS, along the primary-care recovery chain, what period did the national stand-down decision close?",
        "During the WannaCry attack on the NHS, along the primary-care recovery chain, how did the lessons-learned review describe the closed incident period?",
    ],
    "preparedness and CareCERT": [
        "During the WannaCry attack on the NHS, which central department began the preparedness-gap chain?",
        "During the WannaCry attack on the NHS, along the preparedness-gap chain, what formal local cyber-compliance mechanism was missing before the incident?",
        "During the WannaCry attack on the NHS, along the preparedness-gap chain, what assurance function would the missing compliance mechanism have provided?",
        "During the WannaCry attack on the NHS, along the preparedness-gap chain, what March-April cyber-advice area was covered by the assurance gap?",
        "During the WannaCry attack on the NHS, along the preparedness-gap chain, which digital body issued the relevant March-April cyber alerts?",
        "During the WannaCry attack on the NHS, along the preparedness-gap chain, what remedial authority was unavailable in the local cyber-advice sequence?",
        "During the WannaCry attack on the NHS, along the preparedness-gap chain, what on-site cyber-assessment programme existed despite the missing remedial authority?",
        "During the WannaCry attack on the NHS, along the preparedness-gap chain, what inspection coverage had the on-site assessment programme reached before the incident?",
        "During the WannaCry attack on the NHS, along the preparedness-gap chain, what pass outcome did the pre-incident on-site inspection coverage produce?",
        "In the May 2017 NHS WannaCry attack, along the preparedness-gap chain, what timing qualified the pre-incident pass-outcome finding?",
    ],
}


CHAIN_ORDER = [
    "technical exploit and patch",
    "supported Windows patching",
    "trust impact and diversions",
    "cancelled appointments",
    "preparedness and CareCERT",
]


def build_facts() -> list[Fact]:
    specs = [spec for chain in chain_specs().values() for spec in chain]
    specs.extend(extra_fact_specs())
    triples = [spec.triple() for spec in specs]
    duplicates = [triple for triple, count in Counter(triples).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate fact triples: {duplicates}")
    return [
        Fact(
            fact_id=f"nw_f{index:03d}",
            subject=spec.subject,
            relation=spec.relation,
            object=spec.object,
            fact_kind="direct",
            source_id=spec.source_id,
            page=spec.page,
            section=spec.section,
            evidence=spec.evidence,
            parent_fact_ids=[],
        )
        for index, spec in enumerate(specs, start=1)
    ]


def path_nodes(path: list[list[str]]) -> list[str]:
    if not path:
        return []
    return [path[0][0], *[edge[2] for edge in path]]


def build_questions(
    triples: list[tuple[str, str, str]],
    trusted_context: str,
) -> list[dict[str, Any]]:
    chains = chain_specs()
    questions: list[dict[str, Any]] = []
    graph_entities = {node for subject, _relation, obj in triples for node in (subject, obj)}
    aliases = expanded_aliases(graph_entities, ENTITY_ALIASES)
    for hop in range(1, 11):
        for question_index, chain_name in enumerate(CHAIN_ORDER, start=1):
            path = [list(edge.triple()) for edge in chains[chain_name][:hop]]
            question = QUESTION_TEXT[chain_name][hop - 1]
            answer = path[-1][2]
            anchor_info = select_question_anchors(
                question,
                triples,
                answer,
                hop,
                graph_entities,
                aliases,
                prefer_root=True,
            )
            anchors = anchor_info["question_anchor_entities"]
            question_id = f"nhs_wannacry_h{hop:02d}_q{question_index:02d}"
            if not anchors:
                raise ValueError(
                    f"{question_id}: question does not express a valid graph anchor "
                    f"(detected={anchor_info['detected_entities']})"
                )
            distance = shortest_directed_distance(triples, anchors, answer)
            final_subject = path[-1][0]
            flags = shortcut_flags(
                question,
                path,
                answer,
                aliases,
                triples=triples,
                question_anchor_entities=anchors,
                hop_count=hop,
            )
            detected_entities = anchor_info["detected_entities"]
            all_shortcut_entities: list[str] = []
            anchor_label_set = {normalize_entity(anchor) for anchor in anchors}
            for entity in detected_entities:
                if normalize_entity(entity) in anchor_label_set:
                    continue
                entity_distance = shortest_directed_distance(triples, [entity], answer)
                if entity_distance is not None and entity_distance < hop:
                    all_shortcut_entities.append(entity)
            flags["shortcut_entities"] = sorted(set(all_shortcut_entities))
            flags["mentioned_entities"] = detected_entities
            flags["late_chain_entity_mentioned"] = any(
                normalize_entity(entity) != normalize_entity(final_subject)
                for entity in flags["shortcut_entities"]
            )
            flags["one_hop_parent_mentioned"] = any(
                normalize_entity(entity) == normalize_entity(final_subject)
                for entity in flags["shortcut_entities"]
            ) or (
                flags["direct_final_subject_mentioned"]
                and normalize_entity(final_subject) not in anchor_label_set
            )
            ambiguous_discourse_markers = detect_ambiguous_discourse(question)
            local_audit = locality_audit(question, answer, trusted_context)
            if distance != hop:
                raise ValueError(f"{question_id}: shortest distance {distance} != hop {hop}")
            if normalize_entity(path[0][0]) not in anchor_label_set:
                raise ValueError(
                    f"{question_id}: expected_path does not start at a detected question anchor"
                )
            if ambiguous_discourse_markers:
                raise ValueError(
                    f"{question_id}: ambiguous discourse markers remain: {ambiguous_discourse_markers}"
                )
            if hop > 1 and flags["direct_final_subject_mentioned"]:
                raise ValueError(f"{question_id}: question mentions final subject")
            if hop > 1 and flags["expected_answer_mentioned"]:
                raise ValueError(f"{question_id}: question mentions expected answer")
            if flags["shortcut_entities"]:
                raise ValueError(
                    f"{question_id}: question mentions shorter-path graph entities: "
                    f"{flags['shortcut_entities']}"
                )
            entities = sorted({node for edge in path for node in (edge[0], edge[2])})
            relations = sorted({edge[1] for edge in path})
            questions.append(
                {
                    "id": question_id,
                    "hop_count": hop,
                    "question": question,
                    "expected_answer": answer,
                    "expected_path": path,
                    "graph_root_entity": ROOT_ENTITY,
                    "question_anchor_entities": anchors,
                    "reasoning_anchor_entities": anchors,
                    "anchor_detection": {
                        "anchor_detected_from_question": True,
                        "anchor_detection_method": "alias_match",
                        "matched_aliases": anchor_info["matched_aliases"],
                        "detected_entities": anchors,
                    },
                    "hop_semantics": "minimum_required_path",
                    "shortcut_audit": {
                        "shortest_distance_from_question_anchor": distance,
                        "shortest_anchor_distance": distance,
                        "direct_final_subject_mentioned": flags["direct_final_subject_mentioned"],
                        "final_edge_subject": final_subject,
                        "expected_answer_mentioned": flags["expected_answer_mentioned"],
                        "late_chain_entity_mentioned": flags["late_chain_entity_mentioned"],
                        "one_hop_parent_mentioned": flags["one_hop_parent_mentioned"],
                        "mentioned_entities": flags["mentioned_entities"],
                        "shortcut_entities": flags["shortcut_entities"],
                        "ambiguous_discourse_markers": ambiguous_discourse_markers,
                        "human_review_status": "not_reviewed",
                        "locality": local_audit,
                        "unresolved_shortcut": False,
                        "review_notes": (
                            "Generator notes only; not a human review. Question anchor was "
                            "detected from question text; shortest directed distance from the "
                            "detected anchor equals declared hop count; automated checks found "
                            "no late-chain entity, final-edge subject, expected-answer, or "
                            "ambiguous discourse shortcut."
                        ),
                    },
                    "required_entities": entities,
                    "required_relations": relations,
                    "difficulty_notes": (
                        f"{hop}-hop minimum required path through the {chain_name} branch; "
                        "answer is the path terminus."
                    ),
                    "requires_alias_resolution": hop >= 4,
                    "requires_avoiding_sibling_branches": hop >= 3,
                    "requires_composed_answer": False,
                    "requires_carry_forward": hop >= 3,
                    "source_grounded": True,
                    "apollo_like_difficulty_flags": {
                        "path_following": True,
                        "branch_name": chain_name,
                        "hop_depth": hop,
                        "distractor_sibling_edges_present": hop >= 3,
                        "answer_is_path_terminus": True,
                        "requires_temporal_anchor": any(
                            "2017" in part or "May" in part for edge in path for part in edge
                        ),
                        "requires_count_distinction": any(
                            any(character.isdigit() for character in part)
                            for edge in path
                            for part in edge
                        ),
                    },
                }
            )
    return questions


def trusted_context_prose() -> str:
    return (
        "On Friday 12 May 2017, the WannaCry ransomware campaign affected the NHS in England. "
        "The National Audit Office described it as a global ransomware attack and the largest "
        "cyber attack to affect the NHS in England. At 4:00 pm, NHS England declared a major "
        "incident and later used Emergency Preparedness, Resilience and Response arrangements "
        "to coordinate the response. The incident lasted from 12 May to 19 May 2017 and was "
        "stood down at 5:30 pm on Friday 19 May. A cyber-security researcher activated the "
        "WannaCry kill-switch on the evening of 12 May, which stopped further device locking.\n\n"
        "The technical route involved a WannaCry dropper and the MS17-010/EternalBlue SMBv1 "
        "exploit. CISA described the dropper as containing and running the ransomware, using "
        "network scanning on UDP ports 137 and 138 and TCP ports 139 and 445, and propagating "
        "through the SMBv1 exploit. Microsoft explained that the vulnerability affected the "
        "Microsoft Windows SMBv1 server and could allow remote code execution when specially "
        "crafted SMBv1 messages were sent. The security update corrected how SMBv1 handled "
        "crafted requests, and Microsoft Security Bulletin MS17-010 supplied that correction. "
        "Microsoft published the bulletin on 14 March 2017. CISA's 12 May alert recommended "
        "applying the Microsoft patch, disabling SMBv1 if the patch could not be applied, or "
        "blocking SMB at the network boundary.\n\n"
        "The operating-system story was not that Windows XP was the main cause. NHS Digital told "
        "NAO that the majority of infected NHS devices were unpatched but still on supported "
        "Microsoft Windows 7. Trusts using Windows 7 could have protected themselves by applying "
        "the March 2017 Microsoft patch. Unsupported Windows XP devices were a minority of the "
        "identified issues. The Department told NAO that about five percent of the NHS IT estate "
        "still used Windows XP on 12 May 2017, including computers and medical equipment. NAO "
        "gave MRI scanners as an example of medical equipment with embedded Windows XP; isolation "
        "from the network could protect such devices, although that could require manual "
        "workarounds such as pen and paper records. NHS Digital issued CareCERT alerts on 17 March "
        "and 28 April 2017 telling local NHS organisations to patch systems to prevent WannaCry, "
        "but the incident showed that not all organisations had implemented critical patch advice "
        "before the attack.\n\n"
        "NHS Digital said WannaCry spread via the internet, including the N3 network, and confirmed "
        "there were no instances of spread via NHSmail. NHSmail was the NHS email system. NAO also "
        "said internet-facing firewall management would have guarded organisations against infection "
        "whether patched or not, because all infected NHS organisations had unpatched or unsupported "
        "Windows operating systems.\n\n"
        "Preparedness and assurance were also central. The Department of Health had no formal "
        "mechanism before 12 May to assess local compliance with cyber advice and guidance. Such a "
        "mechanism would have assessed CareCERT alert compliance, including the March and April "
        "2017 patch alerts issued by NHS Digital. NHS Digital could not mandate local remedial "
        "action. It had conducted CareCERT Assure assessments of hospital cyber-security before "
        "the attack; by 12 May, 88 of 236 trusts had been inspected and none had passed.\n\n"
        "The impact counts remained distinct. At least 80 of 236 NHS trusts were affected. Of "
        "those, 34 were infected and locked out of devices, including 25 acute trusts. Separately, "
        "46 trusts were disrupted but not infected, including organisations that shut down devices "
        "as a precaution. Five infected acute trusts diverted emergency ambulance services. NAO "
        "listed Barts Health NHS Trust with Royal London Hospital among those diversions. Diversions "
        "affected emergency ambulance services and meant some patients travelled further for "
        "emergency care. NHS England did not collect how many ambulances and patients were diverted, "
        "so the Department and NHS England did not know the full diversion count.\n\n"
        "Primary care was also affected. A further 603 primary care and other NHS organisations "
        "were infected, including 595 GP practices. Those practices needed machines rebuilt before "
        "patching. Commissioning Support Units and other IT delivery partners worked on "
        "re-installation and patching. The DHSC review said 95 percent of infected practices were "
        "complete by 17 May and the remaining five percent by Friday 19 May, when the incident was "
        "stood down.\n\n"
        "Appointments and operations were disrupted. NHS England identified 6,912 cancelled "
        "appointments, including cancelled patient operations, and estimated around 19,494 "
        "cancellations using the normal rate of follow-up appointments to first appointments. The "
        "initial count excluded repeat outpatient appointments and cancellations identified after "
        "18 May. NHS England told NAO that it did not plan to identify the actual cancellation "
        "number. NHS England also identified at least 139 urgent referrals for potential cancer "
        "cancelled as at 18 May."
    )


def graph_metrics(facts: list[Fact], questions: list[dict[str, Any]], trusted_context: str) -> dict[str, Any]:
    triples = [(fact.subject, fact.relation, fact.object) for fact in facts]
    entities = sorted({node for subject, _relation, obj in triples for node in (subject, obj)})
    relation_counts = Counter(relation for _subject, relation, _obj in triples)
    undirected: dict[str, set[str]] = defaultdict(set)
    for subject, _relation, obj in triples:
        undirected[subject].add(obj)
        undirected[obj].add(subject)
    unseen = set(entities)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            node = stack.pop()
            neighbors = undirected[node] & unseen
            unseen -= neighbors
            stack.extend(neighbors)
    hop_distribution = Counter(question["hop_count"] for question in questions)
    audit_rows = audit_questions(triples, questions)
    return {
        "entity_count": len(entities),
        "edge_count": len(triples),
        "relation_count": len(relation_counts),
        "relation_counts": dict(sorted(relation_counts.items())),
        "relations_used_at_least_twice": sum(1 for count in relation_counts.values() if count >= 2),
        "root_out_degree": sum(1 for fact in facts if fact.subject == ROOT_ENTITY),
        "connected_components": components,
        "isolate_count": sum(1 for entity in entities if not undirected[entity]),
        "duplicate_triples": len(triples) - len(set(triples)),
        "hop_distribution": dict(sorted(hop_distribution.items())),
        "hop10_distinct_first_edges": len(
            {tuple(question["expected_path"][0]) for question in questions if question["hop_count"] == 10}
        ),
        "shortcut_count": sum(1 for row in audit_rows if row["shortcut_detected"]),
        "unresolved_shortcuts": sum(1 for row in audit_rows if row["unresolved_shortcut"]),
        "ambiguous_discourse_count": sum(1 for row in audit_rows if row["ambiguous_discourse_markers"]),
        "locality_warning_count": sum(1 for row in audit_rows if row["locality"]["locality_warning"]),
        "unreviewed_count": sum(
            1 for row in audit_rows if row["human_review_status"] == "not_reviewed"
        ),
        "trusted_context_contains_nw_f": "nw_f" in trusted_context,
        "trusted_context_contains_expected_path": "expected_path" in trusted_context.lower(),
        "trusted_context_contains_expected_answer": "expected_answer" in trusted_context.lower(),
    }


def validate_artifacts(
    facts: list[Fact],
    questions: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    triples = {(fact.subject, fact.relation, fact.object) for fact in facts}
    expected_hops = {hop: 5 for hop in range(1, 11)}
    if len(questions) != 50:
        errors.append("expected exactly 50 questions")
    if Counter(question["hop_count"] for question in questions) != expected_hops:
        errors.append("expected five questions for each hop")
    if metrics["entity_count"] < 45:
        errors.append("expected at least 45 entities")
    if metrics["edge_count"] < 55:
        errors.append("expected at least 55 facts")
    if not (15 <= metrics["relation_count"] <= 30):
        errors.append("expected 15-30 relation types")
    if metrics["relations_used_at_least_twice"] <= metrics["relation_count"] // 2:
        errors.append("expected most relation types to be reused")
    if not (6 <= metrics["root_out_degree"] <= 12):
        errors.append("expected root out-degree between 6 and 12")
    if metrics["connected_components"] != 1:
        errors.append("expected one connected component")
    if metrics["isolate_count"]:
        errors.append("expected no isolate entities")
    if metrics["duplicate_triples"]:
        errors.append("expected no duplicate triples")
    if metrics["unresolved_shortcuts"]:
        errors.append("expected zero unresolved shortcuts")
    if metrics["ambiguous_discourse_count"]:
        errors.append("expected zero ambiguous discourse markers")
    if (
        metrics["trusted_context_contains_nw_f"]
        or metrics["trusted_context_contains_expected_path"]
        or metrics["trusted_context_contains_expected_answer"]
    ):
        errors.append("trusted_context contains scoring metadata markers")
    for question in questions:
        path = question["expected_path"]
        if len(path) != question["hop_count"]:
            errors.append(f"{question['id']}: path length mismatch")
        if path[0][0] != ROOT_ENTITY:
            errors.append(f"{question['id']}: path does not start at root")
        if question.get("graph_root_entity") != ROOT_ENTITY:
            errors.append(f"{question['id']}: graph_root_entity mismatch")
        if question.get("question_anchor_entities") != question.get("reasoning_anchor_entities"):
            errors.append(f"{question['id']}: anchor alias fields diverge")
        if not question.get("question_anchor_entities"):
            errors.append(f"{question['id']}: missing question anchor")
        if question.get("shortcut_audit", {}).get("human_review_status") != "not_reviewed":
            errors.append(f"{question['id']}: human review status should be pending")
        if len(path_nodes(path)) != len(set(path_nodes(path))):
            errors.append(f"{question['id']}: repeated path node")
        if len({tuple(edge) for edge in path}) != len(path):
            errors.append(f"{question['id']}: duplicate path edge")
        if any(tuple(edge) not in triples for edge in path):
            errors.append(f"{question['id']}: path edge missing from graph")
        if any(left[2] != right[0] for left, right in zip(path, path[1:])):
            errors.append(f"{question['id']}: path is not contiguous")
    return errors


def validate_question_ids(questions: list[dict[str, Any]]) -> None:
    expected_ids = [f"nhs_wannacry_h{hop:02d}_q{idx:02d}" for hop in range(1, 11) for idx in range(1, 6)]
    actual_ids = [question["id"] for question in questions]
    if actual_ids != expected_ids:
        raise ValueError("question IDs are not the required sequence")


def audit_questions(
    triples: list[tuple[str, str, str]],
    questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for question in questions:
        path = question["expected_path"]
        final_subject = path[-1][0]
        anchors = question["question_anchor_entities"]
        distance = shortest_directed_distance(
            triples,
            anchors,
            question["expected_answer"],
        )
        shortcut_audit = question["shortcut_audit"]
        direct_final_subject_mentioned = shortcut_audit["direct_final_subject_mentioned"]
        expected_answer_mentioned = shortcut_audit["expected_answer_mentioned"]
        late_chain_entity_mentioned = shortcut_audit["late_chain_entity_mentioned"]
        one_hop_parent_mentioned = shortcut_audit["one_hop_parent_mentioned"]
        ambiguous_discourse_markers = shortcut_audit["ambiguous_discourse_markers"]
        shortcut_detected = bool(
            distance is not None
            and distance < question["hop_count"]
            or (question["hop_count"] > 1 and direct_final_subject_mentioned)
            or (question["hop_count"] > 1 and expected_answer_mentioned)
            or late_chain_entity_mentioned
            or one_hop_parent_mentioned
        )
        path_node_list = path_nodes(path)
        repeated_nodes = len(path_node_list) != len(set(path_node_list))
        duplicate_edges = len({tuple(edge) for edge in path}) != len(path)
        unresolved = bool(
            shortcut_detected
            or repeated_nodes
            or duplicate_edges
            or distance != question["hop_count"]
            or ambiguous_discourse_markers
        )
        rows.append(
            {
                "id": question["id"],
                "hop_count": question["hop_count"],
                "question": question["question"],
                "graph_root_entity": question["graph_root_entity"],
                "question_anchor_entities": anchors,
                "reasoning_anchor_entities": question["reasoning_anchor_entities"],
                "anchor_detection": question["anchor_detection"],
                "expected_answer": question["expected_answer"],
                "final_edge_subject": final_subject,
                "expected_path_length": len(path),
                "shortest_distance_from_question_anchor": distance,
                "shortest_anchor_distance": distance,
                "direct_final_subject_mentioned": direct_final_subject_mentioned,
                "expected_answer_mentioned": expected_answer_mentioned,
                "late_chain_entity_mentioned": late_chain_entity_mentioned,
                "one_hop_parent_mentioned": one_hop_parent_mentioned,
                "mentioned_entities": shortcut_audit["mentioned_entities"],
                "shortcut_entities": shortcut_audit["shortcut_entities"],
                "ambiguous_discourse_markers": ambiguous_discourse_markers,
                "human_review_status": shortcut_audit["human_review_status"],
                "locality": shortcut_audit["locality"],
                "repeated_nodes": repeated_nodes,
                "duplicate_edges": duplicate_edges,
                "shortcut_detected": shortcut_detected,
                "unresolved_shortcut": unresolved,
                "review_notes": shortcut_audit["review_notes"],
            }
        )
    return rows


def build_dataset(facts: list[Fact], questions: list[dict[str, Any]], metrics: dict[str, Any], trusted_context: str) -> dict[str, Any]:
    return {
        "test_set_id": DATASET_ID,
        "domain": DOMAIN,
        "root_entity": ROOT_ENTITY,
        "description": (
            "Source-grounded 50-question multihop set on the documented May 2017 WannaCry "
            "impact on the NHS in England, regenerated so declared hops equal the minimum "
            "trusted directed path from anchors explicitly detected in question text to answers."
        ),
        "source_manifest_path": "data/sources/nhs_wannacry/source_manifest.json",
        "requires_fact_provenance": True,
        "hop_semantics": {
            "definition": HOP_DEFINITION,
            "traversal": "directed",
            "alias_normalization": (
                "case-insensitive alias matching; questions must express an anchor entity and "
                "validation must not silently fall back to the graph root"
            ),
            "relation_paraphrase": "questions may paraphrase relations but must not use raw relation labels as quiz keys",
            "shortcut": (
                "any shorter directed path from an explicit question anchor entity to the answer, "
                "naming any non-anchor graph entity with a shorter answer distance, naming the "
                "final-edge subject, or naming the expected answer in questions with hop_count>1"
            ),
            "human_review": "pending; shortcut audits are generator notes only",
            "inflation": "paths that insert semantically empty intermediate noun phrases are invalid",
        },
        "trusted_context": trusted_context,
        "expected_graph_facts": [fact.to_json() for fact in facts],
        "graph_properties": {
            "root_node": ROOT_ENTITY,
            "node_count": metrics["entity_count"],
            "edge_count_designed": metrics["edge_count"],
            "connected_components_designed": metrics["connected_components"],
        },
        "graph_quality": {
            "entity_count": metrics["entity_count"],
            "edge_count": metrics["edge_count"],
            "relation_count": metrics["relation_count"],
            "root_out_degree": metrics["root_out_degree"],
            "relations_used_at_least_twice": metrics["relations_used_at_least_twice"],
            "connected_components": metrics["connected_components"],
            "isolate_count": metrics["isolate_count"],
            "duplicate_triples": metrics["duplicate_triples"],
            "shortcut_count": metrics["shortcut_count"],
            "unresolved_shortcuts": metrics["unresolved_shortcuts"],
            "ambiguous_discourse_count": metrics["ambiguous_discourse_count"],
            "locality_warning_count": metrics["locality_warning_count"],
            "unreviewed_count": metrics["unreviewed_count"],
        },
        "questions": questions,
    }


def build_audit(dataset: dict[str, Any]) -> dict[str, Any]:
    triples = [
        (fact["subject"], fact["relation"], fact["object"])
        for fact in dataset["expected_graph_facts"]
    ]
    rows = audit_questions(triples, dataset["questions"])
    hop_distribution = Counter(row["hop_count"] for row in rows)
    return {
        "audit_id": "nhs_wannacry_hop_semantics_audit",
        "test_set_id": DATASET_ID,
        "definition": HOP_DEFINITION,
        "preliminary_shortcuts_before_rewrite": 15,
        "question_count": len(rows),
        "shortcut_count": sum(1 for row in rows if row["shortcut_detected"]),
        "unresolved_shortcuts": sum(1 for row in rows if row["unresolved_shortcut"]),
        "ambiguous_discourse_count": sum(1 for row in rows if row["ambiguous_discourse_markers"]),
        "locality_warning_count": sum(1 for row in rows if row["locality"]["locality_warning"]),
        "unreviewed_count": sum(
            1 for row in rows if row["human_review_status"] == "not_reviewed"
        ),
        "hop_distribution": {str(hop): hop_distribution[hop] for hop in sorted(hop_distribution)},
        "questions": rows,
    }


def build_audit_markdown(audit: dict[str, Any], dataset: dict[str, Any]) -> str:
    metrics = dataset["graph_quality"]
    lines = [
        "# NHS WannaCry Hop-Semantics Audit",
        "",
        f"Definition: {audit['definition']}",
        "",
        "## Graph depth vs question-required reasoning depth",
        "",
        "- **Graph depth** is shortest directed distance from the benchmark graph root.",
        "- **Question-required reasoning depth** is shortest directed distance from",
        "  anchors detected in the question wording itself.",
        "- This audit measures the second quantity. Validation fails if a question does",
        "  not express its anchors, if discourse anaphora remains, if a shorter-path",
        "  entity/alias is exposed, or if `manual_reviewed` is auto-claimed.",
        "",
        "## Summary",
        "",
        f"- Preliminary shortcuts before rewrite: {audit['preliminary_shortcuts_before_rewrite']}",
        f"- Shortcuts after rewrite: {audit['shortcut_count']}",
        f"- Unresolved shortcuts after rewrite: {audit['unresolved_shortcuts']}",
        f"- Ambiguous discourse markers remaining: {audit['ambiguous_discourse_count']}",
        f"- Locality warnings: {audit['locality_warning_count']}",
        f"- Human review pending: {audit['unreviewed_count']} questions",
        f"- Entities: {metrics['entity_count']}",
        f"- Facts: {metrics['edge_count']}",
        f"- Relation types: {metrics['relation_count']}",
        f"- Root out-degree: {metrics['root_out_degree']}",
        "",
        "Human review status: all rows are `not_reviewed`; automated checks are generator-side audits only.",
        "",
        "## Hop 8-10 audit table",
        "",
        "| id | hop | anchor distance | final subject mentioned | answer mentioned | late-chain mention | locality | review | answer |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in audit["questions"]:
        if row["hop_count"] < 8:
            continue
        lines.append(
            "| {id} | {hop_count} | {shortest_distance_from_question_anchor} | "
            "{direct_final_subject_mentioned} | {expected_answer_mentioned} | "
            "{late_chain_entity_mentioned} | {locality_status} | {human_review_status} | "
            "{expected_answer} |".format(
                **row,
                locality_status=row["locality"]["status"],
            )
        )
    lines.extend(
        [
            "",
            "## Full per-question audit",
            "",
            "| id | hop | path length | anchor distance | anchor | ambiguous refs | locality | unresolved |",
            "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in audit["questions"]:
        lines.append(
            "| {id} | {hop_count} | {expected_path_length} | "
            "{shortest_distance_from_question_anchor} | {anchor} | {ambiguous} | "
            "{locality_status} | {unresolved_shortcut} |".format(
                **row,
                anchor=", ".join(row["question_anchor_entities"]),
                ambiguous=", ".join(row["ambiguous_discourse_markers"]) or "none",
                locality_status=row["locality"]["status"],
            )
        )
    warning_rows = [row for row in audit["questions"] if row["locality"]["locality_warning"]]
    lines.extend(["", "## Locality warnings", ""])
    if not warning_rows:
        lines.append("No locality warnings.")
    else:
        lines.extend(
            [
                "| id | answer | closest context sentence |",
                "| --- | --- | --- |",
            ]
        )
        for row in warning_rows:
            sentence = row["locality"]["closest_context_sentence"].replace("|", "\\|")
            lines.append(f"| {row['id']} | {row['expected_answer']} | {sentence} |")
    lines.append("")
    return "\n".join(lines)


def build_inventory(facts: list[Fact], metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "fact_inventory_id": "nhs_wannacry_fact_inventory",
        "domain": DOMAIN,
        "root_entity": ROOT_ENTITY,
        "source_manifest_path": "data/sources/nhs_wannacry/source_manifest.json",
        "created_date": date.today().isoformat(),
        "research_integrity": {
            "allowed_sources_only": True,
            "notes": (
                "Facts are drawn only from the local NAO, DHSC/CIO, CISA/US-CERT, "
                "and Microsoft MS17-010 sources listed in source_manifest.json. "
                "NHS impact counts prefer NAO where available."
            ),
        },
        "graph_quality": {
            "entity_count": metrics["entity_count"],
            "edge_count": metrics["edge_count"],
            "relation_count": metrics["relation_count"],
            "root_out_degree": metrics["root_out_degree"],
            "relations_used_at_least_twice": metrics["relations_used_at_least_twice"],
            "connected_components": metrics["connected_components"],
            "isolate_count": metrics["isolate_count"],
            "duplicate_triples": metrics["duplicate_triples"],
        },
        "facts": [fact.to_json() for fact in facts],
    }


def build_human_review_manifest() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "description": (
            "External human review manifest for NHS WannaCry hop-semantics. "
            "Entries are empty until a human reviews."
        ),
        "reviews": [],
    }


def build_artifacts() -> tuple[
    dict[str, Any],
    dict[str, Any],
    str,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    facts = build_facts()
    triples = [(fact.subject, fact.relation, fact.object) for fact in facts]
    trusted_context = trusted_context_prose()
    questions = build_questions(triples, trusted_context)
    validate_question_ids(questions)
    metrics = graph_metrics(facts, questions, trusted_context)
    validation_errors = validate_artifacts(facts, questions, metrics)
    if validation_errors:
        raise ValueError("validation failed: " + "; ".join(validation_errors))
    dataset = build_dataset(facts, questions, metrics, trusted_context)
    audit = build_audit(dataset)
    audit_markdown = build_audit_markdown(audit, dataset)
    inventory = build_inventory(facts, metrics)
    human_review = build_human_review_manifest()
    if audit["unresolved_shortcuts"] != 0:
        raise ValueError("audit contains unresolved shortcuts")
    return dataset, audit, audit_markdown, inventory, metrics, human_review


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def print_self_check(metrics: dict[str, Any], audit: dict[str, Any]) -> None:
    print("NHS WannaCry dataset self-check")
    print(f"entity_count: {metrics['entity_count']}")
    print(f"edge_count: {metrics['edge_count']}")
    print(f"relation_count: {metrics['relation_count']}")
    print(f"root_out_degree: {metrics['root_out_degree']}")
    print(f"relations_used_at_least_twice: {metrics['relations_used_at_least_twice']}")
    print(f"connected_components: {metrics['connected_components']}")
    print(f"isolate_count: {metrics['isolate_count']}")
    print(f"shortcut_count: {audit['shortcut_count']}")
    print(f"unresolved_shortcuts: {audit['unresolved_shortcuts']}")
    print(f"ambiguous_discourse_count: {audit['ambiguous_discourse_count']}")
    print(f"locality_warning_count: {audit['locality_warning_count']}")
    print(f"unreviewed_count: {audit['unreviewed_count']}")
    print("relation_multiplicity:")
    for relation, count in metrics["relation_counts"].items():
        print(f"  {relation}: {count}")
    print("hop8_10_audit:")
    print("  id                         hop  shortest  final_subject  answer  locality  unresolved")
    for row in audit["questions"]:
        if row["hop_count"] >= 8:
            print(
                "  {id:<26} {hop_count:>2}   {shortest_anchor_distance:>2}       "
                "{direct_final_subject_mentioned!s:<5}          "
                "{expected_answer_mentioned!s:<5}   {locality_status:<7}   "
                "{unresolved_shortcut!s:<5}".format(
                    **row,
                    locality_status=row["locality"]["status"],
                )
            )


def main() -> None:
    dataset, audit, audit_markdown, inventory, metrics, human_review = build_artifacts()
    write_json(DATASET_OUT, dataset)
    write_json(AUDIT_OUT, audit)
    write_text(AUDIT_MD_OUT, audit_markdown)
    write_json(HUMAN_REVIEW_OUT, human_review)
    write_json(INVENTORY_OUT, inventory)
    print_self_check(metrics, audit)


if __name__ == "__main__":
    main()
