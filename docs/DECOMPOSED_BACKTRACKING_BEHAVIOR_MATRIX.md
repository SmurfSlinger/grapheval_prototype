# Decomposed Backtracking Behavior Coverage Matrix

Deterministic suite: `tests/test_decomposed_backtracking_behavior_suite.py`
(24 scenarios, mock/fixture driven, no live-model dependence). Benchmark
question IDs refer to `nitfs_geoint_multihop_50` (N) and `apollo_multihop_50`
(A) where a live benchmark question also exercises the scenario.

| # | Scenario | Deterministic test | Benchmark question IDs | Expected pipeline behavior | Observed result |
|---|---|---|---|---|---|
| 1 | Atomic question remains atomic | `test_s01_atomic_question_remains_atomic` | N `h01_*`, A `apollo_hop_001` | One sub-question equal to the original | PASS |
| 2 | Nested single-clause question remains atomic | `test_s02_nested_single_clause_question_remains_atomic` | A `apollo_hop_011`, N `h02_*` | Over-splits rejected; original preserved | PASS |
| 3 | True compound question decomposes | `test_s03_true_compound_question_decomposes` | — (benchmark questions are single-target) | Valid multi-sub decomposition accepted | PASS |
| 4 | Invalid fragment decomposition falls back | `test_s04_invalid_fragment_decomposition_falls_back` | regression of A `apollo_hop_001` defect | Fragment splits fall back to original | PASS |
| 5 | Acronym/alias resolution | `test_s05_acronym_and_alias_resolution` | N `h03_q03` (JITC), N `h07_q01` (BF01) | Alias/acronym detected; scoring normalization stable | PASS |
| 6 | Active-to-passive canonical direction | `test_s06_active_to_passive_direction_correction` | N `h01_q05`, N `h02_q05` | Grammar-grounded inversion corrected | PASS |
| 7 | Inverse-direction extraction rejected/corrected safely | `test_s07_inverse_direction_without_grammar_stays_unsupported` | N depth>=5 passive edges | No KG-only flip; claim stays unsupported with anomaly | PASS |
| 8 | Object-only alignment cannot rewrite subject+relation | `test_s08_object_only_alignment_cannot_rewrite_subject_and_relation` | regression of A `apollo_hop_046` defect | Alignment rejected; claim unchanged | PASS |
| 9 | Correct answer with unsupported explanatory prose | `test_s09_correct_answer_with_unsupported_explanatory_prose_not_resolved` | observed live in A depth 7-10 rows | NO_EVIDENCE explanation blocks resolution honestly | PASS |
| 10 | Wrong answer correctly rejected | `test_s10_wrong_answer_correctly_rejected` | A wrong-answer rows | CONTRADICTED label | PASS |
| 11 | Contradiction | `test_s11_contradiction_blocks_resolution` | same as 10 | Contradiction never resolves | PASS |
| 12 | No evidence | `test_s12_no_evidence_claim_labeled` | A/N unresolved rows | NO_EVIDENCE label, no matched fact | PASS |
| 13 | Complete path to intermediate claim, target unsatisfied | `test_s13_complete_intermediate_path_does_not_satisfy_target` | regression of A `apollo_hop_046` | Path completeness alone does not resolve | PASS |
| 14 | Complete path to actual terminal answer | `test_s14_complete_path_to_terminal_answer_includes_final_edge` | N `h10_*`, A `apollo_hop_046` | Final edge included; complete | PASS |
| 15 | Multiple-value/list answer | `test_s15_list_answer_supported_and_scored` | N `h10_q04` (ISO, NTB, and NATO communities) | Supported and scorable | PASS |
| 16 | Numeric answer | `test_s16_numeric_answer_supported_and_scored` | N extra fact 02.10; N `h07_q01` BF01 | Supported and scorable | PASS |
| 17 | Date/version answer | `test_s17_date_version_answer_supported_and_scored` | N `h04_q04`, `h05_q04`, `h09_q02` | Supported and scorable | PASS |
| 18 | Repeated unchanged answer, no new FACTS, stops cleanly | `test_s18_repeated_unchanged_answer_without_new_facts_stops` | A stalled rows | Terminal stop without extra revisions | PASS |
| 19 | Unresolved answer text remains uncorrupted | `test_s19_unresolved_answer_text_remains_uncorrupted` | A unresolved-but-correct rows | Model prose preserved | PASS |
| 20 | Resolved atomic prose projects to verified terminal object | `test_s20_resolved_atomic_prose_projects_to_verified_terminal_object` | A `apollo_hop_001` | Projection only when RESOLVED | PASS |
| 21 | CLAIM/FACT separation | `test_s21_supported_claims_remain_claims_not_facts` | all rows (`claim_edges_written` vs `fact_edges_written`) | Supported CLAIMS never become FACTS | PASS |
| 22 | Execution isolation | `test_s22_execution_isolation_facts_do_not_leak_between_calls` | every live row (fresh execution_id) | Foreign-execution facts never enter a path | PASS |
| 23 | Simultaneous executions do not cross-link | `test_s23_neo4j_store_scopes_every_query_by_execution_id` | Neo4j verification of live runs | All store queries scoped by execution_id | PASS |
| 24 | Expected-answer/path metadata never enters inference | `test_s24_expected_answer_metadata_never_enters_inference_inputs` | all rows | Only id/question/context reach the pipeline | PASS |

Existing regression suites remain unweakened:
`tests/test_pipeline_alignment_and_unresolved_integrity.py`,
`tests/test_decomposition_aggregate_fixes.py`, `tests/test_kgc_schema_aligner.py`,
`tests/test_question_target.py`, `tests/test_expected_answer_leakage.py`.
