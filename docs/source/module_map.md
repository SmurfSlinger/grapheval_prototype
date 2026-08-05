# Module map

Handwritten map of the live architecture. Autodoc details are on {doc}`api_reference`.

| Path / module | Responsibility | Main public symbols | Typical caller | Downstream | LLM? | Neo4j? | Types in → out |
|---|---|---|---|---|---|---|---|
| `scripts/run_multihop_benchmark.py` | Benchmark orchestration + post-inference scoring | `main` / run loop | CLI | `DecomposedBacktrackingRunner` | via runner | via runner | question JSON → result row |
| `src/pipeline/decomposed_backtracking_runner.py` | End-to-end decomposed run | `DecomposedBacktrackingRunner.run_example` | benchmark, API | iteration, storage helpers | yes | yes (optional/required flag) | example → result/trace |
| `src/pipeline/kgc_iteration.py` | Per-sub-question loop | `KgcIterationEngine`, `determine_stop_reason` | runner | comparator, feedback, reviser, path | yes | no (indirect) | answer+facts → history+stop |
| `src/pipeline/graph_comparator.py` | Claim labels | `GraphComparator.compare_claims` | iteration engine | matching / target frame | no | no | claims+facts → evaluations |
| `src/pipeline/backtracking_feedback_builder.py` | Structured feedback | `BacktrackingFeedbackBuilder` | iteration engine | — | no | no | evaluations → feedback items |
| `src/pipeline/backtracking_reviser.py` | LLM revision | reviser class | iteration engine | provider | yes | no | answer+feedback → text |
| `src/pipeline/question_target.py` | Target derive/satisfy | `derive_question_target`, `evaluate_target_satisfaction` | iteration engine | — | no | no | question+evals → target/eval |
| `src/pipeline/evidence_path_resolver.py` | Trusted path | `resolve_evidence_path` | iteration engine | FACT list | no | no | start+terminal+facts → path result |
| `src/pipeline/kgc_schema_aligner.py` | Safe claim field alignment | `align_claims_to_kgc_schema` | claim extract path | — | no | no | claims+facts → aligned |
| `src/pipeline/execution_context.py` | Execution ids | `ExecutionScope` | runner | storage | no | scopes writes | metadata → scope |
| `src/storage/neo4j_store.py` | Persistence | `Neo4jStore`, `*_if_enabled` helpers | runner | Neo4j Bolt | no | yes | facts/evals → graph |
| `src/models.py` | Shared types/enums | `KgcFact`, `KgcClaimLabel`, stop enums | everywhere | — | no | no | dataclasses |
| `src/pipeline/debug_log.py` | JSONL traces | `log_debug_event` | pipeline | filesystem | no | no | events → JSONL |
| `prompts/` | LLM templates | template files | providers/extractors | — | yes | no | strings |
| `api/server.py` | HTTP API | FastAPI `app` | uvicorn | runner | yes | optional | HTTP → JSON |
| `scripts/analyze_final_experiment.py` | Official aggregates | analysis entry | CLI | result JSON | no | no | results → analysis |
| `scripts/analyze_repeatability_experiment.py` | Repeatability aggregates | analysis entry | CLI | result JSONs | no | no | runs → analysis |

## Diagrams

Sources: `docs/diagrams/source/`. Rendered: `docs/diagrams/rendered/`.
