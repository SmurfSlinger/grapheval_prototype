# NHS WannaCry Hop-Semantics Audit

Definition: hop_count = designed root-to-answer graph depth: the length of the intended contiguous trusted directed path from the graph root (also expressed as the question anchor in this dataset) to the expected answer. This equals the expected graph path length and the shortest directed root-to-answer distance under current validation, but does not by itself prove cognitive reasoning depth.

## Honest hop-semantics framing

- Per-question label: `designed_root_to_answer_graph_depth`.
- **Expected path length** is the designed contiguous trusted path length.
- **Shortest directed distance from the graph root** is reported separately.
- **Late-path entity exposure** and **locality / sentence-retrieval risk** are
  audited; graph distance alone does not prove cognitive reasoning depth.
- Validation fails if a question does not express its anchors, if discourse
  anaphora remains, if a shorter-path entity/alias is exposed, or if
  `manual_reviewed` is auto-claimed.

## Summary

- Preliminary shortcuts before rewrite: 15
- Shortcuts after rewrite: 0
- Unresolved shortcuts after rewrite: 0
- Ambiguous discourse markers remaining: 0
- Locality warnings: 3
- Human review pending: 50 questions
- Entities: 88
- Facts: 87
- Relation types: 20
- Root out-degree: 12

Human review status: all rows are `pending` with `generator_checked: true`; automated checks are generator-side audits only.

## Hop 8-10 audit table

| id | hop | path length | root distance | anchor distance | final subject mentioned | answer mentioned | late-chain mention | locality | review | answer |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- |
| nhs_wannacry_h08_q01 | 8 | 8 | 8 | 8 | False | False | False | PASS | pending | SMBv1 crafted-request handling |
| nhs_wannacry_h08_q02 | 8 | 8 | 8 | 8 | False | False | False | WARNING | pending | Local NHS organisations |
| nhs_wannacry_h08_q03 | 8 | 8 | 8 | 8 | False | False | False | PASS | pending | Patients travelling further for emergency care |
| nhs_wannacry_h08_q04 | 8 | 8 | 8 | 8 | False | False | False | PASS | pending | Incomplete national cancellation total |
| nhs_wannacry_h08_q05 | 8 | 8 | 8 | 8 | False | False | False | PASS | pending | 88 of 236 trusts |
| nhs_wannacry_h09_q01 | 9 | 9 | 9 | 9 | False | False | False | PASS | pending | Corrected SMBv1 request handling |
| nhs_wannacry_h09_q02 | 9 | 9 | 9 | 9 | False | False | False | PASS | pending | Local implementation of CareCERT patch advice |
| nhs_wannacry_h09_q03 | 9 | 9 | 9 | 9 | False | False | False | PASS | pending | Number of diverted ambulances and patients not collected |
| nhs_wannacry_h09_q04 | 9 | 9 | 9 | 9 | False | False | False | PASS | pending | Actual cancelled-appointment number |
| nhs_wannacry_h09_q05 | 9 | 9 | 9 | 9 | False | False | False | PASS | pending | None passed |
| nhs_wannacry_h10_q01 | 10 | 10 | 10 | 10 | False | False | False | PASS | pending | Microsoft Security Bulletin MS17-010 |
| nhs_wannacry_h10_q02 | 10 | 10 | 10 | 10 | False | False | False | PASS | pending | Not all organisations implemented critical patch advice before attack |
| nhs_wannacry_h10_q03 | 10 | 10 | 10 | 10 | False | False | False | PASS | pending | Department and NHS England did not know full diversion count |
| nhs_wannacry_h10_q04 | 10 | 10 | 10 | 10 | False | False | False | PASS | pending | Not planned for identification by NHS England |
| nhs_wannacry_h10_q05 | 10 | 10 | 10 | 10 | False | False | False | PASS | pending | Before 12 May 2017 |

## Full per-question audit

| id | hop | path length | root distance | anchor distance | anchor | ambiguous refs | locality | unresolved |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| nhs_wannacry_h01_q01 | 1 | 1 | 1 | 1 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h01_q02 | 1 | 1 | 1 | 1 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h01_q03 | 1 | 1 | 1 | 1 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h01_q04 | 1 | 1 | 1 | 1 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h01_q05 | 1 | 1 | 1 | 1 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h02_q01 | 2 | 2 | 2 | 2 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h02_q02 | 2 | 2 | 2 | 2 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h02_q03 | 2 | 2 | 2 | 2 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h02_q04 | 2 | 2 | 2 | 2 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h02_q05 | 2 | 2 | 2 | 2 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h03_q01 | 3 | 3 | 3 | 3 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h03_q02 | 3 | 3 | 3 | 3 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h03_q03 | 3 | 3 | 3 | 3 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h03_q04 | 3 | 3 | 3 | 3 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h03_q05 | 3 | 3 | 3 | 3 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h04_q01 | 4 | 4 | 4 | 4 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h04_q02 | 4 | 4 | 4 | 4 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h04_q03 | 4 | 4 | 4 | 4 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h04_q04 | 4 | 4 | 4 | 4 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h04_q05 | 4 | 4 | 4 | 4 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h05_q01 | 5 | 5 | 5 | 5 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h05_q02 | 5 | 5 | 5 | 5 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h05_q03 | 5 | 5 | 5 | 5 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h05_q04 | 5 | 5 | 5 | 5 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h05_q05 | 5 | 5 | 5 | 5 | WannaCry attack on the NHS | none | WARNING | False |
| nhs_wannacry_h06_q01 | 6 | 6 | 6 | 6 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h06_q02 | 6 | 6 | 6 | 6 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h06_q03 | 6 | 6 | 6 | 6 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h06_q04 | 6 | 6 | 6 | 6 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h06_q05 | 6 | 6 | 6 | 6 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h07_q01 | 7 | 7 | 7 | 7 | WannaCry attack on the NHS | none | WARNING | False |
| nhs_wannacry_h07_q02 | 7 | 7 | 7 | 7 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h07_q03 | 7 | 7 | 7 | 7 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h07_q04 | 7 | 7 | 7 | 7 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h07_q05 | 7 | 7 | 7 | 7 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h08_q01 | 8 | 8 | 8 | 8 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h08_q02 | 8 | 8 | 8 | 8 | WannaCry attack on the NHS | none | WARNING | False |
| nhs_wannacry_h08_q03 | 8 | 8 | 8 | 8 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h08_q04 | 8 | 8 | 8 | 8 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h08_q05 | 8 | 8 | 8 | 8 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h09_q01 | 9 | 9 | 9 | 9 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h09_q02 | 9 | 9 | 9 | 9 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h09_q03 | 9 | 9 | 9 | 9 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h09_q04 | 9 | 9 | 9 | 9 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h09_q05 | 9 | 9 | 9 | 9 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h10_q01 | 10 | 10 | 10 | 10 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h10_q02 | 10 | 10 | 10 | 10 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h10_q03 | 10 | 10 | 10 | 10 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h10_q04 | 10 | 10 | 10 | 10 | WannaCry attack on the NHS | none | PASS | False |
| nhs_wannacry_h10_q05 | 10 | 10 | 10 | 10 | WannaCry attack on the NHS | none | PASS | False |

## Locality warnings

| id | answer | closest context sentence |
| --- | --- | --- |
| nhs_wannacry_h05_q05 | NHS Digital | NHS Digital issued CareCERT alerts on 17 March and 28 April 2017 telling local NHS organisations to patch systems to prevent WannaCry, but the incident showed that not all organisations had implemented critical patch advice before the attack. |
| nhs_wannacry_h07_q01 | Specially crafted SMBv1 messages | Microsoft explained that the vulnerability affected the Microsoft Windows SMBv1 server and could allow remote code execution when specially crafted SMBv1 messages were sent. |
| nhs_wannacry_h08_q02 | Local NHS organisations | NHS Digital issued CareCERT alerts on 17 March and 28 April 2017 telling local NHS organisations to patch systems to prevent WannaCry, but the incident showed that not all organisations had implemented critical patch advice before the attack. |
