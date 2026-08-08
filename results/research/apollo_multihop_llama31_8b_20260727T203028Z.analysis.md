# Benchmark Analysis: apollo_multihop_50

- Source: `results/research/apollo_multihop_llama31_8b_20260727T203028Z.json`
- Provider/model: ollama / llama3.1:8b
- Branch: debug/8b-hop-validation
- Generated: 2026-07-27T21:12:37.433000+00:00
- num_ctx=8192, timeout=180.0s, neo4j=True, cleared-between-questions=True

Sample-size note: five questions per designed depth — depth-level rates are small-sample descriptions, not statistically significant estimates.

## Overall

| Metric | Value |
|---|---|
| attempted | 50 |
| completed | 50 |
| errors | 0 |
| timeouts | 0 |
| exact_match | 27 |
| contains_expected | 43 |
| pipeline_resolved | 33 |
| resolved_and_matched | 27 |
| resolved_but_wrong | 6 |
| unresolved_but_contains_expected | 15 |
| avg_runtime_seconds | 48.42 |
| median_runtime_seconds | 44.91 |
| avg_iterations | 1.66 |
| avg_revisions | 0.66 |
| supported_claims | 65 |
| contradicted_claims | 1 |
| no_evidence_claims | 12 |
| evidence_path_complete | 36 |
| neo4j_readback_evaluations | 50 |

## By designed depth

| Depth | Attempted | Exact | Contains | Resolved | Resolved+Exact | Unresolved-but-contains | Path complete | Avg runtime s | Avg iters | Avg revs |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 | 4 | 5 | 4 | 4 | 1 | 4 | 40.72 | 1.2 | 0.2 |
| 2 | 5 | 3 | 5 | 3 | 3 | 2 | 4 | 46.91 | 1.6 | 0.6 |
| 3 | 5 | 3 | 3 | 4 | 3 | 0 | 4 | 43.43 | 1.4 | 0.4 |
| 4 | 5 | 2 | 4 | 2 | 2 | 2 | 4 | 51.95 | 1.8 | 0.8 |
| 5 | 5 | 4 | 4 | 5 | 4 | 0 | 5 | 47.74 | 1.4 | 0.4 |
| 6 | 5 | 4 | 5 | 4 | 4 | 1 | 4 | 46.78 | 1.4 | 0.4 |
| 7 | 5 | 1 | 4 | 2 | 1 | 3 | 2 | 48.14 | 1.8 | 0.8 |
| 8 | 5 | 1 | 4 | 3 | 1 | 2 | 3 | 53.92 | 2.2 | 1.2 |
| 9 | 5 | 3 | 4 | 4 | 3 | 1 | 4 | 51.95 | 2.0 | 1.0 |
| 10 | 5 | 2 | 5 | 2 | 2 | 3 | 2 | 52.64 | 1.8 | 0.8 |

## Failure attribution

| Category | Count |
|---|---|
| success | 27 |
| wrong_direct_answer | 7 |
| evidence_path_resolution_error | 7 |
| claim_extraction_error | 5 |
| ambiguous | 3 |
| aggregation_projection_failure | 1 |

## Representative UI cases

- **clean_low_depth_success**: `apollo_hop_001` (hop 1) — execution `apollo_hop_001__20260727T203028Z__656bf325` — Exact answer and honest pipeline resolution.
- **clean_high_depth_success**: `apollo_hop_046` (hop 10) — execution `apollo_hop_046__20260727T210803Z__c3c7849e` — Exact answer and honest pipeline resolution.
- **correct_answer_but_unresolved**: `apollo_hop_005` (hop 1) — execution `apollo_hop_005__20260727T203315Z__738dc7cf` — Answer text contains the expected value but extracted claims did not match trusted FACTS (NO_EVIDENCE).
- **genuine_model_answer_failure**: `apollo_hop_014` (hop 3) — execution `apollo_hop_014__20260727T204021Z__ae6eabf6` — Predicted answer differs from expected answer text.
- **structured_claim_or_pipeline_failure**: `apollo_hop_005` (hop 1) — execution `apollo_hop_005__20260727T203315Z__738dc7cf` — Answer text contains the expected value but extracted claims did not match trusted FACTS (NO_EVIDENCE).

## Per-question appendix

| ID | Hop | Exact | Contains | Resolved | Stop | Iter | Rev | S/C/N | Path len | Path complete | Attribution |
|---|---|---|---|---|---|---|---|---|---|---|---|
| apollo_hop_001 | 1 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 2 | True | success |
| apollo_hop_002 | 1 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 1 | True | success |
| apollo_hop_003 | 1 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 1 | True | success |
| apollo_hop_004 | 1 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 1 | True | success |
| apollo_hop_005 | 1 | False | True | False | STALLED | 2 | 1 | 0/0/1 | 0 | False | claim_extraction_error |
| apollo_hop_006 | 2 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 2 | True | success |
| apollo_hop_007 | 2 | False | True | False | UNRESOLVED_NO_EVIDENCE | 3 | 2 | 1/0/1 | 1 | True | ambiguous |
| apollo_hop_008 | 2 | True | True | True | RESOLVED | 1 | 0 | 2/0/0 | 1 | True | success |
| apollo_hop_009 | 2 | True | True | True | RESOLVED | 1 | 0 | 2/0/0 | 2 | True | success |
| apollo_hop_010 | 2 | False | True | False | STALLED | 2 | 1 | 0/0/1 | 0 | False | claim_extraction_error |
| apollo_hop_011 | 3 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 3 | True | success |
| apollo_hop_012 | 3 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 3 | True | success |
| apollo_hop_013 | 3 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 3 | True | success |
| apollo_hop_014 | 3 | False | False | False | UNRESOLVED_TARGET_NOT_SATISFIED | 3 | 2 | 1/0/0 | 0 | False | wrong_direct_answer |
| apollo_hop_015 | 3 | False | False | True | RESOLVED | 1 | 0 | 2/0/0 | 2 | True | wrong_direct_answer |
| apollo_hop_016 | 4 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 3 | True | success |
| apollo_hop_017 | 4 | False | True | False | STALLED | 2 | 1 | 1/0/1 | 4 | True | ambiguous |
| apollo_hop_018 | 4 | False | True | False | UNRESOLVED_NO_EVIDENCE | 3 | 2 | 2/0/3 | 1 | True | ambiguous |
| apollo_hop_019 | 4 | False | False | False | STALLED | 2 | 1 | 0/1/1 | 0 | False | wrong_direct_answer |
| apollo_hop_020 | 4 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 4 | True | success |
| apollo_hop_021 | 5 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 4 | True | success |
| apollo_hop_022 | 5 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 5 | True | success |
| apollo_hop_023 | 5 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 4 | True | success |
| apollo_hop_024 | 5 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 4 | True | success |
| apollo_hop_025 | 5 | False | False | True | RESOLVED | 3 | 2 | 5/0/0 | 2 | True | wrong_direct_answer |
| apollo_hop_026 | 6 | False | True | False | UNRESOLVED_NO_EVIDENCE | 3 | 2 | 0/0/1 | 0 | False | claim_extraction_error |
| apollo_hop_027 | 6 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 6 | True | success |
| apollo_hop_028 | 6 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 5 | True | success |
| apollo_hop_029 | 6 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 5 | True | success |
| apollo_hop_030 | 6 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 3 | True | success |
| apollo_hop_031 | 7 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 6 | True | success |
| apollo_hop_032 | 7 | False | True | False | STALLED | 2 | 1 | 0/0/1 | 0 | False | claim_extraction_error |
| apollo_hop_033 | 7 | False | True | False | UNRESOLVED_TARGET_NOT_SATISFIED | 2 | 1 | 2/0/0 | 0 | False | evidence_path_resolution_error |
| apollo_hop_034 | 7 | False | True | False | UNRESOLVED_TARGET_NOT_SATISFIED | 3 | 2 | 1/0/0 | 7 | False | evidence_path_resolution_error |
| apollo_hop_035 | 7 | False | False | True | RESOLVED | 1 | 0 | 2/0/0 | 3 | True | wrong_direct_answer |
| apollo_hop_036 | 8 | True | True | True | RESOLVED | 3 | 2 | 3/0/0 | 7 | True | success |
| apollo_hop_037 | 8 | False | False | True | RESOLVED | 2 | 1 | 3/0/0 | 7 | True | wrong_direct_answer |
| apollo_hop_038 | 8 | False | True | False | STALLED | 3 | 2 | 0/0/1 | 0 | False | claim_extraction_error |
| apollo_hop_039 | 8 | False | True | False | UNRESOLVED_TARGET_NOT_SATISFIED | 2 | 1 | 1/0/0 | 0 | False | evidence_path_resolution_error |
| apollo_hop_040 | 8 | False | True | True | RESOLVED | 1 | 0 | 2/0/0 | 5 | True | aggregation_projection_failure |
| apollo_hop_041 | 9 | False | False | True | RESOLVED | 3 | 2 | 2/0/0 | 1 | True | wrong_direct_answer |
| apollo_hop_042 | 9 | True | True | True | RESOLVED | 2 | 1 | 5/0/0 | 6 | True | success |
| apollo_hop_043 | 9 | False | True | False | STALLED | 2 | 1 | 2/0/1 | 9 | False | evidence_path_resolution_error |
| apollo_hop_044 | 9 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 2 | True | success |
| apollo_hop_045 | 9 | True | True | True | RESOLVED | 2 | 1 | 1/0/0 | 6 | True | success |
| apollo_hop_046 | 10 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 9 | True | success |
| apollo_hop_047 | 10 | True | True | True | RESOLVED | 1 | 0 | 1/0/0 | 8 | True | success |
| apollo_hop_048 | 10 | False | True | False | UNRESOLVED_TARGET_NOT_SATISFIED | 2 | 1 | 1/0/0 | 9 | False | evidence_path_resolution_error |
| apollo_hop_049 | 10 | False | True | False | UNRESOLVED_TARGET_NOT_SATISFIED | 3 | 2 | 1/0/0 | 0 | False | evidence_path_resolution_error |
| apollo_hop_050 | 10 | False | True | False | UNRESOLVED_TARGET_NOT_SATISFIED | 2 | 1 | 1/0/0 | 0 | False | evidence_path_resolution_error |
