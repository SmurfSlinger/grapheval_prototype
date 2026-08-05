# Methodology Documentation Audit

**Branch:** `research/methodology-and-code-documentation`  
**Audit HEAD:** `7924761c8082ecda9ce1a18fe3ef1f9f0e0d64c3` (tip when audit began)  
**Frozen inference commit (must not change):** `b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`  
**Date:** 2026-08-04  

This audit records what the **current codebase and preserved artifacts** actually do, before any methodology prose rewrite. Descriptions below are verified against source files, tests, Cypher, prompts, and/or run artifacts. Items that could not be verified are marked explicitly.

## 1. Repository state at audit start

| Item | Value |
|---|---|
| Branch | `research/methodology-and-code-documentation` (created from repeatability tip `7924761`) |
| Untracked work preserved | NITFS dataset/scripts, `.agent_scratch/`, behavior-suite test, prior docs — **not** reset or discarded |
| Report files | `reports/GraphEval Experiment Report.md`, `.docx` |
| Existing `docs/` | Milestone/design/audit Markdown notes; **no** Sphinx site yet |
| Existing diagrams | Simplified Mermaid flowcharts in `README.md` and `docs/kgc_backtracking_milestone_report.md` (conceptual; not exact Neo4j schema) |
| Package layout | `src/` pipeline + models + storage; `api/`; `prompts/`; `scripts/`; `frontend/`; `tests/`; `research/`; `results/research/` |
| Live execution entry (benchmark) | `scripts/run_multihop_benchmark.py` → `DecomposedBacktrackingRunner.run_example` |
| Live execution entry (API/CLI) | `api/server.py` / `src/main.py` → same runner family |

Inference-sensitive paths under `src/`, `prompts/`, benchmark JSONs, and frozen result files were inspected only; they must not be modified by this documentation pass.

## 2. Concept → implementation map

| Concept | Actual implementation file | Actual function/class | Input | Output | Neo4j read/write | Evidence used to verify it | Documentation implication |
|---|---|---|---|---|---|---|---|
| Execution identity / isolation | `src/pipeline/execution_context.py` | `ExecutionScope.begin` | example / benchmark / question ids | `execution_id` = `{question_or_example}__{UTC}__{8-hex}` | Scopes all later writes | Module docstring; WannaCry/Apollo traces | Never describe cross-question shared graph state for live runs |
| Optional clear before one run | `src/storage/neo4j_store.py`, runner | `clear_execution_if_enabled` / `Neo4jStore.clear_execution` | one `execution_id` | DETACH DELETE `Entity` nodes for that id | Write (delete) | Cypher in `clear_execution`; benchmark `--clear-neo4j` | Clears **this execution only**, not the whole DB; isolation mainly via new ids |
| Dev full wipe | `src/storage/neo4j_store.py` | `clear_all` | none | `MATCH (n) DETACH DELETE n` | Write | Method docstring | Not the per-question benchmark path |
| Question decomposition (optional) | `prompts/` + splitter modules; runner | LLM stage `question_splitter` then deterministic validation | question text | list of sub-questions | None | Trace stages `question_split_parsed`; handoff | Decomposition is optional instrumentation, not a controlled experimental arm |
| Context FACT extraction | LLM extractor + validators | context triple extraction / `structured_triple_validated` | trusted context | `list[KgcFact]` | None until persist | Trace `context_fact_parsed`; anomalies `empty_object` | FACTS come from context, not from answers |
| FACT persist | `src/storage/neo4j_store.py` | `store_kgc_facts` / `_create_fact` | scope + facts | `(:Entity)-[:FACT]->(:Entity)` via **MERGE** | Write | Cypher lines 320–347 | Trusted edges; provenance `trusted_context` |
| FACT readback | `src/storage/neo4j_store.py` | `get_kgc_facts` / `read_kgc_facts_if_enabled` | `execution_id` | `list[KgcFact]` | Read | Cypher 187–193; official rows used readback | Working KGc may be Neo4j-backed or in-memory; comparison still Python |
| Working / focused FACT additions | `src/storage/neo4j_store.py`, `working_kgc.py` | `store_working_kgc_additions` / `_create_working_fact` | focused/derived additions | additional **FACT** edges (MERGE) with provenance fields | Write | Cypher 350–395 | Still FACTs; not promoted CLAIMs |
| Initial / projected answer | LLM answer + projector | answer generation / sub-answer projection | question, context, prior answers | answer text per sub-question | None | Trace stages | LLM-only text generation |
| CLAIM extraction | LLM claim extractor + structured parse | `TripleExtractor` path in `KgcIterationEngine` | answer text | `list[Triple]` | None | Trace `claim_parsed` | CLAIMs are answer-sourced |
| Schema alignment | `src/pipeline/kgc_schema_aligner.py` | `align_claims_to_kgc_schema` | claims + KGc facts | aligned claims + alignment trace | None | Trace `claim_alignment` | Deterministic bounded rewrites, not Neo4j |
| Claim comparison / labels | `src/pipeline/graph_comparator.py` | `GraphComparator.compare_claims` | claims, KGc facts, optional `QuestionTarget` | `list[KgcEvaluationResult]` with `SUPPORTED` / `CONTRADICTED` / `NO_EVIDENCE` | None | Code + `claim_comparison` events | **Python** assigns labels; Neo4j does not reason |
| Legacy exact compare | same | `_evaluate_claim_legacy` | claim + indexes | label + reason | None | Exact (S,R,O) → SUPPORTED; same (S,R) different O → CONTRADICTED; else NO_EVIDENCE (+ polarity/engine helpers) | Document both legacy and target-frame paths |
| Target-frame compare | same + `target_frame_normalizer.py` | `_evaluate_claim_target_frame` | claim + target + facts | label using relation families / object compatibility | None | Apollo complex `occurred_during` vs `mission_dates` reason text | Used when `expected_relations` present on target |
| Feedback construction | `src/pipeline/backtracking_feedback_builder.py` | `BacktrackingFeedbackBuilder.build` | evaluations | list of feedback items (all three labels) | None | Code: SUPPORTED→preserve; CONTRADICTED→correct using conflicting FACT; NO_EVIDENCE→omit/mark | Feedback is Python-built, then sent to LLM reviser |
| Revision | `src/pipeline/backtracking_reviser.py` | reviser LLM call | answer + feedback | revised answer | None | Trace revision events / WannaCry regression | LLM revises text only |
| Target satisfaction | `src/pipeline/question_target.py` | `derive_question_target`, `evaluate_target_satisfaction` | question + evaluations | target object + satisfied bool | None | Stop reason `UNRESOLVED_TARGET_NOT_SATISFIED` | Separate from textual scoring |
| Evidence path | `src/pipeline/evidence_path_resolver.py` | `resolve_evidence_path` | start entity, terminal claim, FACT graph | path edges + `complete` + `failure_reason` | Uses in-memory/readback FACTS, not Cypher path algorithms for the verdict | Official hop_036 `evidence_path` object | Path validation is Python over trusted FACTs |
| Stop reasons | `src/pipeline/kgc_iteration.py` | `determine_stop_reason` | labels, target, path, iteration | `SubQuestionStopReason` enum | None | `src/models.py` enum | RESOLVED requires clean labels + target + path not incomplete |
| CLAIM persist | `src/storage/neo4j_store.py` | `store_kgc_claims` / `_create_kgc_claim` | evaluations per iteration | **CREATE** CLAIM edges (append) | Write | Cypher 406–424; runner loop stores **every** history item | Prior-iteration CLAIMs **remain**; not replaced |
| Label storage | Neo4j CLAIM props + result objects | `label`, `reason`, … on CREATE | evaluation | stored on relationship | Write of Python-computed label | `_create_kgc_claim` | Labels calculated in Python, then optionally stored |
| Combine answers | runner helpers | `combine_sub_answers` | sub-results | combined final string | None | Trace `combined_answer` | Post-subquestion assembly |
| Post-inference scoring | `scripts/run_multihop_benchmark.py` + analyzers | exact/contains/normalized match | predicted vs expected | booleans / rates | None | Official result JSON; `tests/test_expected_answer_leakage.py` | Expected answers **never** enter inference |
| Constraints / indexes | `scripts/recreate-neo4j.sh` | Cypher install | — | unique `(execution_id,name)` on Entity; indexes on FACT/CLAIM `execution_id` | Schema | Script lines 128–140 | Document only these |

## 3. Verified call sequence (benchmark question → final result)

Live path for the official Apollo experiment:

1. **`scripts/run_multihop_benchmark.py`** loads one question (context + expected fields held for scoring only).
2. Constructs **`DecomposedBacktrackingRunner`** with `clear_neo4j_before_run` from `--clear-neo4j`, provider `llama3.1:8b`, max iterations 3.
3. **`DecomposedBacktrackingRunner.run_example`** (`src/pipeline/decomposed_backtracking_runner.py`):
   1. `ExecutionScope.begin` → unique `execution_id`.
   2. If configured: `clear_execution_if_enabled(execution_id)` (delete only that id’s entities).
   3. Optional LLM question split → deterministic validation → sub-question list (or single question).
   4. LLM context FACT extraction → structured validation → in-memory FACT list.
   5. `store_kgc_facts_if_enabled` (**Neo4j WRITE** MERGE FACT).
   6. Optional `read_kgc_facts_if_enabled` (**Neo4j READ**) into working KGc.
   7. LLM initial answer (and/or per-subquestion context-grounded mode); project onto sub-questions (LLM).
   8. For each sub-question, **`KgcIterationEngine`** / iteration helpers in `kgc_iteration.py`:
      - LLM claim extract → schema align (Python) → **`GraphComparator.compare_claims`** (Python labels).
      - Optional focused/derived FACT enrichment (LLM extract + Python gate; may WRITE working FACTs later).
      - Target derivation/satisfaction (Python); evidence path (Python over FACTs).
      - If not stopped: feedback (Python) → revise (LLM) → repeat up to max iterations.
      - After sub-question finishes: for **each** iteration in `history`, `store_kgc_claims_if_enabled` (**Neo4j WRITE** CREATE CLAIM) — appends, does not delete prior CLAIMs.
   9. Combine sub-answers; store working FACT additions; build `DecomposedBacktrackingTrace` / result object.
4. Benchmark runner scores `exact_match` / `contains_expected_answer` / etc. **after** inference and writes the result row JSON.

Post-experiment analysis (`scripts/analyze_final_experiment.py`) only reads frozen results; it does not re-run inference.

## 4. Data-model quick reference (application objects)

| Type | Definition in code | Notes |
|---|---|---|
| FACT | `KgcFact` in `src/models.py` | Trusted S–R–O from context (or working enrichment with provenance) |
| CLAIM | `Triple` evaluated to `KgcEvaluationResult` | From answer; label does **not** change type to FACT |
| Labels | `KgcClaimLabel`: `SUPPORTED`, `CONTRADICTED`, `NO_EVIDENCE` | Legacy enum also mentions older strings in Neo4j bad-claim filter |
| Iteration | `SubQuestionIteration` | Per sub-question loop state |
| Stop | `SubQuestionStopReason` | RESOLVED, STALLED, UNRESOLVED_NO_EVIDENCE, UNRESOLVED_TARGET_NOT_SATISFIED, MAX_ITERATIONS, GENERATION_FAILED, NO_CLAIMS_EXTRACTED |
| Execution | `ExecutionScope` | Scopes Neo4j and traces |

## 5. LLM prompt stages (names as recorded)

Observed / configured stage names include: `question_splitter`, context FACT extraction, focused FACT extraction, answer generation, `sub_answer_projector`, claim extraction, reviser. Templates live under `prompts/`. Exact template text must be cited from those files when documented; do not paraphrase behavior that is not in the template or code.

## 6. Preserved artifacts suitable for worked examples

| Example need | Artifact | Limitation |
|---|---|---|
| Clean SUPPORTED | `.runtime/debug/20260727T202312Z_apollo_hop_046_attempt_91bb9b85.jsonl` (post-fix) | Separate from official aggregate row’s null `debug_log_path`, but same frozen code lineage |
| CONTRADICTED (clear FACT conflict) | `.runtime/debug/20260727T010636Z_apollo_complex_attempt_c8a1631c.jsonl` | Qualitative / complex example; not one of the 50 official hop rows |
| CONTRADICTED (over-expanded object) | WannaCry Q2 in `...70a052a7.jsonl` | Outside Apollo quantitative sample |
| NO_EVIDENCE | WannaCry Q1 final claim `… → patching` in same trace | Outside Apollo sample |
| Multi-iteration correction | Official `apollo_hop_036` row in `apollo_multihop_llama31_8b_20260727T203028Z.json` | **`debug_log_path: null`** — intermediate answers/labels **not preserved** |
| Full regression walkthrough | WannaCry `nhs_wannacry_h10_q01` trace above | Must stay explicitly separate from Apollo n=50 stats |

Official Apollo 50-question rows do **not** retain per-iteration debug JSONL (`debug_log_path` null). Do not invent initial answers for those rows.

## 7. Documentation implications (binding)

1. Neo4j stores and retrieves; Python compares and decides stop reasons; the LLM generates/extracts/revises text.
2. CLAIM CREATE is append-only across iterations within an execution.
3. Supported CLAIMs remain CLAIMs.
4. Expected answers and expected paths are post-inference only.
5. No controlled no-feedback baseline exists in this experiment — feasibility and case evidence only.
6. README Mermaid is a **simplified conceptual** view and must be labeled as such if reused.

## 8. Audit completion gate

Phase 1 complete: concept table and verified call sequence recorded. Report methodology rewrite (Phase 5) may proceed only from this audit plus Phase 2–3 evidence files.
