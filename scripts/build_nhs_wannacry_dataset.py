#!/usr/bin/env python3
"""Generate the source-grounded NHS WannaCry multihop benchmark.

The generator is intentionally explicit: every graph edge is a fact with provenance,
the trusted context is natural prose, and validation checks the structural constraints
that previously caused this dataset to be rejected.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET_OUT = ROOT / "data" / "test_sets" / "nhs_wannacry_multihop_50.json"
INVENTORY_OUT = ROOT / "data" / "sources" / "nhs_wannacry" / "fact_inventory.json"
SOURCE_MANIFEST = ROOT / "data" / "sources" / "nhs_wannacry" / "source_manifest.json"

ROOT_ENTITY = "WannaCry attack on the NHS"
DOMAIN = "NHS WannaCry ransomware incident (England, May 2017)"
DATASET_ID = "nhs_wannacry_multihop_50"

NAO = "nao_wannacry_2018"
NAO_SUMMARY = "nao_wannacry_summary_2018"
DHSC = "dhsc_lessons_2018"
CISA = "cisa_ta17_132a_2017"
MS = "microsoft_ms17_010_2017"


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
        if data["parent_fact_ids"] is None:
            data["parent_fact_ids"] = []
        return data


def F(
    fact_id: str,
    subject: str,
    relation: str,
    obj: str,
    source_id: str,
    page: int | str,
    section: str,
    evidence: str,
    *,
    fact_kind: str = "direct",
    derivation_rule: str | None = None,
    parent_fact_ids: list[str] | None = None,
) -> Fact:
    return Fact(
        fact_id=fact_id,
        subject=subject,
        relation=relation,
        object=obj,
        fact_kind=fact_kind,
        source_id=source_id,
        page=page,
        section=section,
        evidence=evidence,
        derivation_rule=derivation_rule,
        parent_fact_ids=parent_fact_ids or [],
    )


def build_facts() -> list[Fact]:
    """Return a connected graph with reused, semantically meaningful relations."""

    facts: list[Fact] = []

    def add(subject: str, relation: str, obj: str, source_id: str, page: int | str, section: str, evidence: str) -> None:
        facts.append(F(f"nw_f{len(facts) + 1:03d}", subject, relation, obj, source_id, page, section, evidence))

    # Root branches. There are 12 direct root edges: enough breadth for choice,
    # but not the rejected star-shaped schema quiz.
    add(ROOT_ENTITY, "caused_by", "WannaCry ransomware", NAO_SUMMARY, 4, "Summary, paragraph 1",
        "NAO describes the 12 May 2017 incident as a global ransomware attack known as WannaCry that affected the NHS.")
    add(ROOT_ENTITY, "infected", "Majority unpatched Windows 7 devices", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NHS Digital told NAO the majority of infected NHS devices were unpatched but on supported Microsoft Windows 7.")
    add(ROOT_ENTITY, "affected", "Unsupported Windows XP minority issues", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NAO records that unsupported XP devices were in the minority of identified infection issues.")
    add(ROOT_ENTITY, "guarded_against_by", "Internet-facing firewall management", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NAO says managing firewalls facing the internet would have guarded organisations against infection whether patched or not.")
    add(ROOT_ENTITY, "spread_via", "Internet including the N3 network", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NHS Digital confirmed WannaCry spread via the internet, including the N3 network.")
    add(ROOT_ENTITY, "status_was", "No spread via NHSmail", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NHS Digital confirmed there were no instances of the ransomware spreading via NHSmail.")
    add(ROOT_ENTITY, "prepared_gap", "Department of Health", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "NAO says the Department had no formal mechanism before 12 May to assess local compliance with its cyber advice.")
    add(ROOT_ENTITY, "affected", "At least 80 of 236 trusts", NAO, 11, "Part One, paragraph 1.2",
        "NHS England data analysed by NAO showed at least 80 of 236 trusts across England were affected.")
    add(ROOT_ENTITY, "infected", "603 primary care and other NHS organisations", NAO_SUMMARY, 4, "Summary, paragraph 2",
        "NAO reports that a further 603 primary care and other NHS organisations were infected.")
    add(ROOT_ENTITY, "affected", "6912 identified cancelled appointments", NAO, 14, "Part One, paragraph 1.8",
        "NHS England identified 6,912 cancelled appointments during its incident data collection.")
    add(ROOT_ENTITY, "addressed_by", "NHS England major incident response", NAO_SUMMARY, 4, "Summary, paragraph 1",
        "At 4 pm on 12 May, NHS England declared the cyber attack a major incident and implemented emergency arrangements.")
    add(ROOT_ENTITY, "addressed_by", "WannaCry kill-switch", NAO_SUMMARY, 4, "Summary, paragraph 1",
        "On the evening of 12 May a cyber-security researcher activated a kill-switch so WannaCry stopped locking devices.")

    # Technical exploit and patch chain.
    add("WannaCry ransomware", "propagates_via", "WannaCry dropper", CISA, 1, "Technical analysis",
        "CISA describes the first WannaCry file as a dropper that contains and runs the ransomware.")
    add("WannaCry dropper", "propagates_via", "MS17-010/EternalBlue SMBv1 exploit", CISA, 1, "Technical analysis",
        "CISA says the dropper propagated via the MS17-010/EternalBlue SMBv1.0 exploit.")
    add("MS17-010/EternalBlue SMBv1 exploit", "exploits", "Microsoft SMBv1 vulnerability", CISA, 1, "Technical analysis",
        "CISA states the malware propagated by exploiting the SMBv1 vulnerability documented by Microsoft bulletin MS17-010.")
    add("MS17-010/EternalBlue SMBv1 exploit", "exploits", "Critical Windows SMB vulnerability", CISA, 1, "Overview",
        "CISA says initial reports indicated access through exploitation of a critical Windows SMB vulnerability.")
    add("Microsoft SMBv1 vulnerability", "affects", "Microsoft Windows SMBv1 server", MS, "HTML", "Executive Summary",
        "Microsoft says the vulnerabilities involved Microsoft Server Message Block 1.0 (SMBv1) server.")
    add("Microsoft Windows SMBv1 server", "status_was", "Vulnerable to remote code execution", MS, "HTML", "Executive Summary",
        "Microsoft states the most severe vulnerability could allow remote code execution.")
    add("Vulnerable to remote code execution", "caused_by", "Specially crafted SMBv1 messages", MS, "HTML", "Executive Summary",
        "Remote code execution could occur if an attacker sent specially crafted messages to an SMBv1 server.")
    add("Specially crafted SMBv1 messages", "affects", "SMBv1 crafted-request handling", MS, "HTML", "Executive Summary",
        "Microsoft says the update corrected how SMBv1 handles specially crafted requests.")
    add("SMBv1 crafted-request handling", "addressed_by", "Corrected SMBv1 request handling", MS, "HTML", "Executive Summary",
        "The security update addresses the vulnerabilities by correcting SMBv1 handling of crafted requests.")
    add("Corrected SMBv1 request handling", "addressed_by", "Microsoft Security Bulletin MS17-010", MS, "HTML", "Executive Summary",
        "Microsoft Security Bulletin MS17-010 is the security update that resolves the SMBv1 vulnerabilities.")
    add("Microsoft SMBv1 vulnerability", "addressed_by", "Microsoft Security Bulletin MS17-010", MS, "HTML", "Executive Summary",
        "MS17-010 resolves vulnerabilities in Microsoft Windows SMB Server.")
    add("Microsoft Security Bulletin MS17-010", "published_on", "14 March 2017", MS, "HTML", "Publication metadata",
        "The Microsoft bulletin states it was published on March 14, 2017.")
    add("Microsoft Security Bulletin MS17-010", "rated_as", "Critical security update", MS, "HTML", "Executive Summary",
        "Microsoft titled MS17-010 as Critical and rated the update Critical for supported Windows releases.")
    add("Microsoft Security Bulletin MS17-010", "rated_as", "Remote code execution update", MS, "HTML", "Affected Software table",
        "The affected software table repeatedly lists Critical Remote Code Execution for supported releases.")
    add("CISA TA17-132A alert", "published_on", "12 May 2017", CISA, 1, "Alert metadata",
        "The CISA/US-CERT alert is the 12 May 2017 TA17-132A WannaCry alert.")
    add("CISA TA17-132A alert", "recommended", "Apply Microsoft patch for MS17-010", CISA, 1, "Recommended Steps for Prevention",
        "CISA recommends applying the Microsoft patch for the MS17-010 SMB vulnerability dated March 14, 2017.")
    add("CISA TA17-132A alert", "recommended", "Disable SMBv1 if patch cannot be applied", CISA, 1, "Recommendations for Network Protection",
        "CISA recommends considering disabling SMBv1 if the patch cannot be applied.")
    add("CISA TA17-132A alert", "recommended", "Block SMB at the network boundary", CISA, 1, "Recommendations for Network Protection",
        "CISA recommends blocking SMB at the network boundary if patching cannot be applied.")
    add("Block SMB at the network boundary", "includes", "TCP port 445 and UDP 137-138 plus TCP 139", CISA, 1, "Recommendations for Network Protection",
        "CISA specifies blocking TCP port 445 with related UDP ports 137-138 and TCP port 139.")
    add("WannaCry dropper", "spread_via", "UDP 137-138 and TCP 139/445 scanning", CISA, 1, "Technical analysis",
        "CISA reports the dropper attempts connections using UDP 137 and 138 and TCP 139 and 445.")
    add("WannaCry dropper", "status_was", "Terminated if hard-coded URI connection succeeded", CISA, 1, "Technical analysis",
        "CISA says the dropper attempts to connect to a hard-coded URI and terminates if the connection is established.")

    # Myth-busting operating-system branch.
    add("Majority unpatched Windows 7 devices", "status_was", "Supported Microsoft Windows", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NAO records that the majority of infected devices were unpatched but on supported Microsoft Windows 7.")
    add("Majority unpatched Windows 7 devices", "addressed_by", "Microsoft Security Bulletin MS17-010", NAO, 18, "Part Two, paragraph 2.5",
        "Trusts using Windows 7 could have protected themselves by applying the March 2017 Microsoft patch.")
    add("Majority unpatched Windows 7 devices", "caused_by", "Missing March 2017 Microsoft patch", NAO, 16, "Part Two, paragraphs 2.3-2.5",
        "Infected organisations had unpatched or unsupported Windows operating systems; Windows 7 systems could have been protected by the March patch.")
    add("Unsupported Windows XP minority issues", "status_was", "Unsupported Microsoft Windows", NAO, 18, "Part Two, paragraph 2.6",
        "Microsoft was no longer releasing patches for Windows XP.")
    add("Unsupported Windows XP minority issues", "counted_as", "About 5 percent of NHS IT estate on 12 May 2017", NAO, 18, "Part Two, paragraph 2.7",
        "The Department told NAO that about 5% of the NHS IT estate still used Windows XP on 12 May 2017.")
    add("About 5 percent of NHS IT estate on 12 May 2017", "includes", "Computers and medical equipment", NAO, 18, "Part Two, paragraph 2.7",
        "The 5% Windows XP estate included computers and medical equipment.")
    add("Computers and medical equipment", "includes", "MRI scanners", NAO, 18, "Part Two, paragraph 2.6",
        "NAO cites medical equipment such as MRI scanners with Windows XP embedded.")
    add("MRI scanners", "guarded_against_by", "Isolating devices from the network", NAO, 18, "Part Two, paragraph 2.6",
        "Trusts running Windows XP on medical equipment could have protected themselves by isolating devices from the rest of the network.")
    add("Isolating devices from the network", "affected", "Manual workarounds", NAO, 18, "Part Two, paragraph 2.6",
        "NAO notes that isolating Windows XP medical equipment may necessitate manual workarounds.")
    add("Manual workarounds", "includes", "Pen and paper records", NAO, 12, "Part One, paragraph 1.5",
        "Some disrupted trusts used manual workarounds and recorded information using pen and paper.")
    add("Pen and paper records", "status_was", "Used by 46 disrupted but not infected trusts", NAO, 12, "Part One, paragraphs 1.2 and 1.5",
        "NAO describes manual workarounds in disrupted trusts and separately counts 46 affected trusts that were not infected.")
    add("Used by 46 disrupted but not infected trusts", "affected", "Shutting down devices as a precaution", NAO_SUMMARY, 7, "Key findings, paragraph 5",
        "The 46 non-infected disrupted trusts included organisations that shut down devices or systems as a precaution.")
    add("Shutting down devices as a precaution", "caused_by", "Absence of timely central advice early on 12 May", NAO, 12, "Part One, paragraph 1.4",
        "NAO says some trusts took precautionary actions on their own initiative because they had not received central advice early enough on 12 May.")
    add("Unsupported Windows XP minority issues", "guarded_against_by", "Microsoft Windows XP emergency patch after WannaCry", NAO, 18, "Part Two, paragraph 2.7",
        "Immediately after WannaCry, Microsoft issued a Windows XP patch that would prevent WannaCry and similar ransomware.")

    # Network, NHSmail, and national systems.
    add("Internet-facing firewall management", "stopped", "WannaCry infection even when unpatched", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NAO says firewall management would have guarded organisations against infection whether patched or not.")
    add("WannaCry infection even when unpatched", "affects", "Unpatched or unsupported Windows operating systems", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "All NHS organisations infected by WannaCry had unpatched or unsupported Windows operating systems.")
    add("Internet including the N3 network", "includes", "N3 network", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NAO states the internet route included the N3 network.")
    add("N3 network", "connected", "All NHS sites in England", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NAO describes N3 as the broadband network connecting all NHS sites in England.")
    add("All NHS sites in England", "includes", "Local NHS organisations", NAO, 21, "Part Three, paragraph 3.1",
        "Local health organisations connected into NHS services include trusts, GPs, CCGs and social care providers.")
    add("Local NHS organisations", "includes", "NHS trusts and GP practices", NAO, 21, "Part Three, paragraph 3.1",
        "NAO lists NHS trusts and GPs among local organisations responsible for managing cyber-security.")
    add("No spread via NHSmail", "includes", "NHSmail", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NAO says there were no instances of WannaCry spreading via NHSmail, the NHS email system.")
    add("NHSmail", "status_was", "NHS email system", NAO_SUMMARY, 10, "Lessons learned, paragraph 12",
        "NAO identifies NHSmail as the NHS email system.")
    add("National NHS IT systems managed by NHS Digital", "includes", "NHSmail", NAO, 12, "Part One, paragraph 1.6",
        "NAO gives NHSmail as an example of a national system managed by NHS Digital.")
    add("National NHS IT systems managed by NHS Digital", "includes", "NHS Spine", NAO, 12, "Part One, paragraph 1.6",
        "NAO gives the NHS Spine as an example of a national system managed by NHS Digital.")
    add("National NHS IT systems managed by NHS Digital", "status_was", "Not infected", NAO, 12, "Part One, paragraph 1.6",
        "NHS Digital told NAO that national NHS IT systems managed by NHS Digital were not infected.")
    add("NHS Spine", "status_was", "Not infected", NAO, 12, "Part One, paragraph 1.6",
        "The NHS Spine is included among national systems that NHS Digital told NAO were not infected.")
    add("NHS Spine", "status_was", "Secure demographic and clinical information service", NAO, 12, "Part One, paragraph 1.6",
        "NAO describes the Spine as holding secure demographic and clinical information.")

    # Preparedness, governance, and CareCERT.
    add("Department of Health", "lacked_before_attack", "Formal local cyber-compliance assessment mechanism", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "Before 12 May, the Department had no formal mechanism for assessing local compliance with its advice and guidance.")
    add("Department of Health", "affected", "Health-sector cyber-security resilience", NAO, 21, "Part Three, paragraph 3.1",
        "The Department has overall national responsibility for cyber-security resilience and incident response in health.")
    add("Department of Health", "coordinated_with", "NHS Digital", NAO_SUMMARY, 5, "Key findings, paragraph 1",
        "The Department and NHS England worked with NHS Digital and others to respond to the attack.")
    add("Department of Health", "coordinated_with", "NHS England", NAO_SUMMARY, 5, "Key findings, paragraph 1",
        "NAO describes the Department and NHS England working together on the response.")
    add("Department of Health", "coordinated_with", "Cabinet Office", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "The Department and Cabinet Office wrote to trusts in 2014 about migrating from old software.")
    add("Cabinet Office", "issued", "2014 Windows XP migration letter", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "The Department and Cabinet Office wrote to trusts in 2014 about robust plans to migrate away from Windows XP.")
    add("2014 Windows XP migration letter", "warned_to_apply", "Robust plans to migrate away from Windows XP", NAO, 18, "Part Two, paragraph 2.7",
        "The 2014 letter said robust plans to migrate away from old software such as Windows XP were essential.")
    add("Robust plans to migrate away from Windows XP", "counted_as", "April 2015 migration-support deadline", NAO, 18, "Part Two, paragraph 2.7",
        "The 2014 letter described temporary help until April 2015, after which there would be no support.")
    add("NHS Digital", "issued", "CareCERT alerts of March and April 2017", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "NHS Digital issued critical alerts in March and April 2017 warning organisations to patch systems to prevent WannaCry.")
    add("CareCERT alerts of March and April 2017", "warned_to_apply", "Microsoft Security Bulletin MS17-010", NAO, 18, "Part Two, paragraph 2.5",
        "The CareCERT alerts asked trusts to apply the Microsoft patch issued in March 2017.")
    add("CareCERT alerts of March and April 2017", "published_on", "17 March and 28 April 2017", NAO, 18, "Part Two, paragraph 2.5",
        "NAO records CareCERT alerts on 17 March and 28 April asking organisations to apply the patch.")
    add("CareCERT alerts of March and April 2017", "status_was", "NHS Digital CareCERT email alerts", NAO, 18, "Footnote 3",
        "NAO defines a CareCERT alert as an email from NHS Digital providing information or requiring action.")
    add("NHS Digital", "conducted", "CareCERT Assure assessments", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "Before the attack, NHS Digital had conducted on-site cyber-security assessments for trusts.")
    add("CareCERT Assure assessments", "status_was", "Voluntary on-site cyber-security inspections", NAO, 19, "Part Two, paragraph 2.11",
        "NHS Digital offered voluntary on-site CareCERT Assure inspections before the attack.")
    add("CareCERT Assure assessments", "assessed", "Hospital cyber-security", NAO, 19, "Part Two, paragraph 2.11",
        "The CareCERT Assure inspection assessed hospital cyber-security.")
    add("Voluntary on-site cyber-security inspections", "counted_as", "88 of 236 trusts", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "By 12 May, NHS Digital had inspected 88 of 236 trusts.")
    add("CareCERT Assure assessments", "counted_as", "88 of 236 trusts", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "NAO reports that NHS Digital inspected 88 of 236 trusts before the attack.")
    add("88 of 236 trusts", "status_was", "None passed", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "NAO says none of the 88 inspected trusts had passed.")
    add("None passed", "counted_as", "Before 12 May 2017", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "The none-passed result refers to assessments completed before 12 May 2017.")
    add("Before 12 May 2017", "lacked_before_attack", "Formal local cyber-compliance assessment mechanism", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "NAO states that before 12 May 2017 the Department had no formal local compliance assessment mechanism.")
    add("Formal local cyber-compliance assessment mechanism", "assessed", "CareCERT alert compliance assurance", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "The missing formal mechanism would have assessed whether organisations complied with cyber advice and guidance such as CareCERT alerts.")
    add("CareCERT alert compliance assurance", "includes", "CareCERT alerts of March and April 2017", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "The relevant advice included NHS Digital's March and April 2017 CareCERT patch alerts.")
    add("NHS Digital", "lacked_before_attack", "Power to mandate local remedial action", NAO_SUMMARY, 6, "Key findings, paragraph 4",
        "NAO says NHS Digital cannot mandate a local body to take remedial action.")
    add("NHS Digital", "issued", "High Severity CareCERT alert on 12 May 2017", DHSC, 12, "Incident chronology, footnote 35",
        "The DHSC lessons review says NHS Digital issued a High Severity CareCERT alert on 12 May.")
    add("High Severity CareCERT alert on 12 May 2017", "published_on", "12 May 2017", DHSC, 12, "Incident chronology, footnote 35",
        "The DHSC review dates the High Severity CareCERT alert to 12 May 2017.")

    # Trust, service and diagnostic impact.
    add("At least 80 of 236 trusts", "includes", "34 infected and locked-out trusts", NAO, 11, "Part One, paragraph 1.2",
        "Of the 80 affected trusts, 34 were infected and locked out of devices.")
    add("At least 80 of 236 trusts", "includes", "46 disrupted but not infected trusts", NAO, 11, "Part One, paragraph 1.2",
        "NAO separately counts 46 trusts that were not infected but reported disruption.")
    add("At least 80 of 236 trusts", "counted_as", "At least 34 percent of trusts in England", NAO_SUMMARY, 6, "Key findings, paragraph 5",
        "NAO says the attack led to disruption in at least 34% of trusts in England.")
    add("34 infected and locked-out trusts", "includes", "25 infected acute trusts", NAO, 11, "Part One, paragraph 1.2",
        "The 34 infected locked-out trusts included 25 acute trusts.")
    add("34 infected and locked-out trusts", "affected", "Locked or isolated medical devices", NAO, 11, "Part One, paragraph 1.3",
        "Infected trusts experienced medical equipment and devices being locked or isolated from IT systems.")
    add("Locked or isolated medical devices", "affected", "Radiology and pathology services", NAO, 11, "Part One, paragraph 1.3",
        "Locked or isolated medical equipment disrupted radiology and pathology departments.")
    add("Locked or isolated medical devices", "includes", "1220 diagnostic devices as of 19 May 2017", NAO, 12, "Part One, paragraph 1.3",
        "As at 19 May, NHS England had identified 1,220 infected pieces of diagnostic equipment.")
    add("1220 diagnostic devices as of 19 May 2017", "counted_as", "About 1 percent of NHS diagnostic equipment", NAO, 12, "Part One, paragraph 1.3",
        "The 1,220 infected devices were about 1% of all such NHS equipment.")
    add("46 disrupted but not infected trusts", "status_was", "Not infected", NAO, 11, "Part One, paragraph 1.2",
        "NAO explicitly distinguishes the 46 trusts as not infected but reporting disruption.")
    add("46 disrupted but not infected trusts", "affected", "Shutting down email and other systems", NAO, 12, "Part One, paragraph 1.4",
        "Some disrupted non-infected trusts shut down email and other systems as a precaution.")
    add("46 disrupted but not infected trusts", "affected", "Disconnecting from N3", NAO, 12, "Part One, paragraph 1.4",
        "NAO lists trusts disconnecting from N3 as one cause of disruption.")
    add("25 infected acute trusts", "affected", "Five acute trusts diverting emergency ambulances", NAO, 13, "Part One, paragraph 1.7",
        "Of the 25 infected acute trusts, five had to divert emergency ambulance services.")
    add("Five acute trusts diverting emergency ambulances", "includes", "Barts Health NHS Trust", NAO, 13, "Part One, paragraph 1.7",
        "Barts Health NHS Trust is one of the five listed diverting trusts.")
    add("Barts Health NHS Trust", "diverted_from_hospital", "Royal London Hospital", NAO, 13, "Part One, paragraph 1.7",
        "NAO lists Barts Health NHS Trust with Royal London Hospital.")
    add("Five acute trusts diverting emergency ambulances", "includes", "Mid Essex Hospital Services NHS Trust", NAO, 13, "Part One, paragraph 1.7",
        "Mid Essex Hospital Services NHS Trust is one of the five listed diverting trusts.")
    add("Mid Essex Hospital Services NHS Trust", "diverted_from_hospital", "Broomfield Hospital", NAO, 13, "Part One, paragraph 1.7",
        "NAO lists Mid Essex Hospital Services NHS Trust with Broomfield Hospital.")
    add("Five acute trusts diverting emergency ambulances", "includes", "East and North Hertfordshire NHS Trust", NAO, 13, "Part One, paragraph 1.7",
        "East and North Hertfordshire NHS Trust is one of the five listed diverting trusts.")
    add("East and North Hertfordshire NHS Trust", "diverted_from_hospital", "Lister Hospital", NAO, 13, "Part One, paragraph 1.7",
        "NAO lists East and North Hertfordshire NHS Trust with Lister Hospital.")
    add("Five acute trusts diverting emergency ambulances", "includes", "Hampshire Hospitals NHS Foundation Trust", NAO, 13, "Part One, paragraph 1.7",
        "Hampshire Hospitals NHS Foundation Trust is one of the five listed diverting trusts.")
    add("Hampshire Hospitals NHS Foundation Trust", "diverted_from_hospital", "Basingstoke Hospital", NAO, 13, "Part One, paragraph 1.7",
        "NAO lists Hampshire Hospitals NHS Foundation Trust with Basingstoke Hospital.")
    add("Five acute trusts diverting emergency ambulances", "includes", "North Cumbria University Hospitals NHS Trust", NAO, 13, "Part One, paragraph 1.7",
        "North Cumbria University Hospitals NHS Trust is one of the five listed diverting trusts.")
    add("North Cumbria University Hospitals NHS Trust", "diverted_from_hospital", "West Cumberland Hospital", NAO, 13, "Part One, paragraph 1.7",
        "NAO lists North Cumbria University Hospitals NHS Trust with West Cumberland Hospital.")
    add("Royal London Hospital", "affected", "Emergency ambulance services", NAO, 13, "Part One, paragraph 1.7",
        "The listed hospitals were diverting emergency ambulance services.")
    add("Broomfield Hospital", "affected", "Emergency ambulance services", NAO, 13, "Part One, paragraph 1.7",
        "The listed hospitals were diverting emergency ambulance services.")
    add("Lister Hospital", "affected", "Emergency ambulance services", NAO, 13, "Part One, paragraph 1.7",
        "The listed hospitals were diverting emergency ambulance services.")
    add("Emergency ambulance services", "affected", "Patients travelling further for emergency care", NAO, 14, "Part One, paragraph 1.10",
        "Some patients had to travel further because five hospitals diverted services.")
    add("Patients travelling further for emergency care", "status_was", "Number of diverted ambulances and patients not collected", NAO, 14, "Part One, paragraph 1.8",
        "NHS England did not collect data on how many ambulances and patients were diverted.")
    add("Number of diverted ambulances and patients not collected", "status_was", "Department and NHS England did not know full diversion count", NAO_SUMMARY, 8, "Key findings, paragraph 6",
        "NAO says neither the Department nor NHS England knew how many ambulances and patients were diverted.")

    # Cancellation branch.
    add("6912 identified cancelled appointments", "counted_as", "NHS England identified cancellations", NAO, 14, "Part One, paragraph 1.8",
        "NHS England identified that 6,912 appointments had been cancelled.")
    add("NHS England identified cancellations", "estimated_as", "About 19494 estimated cancellations", NAO, 14, "Part One, paragraph 1.8",
        "NHS England estimated the total number of cancelled appointments as around 19,494.")
    add("About 19494 estimated cancellations", "estimated_as", "Normal follow-up-to-first appointment rate", NAO, 14, "Part One, paragraph 1.8",
        "The estimate was based on the normal rate of follow-up appointments to first appointments.")
    add("Normal follow-up-to-first appointment rate", "status_was", "Estimate basis for total cancellations", NAO, 14, "Part One, paragraph 1.8",
        "NAO identifies the normal follow-up to first appointment rate as the basis for the cancellation estimate.")
    add("Estimate basis for total cancellations", "includes", "Repeat outpatient appointments", NAO, 14, "Part One, paragraph 1.8",
        "NAO says the initial 6,912 figure did not include repeat outpatient appointments.")
    add("Repeat outpatient appointments", "status_was", "Excluded from initial 6912 collection", NAO, 14, "Part One, paragraph 1.8",
        "Repeat outpatient appointments were excluded from the initial 6,912 count.")
    add("Excluded from initial 6912 collection", "includes", "Cancellations identified after 18 May", NAO, 14, "Part One, paragraph 1.8",
        "The initial 6,912 figure also excluded cancellations identified after 18 May.")
    add("Cancellations identified after 18 May", "status_was", "Also excluded from initial 6912 collection", NAO, 14, "Part One, paragraph 1.8",
        "Cancellations identified after 18 May were also outside the initial 6,912 count.")
    add("Also excluded from initial 6912 collection", "counted_as", "Actual cancelled-appointment number not planned for identification", NAO, 14, "Part One, paragraph 1.8",
        "NHS England told NAO it did not plan to identify the actual cancellation number.")
    add("6912 identified cancelled appointments", "includes", "Cancelled patient operations", NAO_SUMMARY, 7, "Figure 1",
        "NAO's summary figure notes the identified cancelled appointments included cancelled patient operations.")
    add("NHS England identified cancellations", "includes", "At least 139 urgent cancer referrals by 18 May", NAO, 14, "Part One, paragraph 1.10",
        "NHS England identified at least 139 urgent referrals for potential cancer cancelled as at 18 May.")

    # Primary care recovery branch.
    add("603 primary care and other NHS organisations", "includes", "595 GP practices", NAO_SUMMARY, 4, "Summary, paragraph 2",
        "The 603 infected primary care and other organisations included 595 GP practices.")
    add("595 GP practices", "affected", "Machines rebuilt before patching", DHSC, 12, "Incident chronology, paragraph 2.14",
        "The DHSC review says 595 infected practices needed machines rebuilt before they were patched.")
    add("Machines rebuilt before patching", "addressed_by", "Re-installation and patching by IT delivery partners", DHSC, 12, "Incident chronology, paragraph 2.14",
        "Commissioning Support Units and other IT delivery partners worked with NHS England and NHS Digital to re-install and patch primary-care systems.")
    add("Re-installation and patching by IT delivery partners", "status_was", "95 percent complete by 17 May 2017", DHSC, 12, "Incident chronology, paragraph 2.14",
        "The DHSC review says 95% of infected practices were re-installed and patched by 17 May.")
    add("95 percent complete by 17 May 2017", "status_was", "Remaining 5 percent completed by Friday 19 May 2017", DHSC, 12, "Incident chronology, paragraph 2.14",
        "The remaining 5% were completed by Friday 19 May when the incident was stood down.")
    add("Remaining 5 percent completed by Friday 19 May 2017", "stood_down_on", "Friday 19 May 2017", DHSC, 12, "Incident chronology, paragraph 2.14",
        "The remaining primary-care patching was completed by Friday 19 May when the incident was stood down.")
    add("Friday 19 May 2017", "stood_down_on", "Incident stood down at 5:30 pm", NAO, 15, "Part One, paragraph 1.13 and Figure 2",
        "NAO Figure 2 records the incident being stood down at 5:30 pm on Friday 19 May.")
    add("Incident stood down at 5:30 pm", "status_was", "NHS England stand-down decision", NAO, 15, "Part One, paragraph 1.13 and Figure 2",
        "NAO records NHS England standing down the incident on Friday 19 May.")
    add("NHS England stand-down decision", "counted_as", "One-week incident period from 12 May to 19 May 2017", DHSC, 10, "Incident chronology, paragraph 2.7",
        "The DHSC review says the incident lasted a week, from 16:00 on 12 May to 17:30 on 19 May.")
    add("Re-installation and patching by IT delivery partners", "coordinated_with", "Commissioning Support Units", DHSC, 12, "Incident chronology, paragraph 2.14",
        "The DHSC review names Commissioning Support Units among IT delivery partners involved in primary-care remediation.")

    # Incident response, kill-switch, recovery, ransom and post-incident actions.
    add("NHS England major incident response", "declared_at", "4:00 pm on 12 May 2017", NAO_SUMMARY, 4, "Summary, paragraph 1",
        "At 4 pm on 12 May, NHS England declared the cyber attack a major incident.")
    add("4:00 pm on 12 May 2017", "status_was", "National major incident declaration", DHSC, 10, "Incident chronology, paragraph 2.7",
        "The DHSC review says the incident was formally stood up at 16:00 on 12 May.")
    add("NHS England major incident response", "activated", "Emergency Preparedness Resilience and Response plans", NAO_SUMMARY, 9, "Key findings, paragraph 10",
        "NAO says NHS England initiated EPRR plans at 6:45 pm to act as the single point of coordination.")
    add("Emergency Preparedness Resilience and Response plans", "declared_at", "6:45 pm on 12 May 2017", NAO_SUMMARY, 9, "Key findings, paragraph 10",
        "NAO records NHS England initiating EPRR plans at 6:45 pm on 12 May.")
    add("NHS England major incident response", "coordinated_with", "NHS Digital", NAO, 13, "Figure 2 timeline",
        "Figure 2 says NHS England led the response, coordinating particularly with NHS Digital.")
    add("NHS England major incident response", "coordinated_with", "Department of Health", NAO_SUMMARY, 5, "Key findings, paragraph 1",
        "NAO says the Department and NHS England worked together on the response.")
    add("NHS England major incident response", "coordinated_with", "National Cyber Security Centre", NAO_SUMMARY, 5, "Key findings, paragraph 1",
        "NAO lists the National Cyber Security Centre among organisations involved in the response.")
    add("NHS England major incident response", "coordinated_with", "National Crime Agency", NAO_SUMMARY, 7, "Key findings, paragraph 7",
        "The Department, NHS England and the National Crime Agency told NAO no NHS organisation paid the ransom.")
    add("NHS England major incident response", "coordinated_with", "NHS Improvement", NAO_SUMMARY, 5, "Key findings, paragraph 1",
        "NAO lists NHS Improvement among organisations involved in the response.")
    add("NHS England major incident response", "issued", "14 May anti-ransom letter", NAO_SUMMARY, 7, "Key findings, paragraph 7",
        "NHS Digital wrote to all trusts on 14 May advising against ransom payments.")
    add("14 May anti-ransom letter", "warned_to_apply", "Do not pay the WannaCry ransom", NAO_SUMMARY, 7, "Key findings, paragraph 7",
        "The 14 May letter advised against paying ransoms.")
    add("NHS England major incident response", "status_was", "No NHS ransom paid", NAO_SUMMARY, 7, "Key findings, paragraph 7",
        "The Department, NHS England and the National Crime Agency told NAO no NHS organisation paid the ransom.")
    add("WannaCry kill-switch", "status_was", "Activated evening of 12 May 2017", NAO_SUMMARY, 4, "Summary, paragraph 1",
        "A cyber-security researcher activated the kill-switch on the evening of 12 May.")
    add("Cyber-security researcher", "activated", "WannaCry kill-switch", NAO_SUMMARY, 8, "Key findings, paragraph 8",
        "NAO says a cyber-security researcher activated the kill-switch.")
    add("WannaCry kill-switch", "stopped", "Further WannaCry device locking", NAO_SUMMARY, 4, "Summary, paragraph 1",
        "The kill-switch meant WannaCry stopped locking devices.")
    add("WannaCry kill-switch", "stopped", "Further malware spread", DHSC, 10, "Incident chronology, paragraph 2.4",
        "The DHSC review says the kill-switch had the effect of stopping WannaCry infecting further devices.")
    add("Further WannaCry device locking", "affected", "NHS service recovery", NAO_SUMMARY, 8, "Key findings, paragraph 8",
        "NAO says the researcher's action meant infected organisations were not locked out and the attack could have caused more disruption otherwise.")
    add("NHS service recovery", "status_was", "Only Lister and Broomfield still diverting by 16 May 2017", NAO, 15, "Part One, paragraph 1.13",
        "By Tuesday 16 May, only Lister Hospital and Broomfield Hospital were still diverting patients.")
    add("Only Lister and Broomfield still diverting by 16 May 2017", "includes", "Lister Hospital", NAO, 15, "Part One, paragraph 1.13",
        "NAO names Lister Hospital as one of the two hospitals still diverting on 16 May.")
    add("Only Lister and Broomfield still diverting by 16 May 2017", "includes", "Broomfield Hospital", NAO, 15, "Part One, paragraph 1.13",
        "NAO names Broomfield Hospital as one of the two hospitals still diverting on 16 May.")
    add("NHS England major incident response", "stood_down_on", "Friday 19 May 2017", NAO, 15, "Part One, paragraph 1.13",
        "NHS England stood down the incident on Friday 19 May.")
    add("NHS England major incident response", "issued", "Post-attack board assurance request", NAO_SUMMARY, 10, "Lessons learned, paragraph 14",
        "After WannaCry, NHS England and NHS Improvement wrote to boards seeking assurance on CareCERT alerts and firewall action.")
    add("Post-attack board assurance request", "warned_to_apply", "39 CareCERT alerts from March to May 2017", NAO_SUMMARY, 10, "Lessons learned, paragraph 14",
        "The post-attack request asked boards to implement all 39 CareCERT alerts issued between March and May 2017.")
    add("Post-attack board assurance request", "warned_to_apply", "Essential local firewall securing actions", NAO_SUMMARY, 10, "Lessons learned, paragraph 14",
        "The post-attack request also asked boards to take essential action to secure local firewalls.")
    add("Department of Health", "prepared_gap", "Tested national cyber-attack response plan", NAO_SUMMARY, 10, "Lessons learned, paragraph 14",
        "NAO identifies a lesson to develop and test a cyber-attack response plan with clear national and local roles.")
    add("Tested national cyber-attack response plan", "addressed_by", "Clear national and local response roles", NAO_SUMMARY, 10, "Lessons learned, paragraph 14",
        "The lesson was to have a response plan setting out clear roles and responsibilities for national and local organisations.")
    add("Department of Health", "prepared_gap", "Assurance that critical CareCERT alerts were implemented", NAO_SUMMARY, 10, "Lessons learned, paragraph 14",
        "NAO lists the need to ensure organisations implement critical CareCERT alerts, including patches.")

    return facts


def trusted_context_prose() -> str:
    """Natural-language context covering every fact without fact IDs or schema keys."""

    return (
        "On Friday 12 May 2017, a global ransomware campaign known as WannaCry affected the NHS in England, "
        "although the NHS was not the specific target. The National Audit Office described WannaCry as the "
        "largest cyber attack to affect the NHS in England. It encrypted data on infected computers and "
        "demanded ransom payments, but the Department of Health, NHS England and the National Crime Agency "
        "told the NAO that no NHS organisation paid the ransom. NHS Digital also advised against paying, "
        "including in a letter to trusts on 14 May. At 4:00 pm on 12 May, NHS England declared a national "
        "major incident; at 6:45 pm it initiated Emergency Preparedness, Resilience and Response arrangements "
        "to coordinate the response, especially with NHS Digital. The Department of Health, the National Cyber "
        "Security Centre, the National Crime Agency and NHS Improvement were also involved. The incident lasted "
        "for the week from 12 May to 19 May 2017 and was stood down by NHS England at 5:30 pm on Friday "
        "19 May.\n\n"
        "The technical route was the Windows SMB weakness addressed by Microsoft Security Bulletin MS17-010. "
        "CISA/US-CERT described a WannaCry dropper that contained and ran the ransomware, attempted network "
        "connections on UDP ports 137 and 138 and TCP ports 139 and 445, and propagated using the "
        "MS17-010/EternalBlue SMBv1.0 exploit. That exploit targeted a critical Windows SMBv1 vulnerability. "
        "Microsoft explained that the vulnerability affected Microsoft Windows SMBv1 server handling and could "
        "allow remote code execution when an attacker sent specially crafted SMBv1 messages. The correction was "
        "to fix how SMBv1 handled those crafted requests. Microsoft published MS17-010 on 14 March 2017 and "
        "rated it Critical, including for remote code execution. CISA's 12 May alert recommended applying the "
        "MS17-010 patch; if patching could not be applied, it recommended disabling SMBv1 or blocking SMB at "
        "the network boundary, including TCP port 445 and related UDP 137-138 and TCP 139. CISA also recorded "
        "that the dropper terminated if a connection to its hard-coded URI succeeded.\n\n"
        "The operating-system story is often misunderstood. NHS Digital told the NAO that the majority of "
        "infected NHS devices were unpatched but still on supported Microsoft Windows 7. Trusts using Windows 7 "
        "could have protected themselves by applying the March 2017 Microsoft patch. Unsupported Windows XP "
        "devices were only a minority of identified issues. Microsoft was no longer releasing normal XP patches, "
        "but the Department told the NAO that about five percent of the NHS IT estate, including computers and "
        "medical equipment, still used Windows XP on 12 May. Some medical equipment, such as MRI scanners, had "
        "Windows XP embedded; such equipment could have been protected by isolation from the network, although "
        "isolation could require manual workarounds. Some disrupted trusts used pen and paper records for tasks "
        "normally done electronically. After WannaCry, Microsoft issued an emergency Windows XP patch that would "
        "prevent WannaCry and similar ransomware.\n\n"
        "NHS Digital said WannaCry spread via the internet, including the N3 network, the broadband network "
        "connecting NHS sites in England. It confirmed there were no instances of spread via NHSmail, the NHS "
        "email system. National NHS IT systems managed by NHS Digital were not infected. Those national systems "
        "included NHSmail and the NHS Spine; the Spine held secure demographic and clinical information. The NAO "
        "also recorded that managing firewalls facing the internet would have guarded organisations against "
        "infection whether or not their systems had been patched, because all infected NHS organisations had "
        "unpatched or unsupported Windows operating systems.\n\n"
        "The preparedness gap sat with the Department of Health's national responsibilities and the limits of "
        "local assurance. The Department had overall national responsibility for health-sector cyber-security "
        "resilience, while management was devolved to local organisations such as NHS trusts and GP practices. "
        "Before 12 May 2017 there was no formal mechanism to assess whether local NHS organisations had complied "
        "with cyber advice and guidance, including CareCERT alerts. The Department and Cabinet Office had written "
        "to trusts in 2014 that robust plans to migrate away from old software such as Windows XP were essential, "
        "with April 2015 marking the end of temporary support. NHS Digital issued CareCERT email alerts in March "
        "and April 2017, specifically on 17 March and 28 April, asking organisations to apply the Microsoft patch. "
        "NHS Digital also offered voluntary on-site CareCERT Assure inspections to assess hospital cyber-security. "
        "By 12 May, 88 of 236 trusts had been inspected and none had passed. NHS Digital could not mandate local "
        "remedial action. During the incident it issued a High Severity CareCERT alert on 12 May. After the attack, "
        "lessons included testing a national cyber-attack response plan with clear national and local roles and "
        "assuring implementation of critical CareCERT alerts.\n\n"
        "The impact counts must remain separate. At least 80 of 236 trusts were affected, representing at least "
        "34 percent of trusts in England. Of those, 34 were infected and locked out of devices, including 25 acute "
        "trusts, while 46 were not infected but still reported disruption. Some of the non-infected disrupted "
        "trusts shut down email or other systems, disconnected from N3, or acted on their own initiative because "
        "central advice had not arrived early enough on 12 May. In infected trusts, locked or isolated medical "
        "devices disrupted radiology and pathology services; as at 19 May, NHS England had identified 1,220 "
        "infected diagnostic devices, about one percent of such NHS equipment. Separately, 603 primary care and "
        "other NHS organisations were infected, including 595 GP practices. Those practices needed machines "
        "rebuilt before patching. Commissioning Support Units and other IT delivery partners worked with NHS "
        "England and NHS Digital on re-installation and patching; 95 percent of infected practices were complete "
        "by 17 May and the remaining five percent by Friday 19 May.\n\n"
        "Five of the infected acute trusts had to divert emergency ambulance services. They were Barts Health NHS "
        "Trust at Royal London Hospital, Mid Essex Hospital Services NHS Trust at Broomfield Hospital, East and "
        "North Hertfordshire NHS Trust at Lister Hospital, Hampshire Hospitals NHS Foundation Trust at Basingstoke "
        "Hospital, and North Cumbria University Hospitals NHS Trust at West Cumberland Hospital. Emergency ambulance "
        "diversions meant some patients travelled further for emergency care. NHS England did not collect data on "
        "how many ambulances and patients were diverted, so neither the Department nor NHS England knew the full "
        "diversion count. By Tuesday 16 May only Lister Hospital and Broomfield Hospital were still diverting.\n\n"
        "Appointments and operations were also disrupted. NHS England identified 6,912 cancelled appointments, "
        "including cancelled patient operations, but that initial collection did not include repeat outpatient "
        "appointments or cancellations identified after 18 May. It estimated about 19,494 cancellations in total "
        "using the normal rate of follow-up appointments to first appointments, but told the NAO it did not plan "
        "to identify the actual number. NHS England also identified at least 139 urgent referrals for potential "
        "cancer cancelled as at 18 May. On the evening of 12 May, a cyber-security researcher activated the WannaCry "
        "kill-switch. The kill-switch stopped further device locking and further malware spread, aiding NHS service "
        "recovery. Afterward, NHS England and NHS Improvement wrote to boards asking them to implement all 39 "
        "CareCERT alerts issued from March to May 2017 and to take essential local firewall-securing action."
    )


def chain_definitions() -> dict[str, list[list[str]]]:
    """Five independent 10-hop chains used to create balanced questions."""

    R = ROOT_ENTITY
    return {
        "technical exploit and patch": [
            [R, "caused_by", "WannaCry ransomware"],
            ["WannaCry ransomware", "propagates_via", "WannaCry dropper"],
            ["WannaCry dropper", "propagates_via", "MS17-010/EternalBlue SMBv1 exploit"],
            ["MS17-010/EternalBlue SMBv1 exploit", "exploits", "Microsoft SMBv1 vulnerability"],
            ["Microsoft SMBv1 vulnerability", "affects", "Microsoft Windows SMBv1 server"],
            ["Microsoft Windows SMBv1 server", "status_was", "Vulnerable to remote code execution"],
            ["Vulnerable to remote code execution", "caused_by", "Specially crafted SMBv1 messages"],
            ["Specially crafted SMBv1 messages", "affects", "SMBv1 crafted-request handling"],
            ["SMBv1 crafted-request handling", "addressed_by", "Corrected SMBv1 request handling"],
            ["Corrected SMBv1 request handling", "addressed_by", "Microsoft Security Bulletin MS17-010"],
        ],
        "Windows XP myth-busting": [
            [R, "affected", "Unsupported Windows XP minority issues"],
            ["Unsupported Windows XP minority issues", "counted_as", "About 5 percent of NHS IT estate on 12 May 2017"],
            ["About 5 percent of NHS IT estate on 12 May 2017", "includes", "Computers and medical equipment"],
            ["Computers and medical equipment", "includes", "MRI scanners"],
            ["MRI scanners", "guarded_against_by", "Isolating devices from the network"],
            ["Isolating devices from the network", "affected", "Manual workarounds"],
            ["Manual workarounds", "includes", "Pen and paper records"],
            ["Pen and paper records", "status_was", "Used by 46 disrupted but not infected trusts"],
            ["Used by 46 disrupted but not infected trusts", "affected", "Shutting down devices as a precaution"],
            ["Shutting down devices as a precaution", "caused_by", "Absence of timely central advice early on 12 May"],
        ],
        "cancelled appointments": [
            [R, "affected", "6912 identified cancelled appointments"],
            ["6912 identified cancelled appointments", "counted_as", "NHS England identified cancellations"],
            ["NHS England identified cancellations", "estimated_as", "About 19494 estimated cancellations"],
            ["About 19494 estimated cancellations", "estimated_as", "Normal follow-up-to-first appointment rate"],
            ["Normal follow-up-to-first appointment rate", "status_was", "Estimate basis for total cancellations"],
            ["Estimate basis for total cancellations", "includes", "Repeat outpatient appointments"],
            ["Repeat outpatient appointments", "status_was", "Excluded from initial 6912 collection"],
            ["Excluded from initial 6912 collection", "includes", "Cancellations identified after 18 May"],
            ["Cancellations identified after 18 May", "status_was", "Also excluded from initial 6912 collection"],
            ["Also excluded from initial 6912 collection", "counted_as", "Actual cancelled-appointment number not planned for identification"],
        ],
        "primary-care recovery": [
            [R, "infected", "603 primary care and other NHS organisations"],
            ["603 primary care and other NHS organisations", "includes", "595 GP practices"],
            ["595 GP practices", "affected", "Machines rebuilt before patching"],
            ["Machines rebuilt before patching", "addressed_by", "Re-installation and patching by IT delivery partners"],
            ["Re-installation and patching by IT delivery partners", "status_was", "95 percent complete by 17 May 2017"],
            ["95 percent complete by 17 May 2017", "status_was", "Remaining 5 percent completed by Friday 19 May 2017"],
            ["Remaining 5 percent completed by Friday 19 May 2017", "stood_down_on", "Friday 19 May 2017"],
            ["Friday 19 May 2017", "stood_down_on", "Incident stood down at 5:30 pm"],
            ["Incident stood down at 5:30 pm", "status_was", "NHS England stand-down decision"],
            ["NHS England stand-down decision", "counted_as", "One-week incident period from 12 May to 19 May 2017"],
        ],
        "preparedness and CareCERT": [
            [R, "prepared_gap", "Department of Health"],
            ["Department of Health", "coordinated_with", "NHS Digital"],
            ["NHS Digital", "conducted", "CareCERT Assure assessments"],
            ["CareCERT Assure assessments", "status_was", "Voluntary on-site cyber-security inspections"],
            ["Voluntary on-site cyber-security inspections", "counted_as", "88 of 236 trusts"],
            ["88 of 236 trusts", "status_was", "None passed"],
            ["None passed", "counted_as", "Before 12 May 2017"],
            ["Before 12 May 2017", "lacked_before_attack", "Formal local cyber-compliance assessment mechanism"],
            ["Formal local cyber-compliance assessment mechanism", "assessed", "CareCERT alert compliance assurance"],
            ["CareCERT alert compliance assurance", "includes", "CareCERT alerts of March and April 2017"],
        ],
    }


QUESTION_TEXT: dict[str, list[str]] = {
    "technical exploit and patch": [
        "What malware caused the May 2017 NHS cyber attack?",
        "Which WannaCry component did the ransomware propagate through in CISA's analysis?",
        "Which exploit did the WannaCry dropper use to propagate?",
        "Which vulnerability did the MS17-010/EternalBlue SMBv1 exploit target?",
        "Which Microsoft server component was affected by that SMBv1 vulnerability?",
        "What severe outcome was the Microsoft Windows SMBv1 server vulnerable to?",
        "What attacker input could lead to remote code execution against the SMBv1 server?",
        "What handling path was affected by specially crafted SMBv1 messages?",
        "What correction addressed the crafted-request handling problem?",
        "Which Microsoft bulletin supplied the corrected SMBv1 request handling?",
    ],
    "Windows XP myth-busting": [
        "What did NAO describe as the minority Windows XP issue, rather than the majority infection story?",
        "What share of the NHS IT estate did those Windows XP issues represent on 12 May 2017?",
        "What kinds of assets were included in that five-percent Windows XP estate?",
        "Which medical equipment example did NAO give for Windows XP embedded in equipment?",
        "What network measure could protect those MRI scanners with embedded Windows XP?",
        "What operational workaround could isolation of those devices require?",
        "What record-keeping method appeared in those manual workarounds?",
        "Which disrupted group used such pen-and-paper workarounds while not being infected?",
        "What precautionary action did those disrupted but non-infected trusts take?",
        "What missing early input contributed to trusts shutting devices down as a precaution?",
    ],
    "cancelled appointments": [
        "How many cancelled appointments did NHS England identify during the incident collection?",
        "What did the 6,912 figure represent in NHS England's collection?",
        "What total cancellation figure did NHS England estimate from the identified cancellations?",
        "What rate did NHS England use to estimate around 19,494 cancellations?",
        "What role did the normal follow-up-to-first appointment rate play?",
        "Which appointment category was included among the exclusions from the initial count?",
        "How were repeat outpatient appointments treated in the initial 6,912 collection?",
        "What later cancellations were also excluded from the initial 6,912 collection?",
        "How were cancellations identified after 18 May treated in the initial collection?",
        "What did NHS England not plan to identify after those exclusions?",
    ],
    "primary-care recovery": [
        "How many primary care and other NHS organisations were infected?",
        "How many GP practices were included in the 603 infected primary-care and other organisations?",
        "What did the 595 infected GP practices need before patching?",
        "What remediation work addressed machines that needed rebuilding before patching?",
        "What was the completion status of that re-installation and patching by 17 May?",
        "What remained to be completed by Friday 19 May?",
        "On what date was the remaining five percent complete as the incident was stood down?",
        "What stand-down time is attached to Friday 19 May 2017?",
        "Whose decision was the 5:30 pm incident stand-down?",
        "What one-week incident period did the NHS England stand-down close?",
    ],
    "preparedness and CareCERT": [
        "Which national department is the starting point for the pre-attack preparedness gap?",
        "Which digital body worked with the Department of Health in the response and assurance context?",
        "What assessment programme did NHS Digital conduct before the attack?",
        "What kind of inspections were the CareCERT Assure assessments?",
        "How many trusts had received those voluntary on-site inspections before the attack?",
        "What was the pass result for those 88 inspected trusts?",
        "Before what date did the none-passed result apply?",
        "What formal mechanism was missing before 12 May 2017?",
        "What kind of assurance would that formal mechanism have assessed?",
        "Which March-April 2017 alerts were covered by that compliance-assurance gap?",
    ],
}


def make_question(qid: str, hop: int, question: str, path: list[list[str]], chain_name: str) -> dict[str, Any]:
    entities = sorted({node for edge in path for node in (edge[0], edge[2])})
    relations = sorted({edge[1] for edge in path})
    return {
        "id": qid,
        "hop_count": hop,
        "question": question,
        "answer": path[-1][2],
        "expected_answer": path[-1][2],
        "expected_path": path,
        "required_entities": entities,
        "required_relations": relations,
        "difficulty_notes": f"{hop}-hop path through the {chain_name} branch; answer is the path terminus.",
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
            "requires_temporal_anchor": any("2017" in part or "May" in part for edge in path for part in edge),
            "requires_count_distinction": any(any(ch.isdigit() for ch in part) for edge in path for part in edge),
        },
    }


def build_questions() -> list[dict[str, Any]]:
    chains = chain_definitions()
    chain_order = [
        "technical exploit and patch",
        "Windows XP myth-busting",
        "cancelled appointments",
        "primary-care recovery",
        "preparedness and CareCERT",
    ]
    questions: list[dict[str, Any]] = []
    for hop in range(1, 11):
        for idx, chain_name in enumerate(chain_order, start=1):
            path = chains[chain_name][:hop]
            question = QUESTION_TEXT[chain_name][hop - 1]
            questions.append(make_question(f"nhs_wannacry_h{hop:02d}_q{idx:02d}", hop, question, path, chain_name))
    return questions


def graph_metrics(facts: list[Fact], questions: list[dict[str, Any]], trusted_context: str) -> dict[str, Any]:
    triples = [(f.subject, f.relation, f.object) for f in facts]
    entities = sorted({node for s, _, o in triples for node in (s, o)})
    relation_counts = Counter(r for _, r, _ in triples)

    neighbors: dict[str, set[str]] = defaultdict(set)
    for s, _, o in triples:
        neighbors[s].add(o)
        neighbors[o].add(s)

    seen: set[str] = set()
    components = 0
    for entity in entities:
        if entity in seen:
            continue
        components += 1
        queue: deque[str] = deque([entity])
        seen.add(entity)
        while queue:
            current = queue.popleft()
            for nxt in neighbors[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)

    hop_distribution = Counter(q["hop_count"] for q in questions)
    path_errors = validate_paths(facts, questions)
    duplicate_triples = len(triples) - len(set(triples))
    direct_missing_provenance = [
        f.fact_id
        for f in facts
        if f.fact_kind == "direct" and (not f.source_id or f.page in ("", None) or not f.section or not f.evidence)
    ]
    derived = [f for f in facts if f.fact_kind == "derived"]
    isolates = [entity for entity in entities if not neighbors[entity]]
    hop10_first_edges = {tuple(q["expected_path"][0]) for q in questions if q["hop_count"] == 10}

    return {
        "entity_count": len(entities),
        "edge_count": len(facts),
        "relation_count": len(relation_counts),
        "root_out_degree": sum(1 for f in facts if f.subject == ROOT_ENTITY),
        "relation_counts": dict(sorted(relation_counts.items())),
        "relations_used_at_least_twice": sum(1 for count in relation_counts.values() if count >= 2),
        "hop_distribution": dict(sorted(hop_distribution.items())),
        "connected_components": components,
        "isolate_count": len(isolates),
        "duplicate_triples": duplicate_triples,
        "derived_fact_count": len(derived),
        "direct_facts_missing_provenance": direct_missing_provenance,
        "hop10_distinct_first_edges": len(hop10_first_edges),
        "path_validation_errors": path_errors,
        "trusted_context_contains_nw_f": "nw_f" in trusted_context,
        "trusted_context_contains_fact_id": "fact_id" in trusted_context,
    }


def validate_paths(facts: list[Fact], questions: list[dict[str, Any]]) -> list[str]:
    edge_set = {(f.subject, f.relation, f.object) for f in facts}
    errors: list[str] = []
    for q in questions:
        path = q["expected_path"]
        if len(path) != q["hop_count"]:
            errors.append(f"{q['id']}: hop_count {q['hop_count']} but path length {len(path)}")
        if not path or path[0][0] != ROOT_ENTITY:
            errors.append(f"{q['id']}: path does not start at root")
        for idx, edge in enumerate(path):
            triple = tuple(edge)
            if triple not in edge_set:
                errors.append(f"{q['id']}: edge {idx + 1} missing from fact graph: {triple}")
            if idx and path[idx - 1][2] != edge[0]:
                errors.append(f"{q['id']}: edge {idx + 1} is not contiguous with prior edge")
        if path and (q["answer"] != path[-1][2] or q["expected_answer"] != path[-1][2]):
            errors.append(f"{q['id']}: answer is not path terminus")
    return errors


def validate_dataset(facts: list[Fact], questions: list[dict[str, Any]], trusted_context: str) -> dict[str, Any]:
    metrics = graph_metrics(facts, questions, trusted_context)
    errors: list[str] = []

    if not (45 <= metrics["entity_count"]):
        errors.append("expected at least 45 entities")
    if not (55 <= metrics["edge_count"]):
        errors.append("expected at least 55 facts")
    if not (15 <= metrics["relation_count"] <= 30):
        errors.append("expected 15-30 distinct relations")
    if metrics["relations_used_at_least_twice"] <= metrics["relation_count"] // 2:
        errors.append("expected most relation types to be reused")
    if metrics["connected_components"] != 1:
        errors.append("expected exactly one connected component")
    if metrics["isolate_count"] != 0:
        errors.append("expected no isolate entities")
    if metrics["duplicate_triples"] != 0:
        errors.append("expected no duplicate triples")
    if not (6 <= metrics["root_out_degree"] <= 12):
        errors.append("expected root out-degree between 6 and 12")
    if metrics["derived_fact_count"] > 5:
        errors.append("expected at most 5 derived facts")
    if metrics["direct_facts_missing_provenance"]:
        errors.append("direct facts missing provenance")
    if len(questions) != 50:
        errors.append("expected exactly 50 questions")
    expected_hops = {hop: 5 for hop in range(1, 11)}
    if metrics["hop_distribution"] != expected_hops:
        errors.append("expected exactly five questions for each hop 1-10")
    expected_ids = [f"nhs_wannacry_h{hop:02d}_q{idx:02d}" for hop in range(1, 11) for idx in range(1, 6)]
    actual_ids = [q["id"] for q in questions]
    if actual_ids != expected_ids:
        errors.append("question IDs are not the required ordered sequence")
    if metrics["hop10_distinct_first_edges"] < 2:
        errors.append("expected at least two distinct first edges among hop-10 questions")
    if metrics["path_validation_errors"]:
        errors.append("path validation errors present")
    if metrics["trusted_context_contains_nw_f"] or metrics["trusted_context_contains_fact_id"]:
        errors.append("trusted_context contains forbidden fact-id markers")

    metrics["validation_errors"] = errors
    return metrics


def build_dataset(facts: list[Fact], questions: list[dict[str, Any]], trusted_context: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_set_id": DATASET_ID,
        "domain": DOMAIN,
        "root_entity": ROOT_ENTITY,
        "description": (
            "Source-grounded 50-question multihop set on the documented May 2017 WannaCry "
            "impact on the NHS in England, regenerated with reused relation types and natural trusted context."
        ),
        "source_manifest_path": "data/sources/nhs_wannacry/source_manifest.json",
        "trusted_context": trusted_context,
        "expected_graph_facts": [fact.to_json() for fact in facts],
        "graph_quality": {
            "entity_count": metrics["entity_count"],
            "edge_count": metrics["edge_count"],
            "relation_count": metrics["relation_count"],
            "root_out_degree": metrics["root_out_degree"],
            "relations_used_at_least_twice": metrics["relations_used_at_least_twice"],
            "connected_components": metrics["connected_components"],
            "isolate_count": metrics["isolate_count"],
            "duplicate_triples": metrics["duplicate_triples"],
            "hop10_distinct_first_edges": metrics["hop10_distinct_first_edges"],
        },
        "questions": questions,
    }


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
                "Facts are drawn only from the local NAO, DHSC/CIO, CISA/US-CERT, and Microsoft MS17-010 "
                "sources listed in source_manifest.json. NHS impact counts prefer NAO where available."
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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_self_check(metrics: dict[str, Any]) -> None:
    print("NHS WannaCry dataset self-check")
    print(f"entity_count: {metrics['entity_count']}")
    print(f"edge_count: {metrics['edge_count']}")
    print(f"relation_count: {metrics['relation_count']}")
    print(f"root_out_degree: {metrics['root_out_degree']}")
    print(f"relations_used_at_least_twice: {metrics['relations_used_at_least_twice']}")
    print("relation_multiplicity:")
    for relation, count in metrics["relation_counts"].items():
        print(f"  {relation}: {count}")
    print(f"hop_distribution: {metrics['hop_distribution']}")
    print(f"path_validation_errors: {len(metrics['path_validation_errors'])}")
    print(f"trusted_context_contains_nw_f: {metrics['trusted_context_contains_nw_f']}")
    print(f"trusted_context_contains_fact_id: {metrics['trusted_context_contains_fact_id']}")
    print(f"connected_components: {metrics['connected_components']}")
    print(f"isolate_count: {metrics['isolate_count']}")
    print(f"duplicate_triples: {metrics['duplicate_triples']}")
    print(f"hop10_distinct_first_edges: {metrics['hop10_distinct_first_edges']}")
    if metrics["validation_errors"]:
        print("validation_errors:")
        for error in metrics["validation_errors"]:
            print(f"  - {error}")


def main() -> None:
    facts = build_facts()
    questions = build_questions()
    trusted_context = trusted_context_prose()
    metrics = validate_dataset(facts, questions, trusted_context)

    if metrics["validation_errors"]:
        print_self_check(metrics)
        raise SystemExit(1)

    write_json(DATASET_OUT, build_dataset(facts, questions, trusted_context, metrics))
    write_json(INVENTORY_OUT, build_inventory(facts, metrics))
    print_self_check(metrics)


if __name__ == "__main__":
    main()
