# Decomposed Iterative KGc — Research Design

Experimental path alongside the stable monolithic KGc backtracking demo.

## Why decompose compound questions?

Compound questions (e.g. Apollo rocket + engines + launch site + mission goal) force a single claim-extraction pass to cover many topics at once. Missed claims are hard to recover. The research hypothesis: **atomic sub-questions with per-question iteration and carry-forward context** may improve claim coverage and correction reliability.

## Stable vs experimental

| Condition | Runner | Default UI mode | Primary example |
|-----------|--------|-----------------|-----------------|
| **A — Monolithic** | `BacktrackingRunner` | KGc backtracking demo | `saturn_v_apollo_11_001` |
| **B — Decomposed** | `DecomposedBacktrackingRunner` | Decomposed iterative KGc | `apollo_complex` (stress) |

The stable Apollo preset demo is a **regression fixture** and must not be replaced.

## Architecture

```
Original compound question
  → QuestionSplitter (LLM, strict JSON)
  → ordered sub-questions

For each sub-question:
  Answer(0) generated per sub-question (+ carry-forward from resolved prior answers)
  → extract claims (CSV preferred, JSON fallback)
  → align to working KGc schema
  → GraphComparator (deterministic labels)
  → BacktrackingFeedbackBuilder
  → BacktrackingReviser → Answer(n+1)
  → repeat until RESOLVED / STALLED / UNRESOLVED_NO_EVIDENCE / MAX_ITERATIONS

After all sub-questions:
  → combine_sub_answers (deterministic concatenation)
```

## Structured output strategy

| Task | Format | Parser |
|------|--------|--------|
| Context → KGc facts | CSV: `subject,relation,object,evidence` | `parse_context_facts_response` |
| Answer(n) → claims | CSV: `subject,relation,object,source_sentence` | `parse_claims_response` |
| Compound → sub-questions | JSON: `{"questions": [{"id": 1, "question": "..."}]}` | `parse_question_split_response` |

Rules:
- Exact headers, no prose before/after CSV
- One retry on malformed output (`complete_with_retry`)
- Legacy JSON triple lists still accepted for mock/backward compatibility

**The LLM does not assign SUPPORTED / CONTRADICTED / NO_EVIDENCE.** Labels come from deterministic Python comparison in `GraphComparator`.

## Stop conditions

| State | Rule |
|-------|------|
| `RESOLVED` | 0 contradicted, 0 no-evidence, ≥1 evaluated claim |
| `STALLED` | Revised answer unchanged, or same evaluation signature repeats |
| `UNRESOLVED_NO_EVIDENCE` | No contradictions remain but NO_EVIDENCE persists at max iterations |
| `MAX_ITERATIONS` | Iteration limit reached with remaining contradictions |

## Base KGc vs working KGc

- **`base_kgc`**: extracted once from trusted context only
- **`working_kgc`**: starts as copy of base; optional promotion scaffold
- **`candidate_kgc_updates`**: provenance-aware log of would-be updates

Provenance types:
- `trusted_context`
- `supported_by_existing_kgc`
- `derived_from_supported_facts`
- `externally_retrieved_and_validated`

**Automatic promotion is disabled by default.** Unvalidated LLM claims are never inserted into working KGc. This milestone implements the interface and logging only — evolving KGc is **not solved**.

Resolved sub-question answers are carried forward as **text context** to later sub-questions, not automatically as KGc FACT edges.

## Experiment comparison

Record via `DecomposedExperimentMetrics`:
- sub-question count, iteration count, label totals
- structured-output retries
- stop-reason counts (resolved / stalled / unresolved / max iterations)

API: `POST /run-decomposed-kgc-backtracking`

## Key modules

| File | Role |
|------|------|
| `src/pipeline/structured_output.py` | CSV/JSON parsers + retry |
| `src/pipeline/question_splitter.py` | Compound → sub-questions |
| `src/pipeline/kgc_iteration.py` | Per-sub-question iteration engine |
| `src/pipeline/decomposed_backtracking_runner.py` | Orchestrator |
| `src/pipeline/working_kgc.py` | Working KGc scaffold |
| `src/pipeline/sub_answer_combiner.py` | Final answer assembly |

## Limitations (this milestone)

- Mock mode uses question-split profiles and answer-scoped claim filtering; full `apollo_complex` mock profiles are not hard-coded
- Working KGc promotion is scaffold-only
- Sub-answer combination is deterministic concatenation, not LLM synthesis
- Neo4j storage schema unchanged; decomposed runs store base FACT edges only

---

## Final stabilization milestone (frozen)

**Summary:** The prototype now supports decomposing a compound question, projecting an external flawed Answer(0) into atomic sub-answers, enriching a working KGc from trusted context per sub-question, deterministically evaluating claims, revising and re-evaluating each answer until resolved or honestly stopped, and comparing decomposed processing against the monolithic baseline.

This is a prototype milestone, not a claim that hallucinations are prevented or that KGc evolution is solved.

### Stabilization fixes (narrow scope)

| Issue | Fix |
|-------|-----|
| Preset Answer(0) projection integrity | `labeled_field_projection.py` — deterministic `Label: value` parsing before LLM fallback; faithfulness validation |
| Date-range wording variants | `date_range_normalize.py` — `DateInterval` parse/compare for occurrence-date targets |
| Collection-amount over-capture | `collection_amount_extract.py` — stop before trailing clauses (`was collected during…`) |
| Abstention → false claims | `abstention_detection.py` — conservative phrase detection; skip claim extraction; `UNRESOLVED_NO_EVIDENCE` stop |

### Answer(0) projection modes

| Mode | Behavior |
|------|----------|
| `preset_external_projected` | Use `example.initial_answer`; deterministic labeled-field projection when field count matches sub-questions |
| `generated_external_projected` | Generate compound Answer(0), then project |
| `context_grounded_per_subquestion` | Generate Answer(0) per sub-question from context |

Trace fields: `projection_method`, `projection_source`, `projection_faithfulness_passed`.

### Expected `apollo_complex` behavior (Ollama `gemma4:e2b`)

| Sub-Q | Expected path |
|-------|---------------|
| Q1 dates | Wrong 1985 → CONTRADICTED → corrected 1969 variant → SUPPORTED → RESOLVED |
| Q2 crew | Wrong crew → CONTRADICTED → corrected → RESOLVED |
| Q3 launch | Wrong airport → CONTRADICTED → Kennedy Space Center → RESOLVED |
| Q4 president | Wrong Trump unsupported; **no** unsafe relation equivalence; honest UNRESOLVED acceptable |
| Q5 amount | Wrong 7 oz → CONTRADICTED → 21.5 kg → SUPPORTED → RESOLVED |

**Target: 4/5 legitimately resolved** — do not optimize for 5/5.

### Monolithic vs decomposed comparison

Run: `python scripts/stabilization_milestone_report.py --provider ollama --model gemma4:e2b`

Compare on same `apollo_complex` example:
- **A (monolithic):** compound question + compound Answer(0) + single extraction/evaluation/revision path
- **B (decomposed):** atomic sub-questions + projected Answer(0) + per-question iteration + carry-forward

Record: structured-output retries, claims, initial/final labels, revisions, resolved targets, stop reasons, combined answer quality. Not statistically significant — prototype comparison only.

### Known limitations (post-stabilization)

- Q4 president may remain honestly unresolved without explicit `president_at_time` facts
- LLM extraction/revision still non-deterministic; comparator is deterministic
- Sub-answer combination is concatenation, not synthesis
- No LLM judge, embeddings, or derived temporal reasoning in this milestone

### Milestone frozen

Implementation work stops here unless a true blocking defect remains. See `results/stabilization_milestone_report.json` for latest run records.

---

## Patient-chart generalization (`patient_d_314_complex`)

Second-domain stress case for selective preservation + correction. Trusted context is the only source of truth; no patient-specific values are hard-coded into matching logic.

| Item | Value |
|------|-------|
| Example id | `patient_d_314_complex` |
| Answer(0) mode | `preset_external_projected` (7 labeled fields) |
| Intent registry | `src/pipeline/kgc_matching.py` (`INTENT_RELATION_FAMILIES`) |
| Composite slots | `src/pipeline/composite_claim_slots.py` (kidney, discontinued+reason, active+dose, allergy+reaction) |
| Context bootstrap | `src/pipeline/trusted_context_bootstrap.py` (pattern-based, not case-value hard-coding) |
| Unit regression | `tests/test_patient_chart_generalization.py` |
| Ollama acceptance | `scripts/patient_chart_acceptance.py` (Apollo once + 3 consecutive patient runs) |

### Expected selective behavior

| Sub-Q | Preserve | Correct |
|-------|----------|---------|
| Diagnosis | type 2 diabetes mellitus | — |
| A1C | — | 6.2% → 9.1% |
| Kidney | CKD stage 3b | eGFR 78 → 38 |
| Stopped med | metformin | hypoglycemia → GI intolerance |
| Active med | empagliflozin active/tolerated | 25 mg → 10 mg |
| Discussed | status “not started” | insulin glargine → semaglutide |
| Allergy | penicillin | anaphylaxis → hives |

Medication-status families (`active` / `discontinued` / `discussed_not_started`) must not collapse. Composite targets require **all** attribute slots supported before `RESOLVED`.
