# NHS WannaCry Hop-Semantics Audit

Definition: hop_count = minimum number of trusted directed graph edges needed to derive the expected answer from the question's reasoning_anchor_entities, under allowed alias normalization, without outside knowledge.

## Summary

- Preliminary shortcuts before rewrite: 15
- Shortcuts after rewrite: 0
- Unresolved shortcuts after rewrite: 0
- Entities: 88
- Facts: 87
- Relation types: 20
- Root out-degree: 12

## Hop 8-10 audit table

| id | hop | shortest distance | final subject mentioned | answer mentioned | unresolved | answer |
| --- | ---: | ---: | --- | --- | --- | --- |
| nhs_wannacry_h08_q01 | 8 | 8 | False | False | False | SMBv1 crafted-request handling |
| nhs_wannacry_h08_q02 | 8 | 8 | False | False | False | Local NHS organisations |
| nhs_wannacry_h08_q03 | 8 | 8 | False | False | False | Patients travelling further for emergency care |
| nhs_wannacry_h08_q04 | 8 | 8 | False | False | False | Incomplete national cancellation total |
| nhs_wannacry_h08_q05 | 8 | 8 | False | False | False | 88 of 236 trusts |
| nhs_wannacry_h09_q01 | 9 | 9 | False | False | False | Corrected SMBv1 request handling |
| nhs_wannacry_h09_q02 | 9 | 9 | False | False | False | Local implementation of CareCERT patch advice |
| nhs_wannacry_h09_q03 | 9 | 9 | False | False | False | Number of diverted ambulances and patients not collected |
| nhs_wannacry_h09_q04 | 9 | 9 | False | False | False | Actual cancelled-appointment number |
| nhs_wannacry_h09_q05 | 9 | 9 | False | False | False | None passed |
| nhs_wannacry_h10_q01 | 10 | 10 | False | False | False | Microsoft Security Bulletin MS17-010 |
| nhs_wannacry_h10_q02 | 10 | 10 | False | False | False | Not all organisations implemented critical patch advice before attack |
| nhs_wannacry_h10_q03 | 10 | 10 | False | False | False | Department and NHS England did not know full diversion count |
| nhs_wannacry_h10_q04 | 10 | 10 | False | False | False | Not planned for identification by NHS England |
| nhs_wannacry_h10_q05 | 10 | 10 | False | False | False | Before 12 May 2017 |

## Full per-question audit

| id | hop | path length | shortest distance | final subject mentioned | unresolved |
| --- | ---: | ---: | ---: | --- | --- |
| nhs_wannacry_h01_q01 | 1 | 1 | 1 | False | False |
| nhs_wannacry_h01_q02 | 1 | 1 | 1 | False | False |
| nhs_wannacry_h01_q03 | 1 | 1 | 1 | False | False |
| nhs_wannacry_h01_q04 | 1 | 1 | 1 | False | False |
| nhs_wannacry_h01_q05 | 1 | 1 | 1 | False | False |
| nhs_wannacry_h02_q01 | 2 | 2 | 2 | False | False |
| nhs_wannacry_h02_q02 | 2 | 2 | 2 | False | False |
| nhs_wannacry_h02_q03 | 2 | 2 | 2 | False | False |
| nhs_wannacry_h02_q04 | 2 | 2 | 2 | False | False |
| nhs_wannacry_h02_q05 | 2 | 2 | 2 | False | False |
| nhs_wannacry_h03_q01 | 3 | 3 | 3 | False | False |
| nhs_wannacry_h03_q02 | 3 | 3 | 3 | False | False |
| nhs_wannacry_h03_q03 | 3 | 3 | 3 | False | False |
| nhs_wannacry_h03_q04 | 3 | 3 | 3 | False | False |
| nhs_wannacry_h03_q05 | 3 | 3 | 3 | False | False |
| nhs_wannacry_h04_q01 | 4 | 4 | 4 | False | False |
| nhs_wannacry_h04_q02 | 4 | 4 | 4 | False | False |
| nhs_wannacry_h04_q03 | 4 | 4 | 4 | False | False |
| nhs_wannacry_h04_q04 | 4 | 4 | 4 | False | False |
| nhs_wannacry_h04_q05 | 4 | 4 | 4 | False | False |
| nhs_wannacry_h05_q01 | 5 | 5 | 5 | False | False |
| nhs_wannacry_h05_q02 | 5 | 5 | 5 | False | False |
| nhs_wannacry_h05_q03 | 5 | 5 | 5 | False | False |
| nhs_wannacry_h05_q04 | 5 | 5 | 5 | False | False |
| nhs_wannacry_h05_q05 | 5 | 5 | 5 | False | False |
| nhs_wannacry_h06_q01 | 6 | 6 | 6 | False | False |
| nhs_wannacry_h06_q02 | 6 | 6 | 6 | False | False |
| nhs_wannacry_h06_q03 | 6 | 6 | 6 | False | False |
| nhs_wannacry_h06_q04 | 6 | 6 | 6 | False | False |
| nhs_wannacry_h06_q05 | 6 | 6 | 6 | False | False |
| nhs_wannacry_h07_q01 | 7 | 7 | 7 | False | False |
| nhs_wannacry_h07_q02 | 7 | 7 | 7 | False | False |
| nhs_wannacry_h07_q03 | 7 | 7 | 7 | False | False |
| nhs_wannacry_h07_q04 | 7 | 7 | 7 | False | False |
| nhs_wannacry_h07_q05 | 7 | 7 | 7 | False | False |
| nhs_wannacry_h08_q01 | 8 | 8 | 8 | False | False |
| nhs_wannacry_h08_q02 | 8 | 8 | 8 | False | False |
| nhs_wannacry_h08_q03 | 8 | 8 | 8 | False | False |
| nhs_wannacry_h08_q04 | 8 | 8 | 8 | False | False |
| nhs_wannacry_h08_q05 | 8 | 8 | 8 | False | False |
| nhs_wannacry_h09_q01 | 9 | 9 | 9 | False | False |
| nhs_wannacry_h09_q02 | 9 | 9 | 9 | False | False |
| nhs_wannacry_h09_q03 | 9 | 9 | 9 | False | False |
| nhs_wannacry_h09_q04 | 9 | 9 | 9 | False | False |
| nhs_wannacry_h09_q05 | 9 | 9 | 9 | False | False |
| nhs_wannacry_h10_q01 | 10 | 10 | 10 | False | False |
| nhs_wannacry_h10_q02 | 10 | 10 | 10 | False | False |
| nhs_wannacry_h10_q03 | 10 | 10 | 10 | False | False |
| nhs_wannacry_h10_q04 | 10 | 10 | 10 | False | False |
| nhs_wannacry_h10_q05 | 10 | 10 | 10 | False | False |
