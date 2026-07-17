# KGc Demo Quick Reference

## 30-second explanation

This prototype tests whether a **context knowledge graph (KGc)** can audit a flawed external LLM answer: extract claims from **Answer(0)**, compare them to trusted graph facts, label each claim **SUPPORTED / CONTRADICTED / NO_EVIDENCE**, turn labels into **backtracking feedback**, and produce a revised **Answer(1)**. Preset flawed Answer(0) simulates an external LLM that may hallucinate; KGc is the auditing/backtracking layer—not the answer generator being evaluated.

## Pipeline

```
External Answer(0) → KGc (from trusted context) → claim extraction
  → Eval(Answer(0), KGc) → backtracking feedback → Answer(1)
```

At iteration 0: **Answer(n) = Answer(0)**.

## Files to know first

| File | Role |
|------|------|
| `api/server.py` | FastAPI; `POST /run-kgc-backtracking` |
| `src/pipeline/backtracking_runner.py` | Orchestrator: `BacktrackingRunner.run_example()` |
| `src/pipeline/context_triple_extractor.py` | Builds KGc from context |
| `src/pipeline/triple_extractor.py` | Extracts claims from Answer(0) |
| `src/pipeline/graph_comparator.py` | Labels claims vs KGc (deterministic) |
| `src/pipeline/backtracking_feedback_builder.py` | Feedback from labels |
| `src/pipeline/backtracking_reviser.py` | Produces Answer(1) (LLM) |
| `src/llm/mock_provider.py` | Deterministic demo without API keys |
| `frontend/app/page.tsx` | Main page; tool mode + run handlers |
| `frontend/components/KgcFlowView.tsx` | Demo result cards |
| `data/examples.json` | Preset examples including Apollo |

## UI cheat sheet

| UI section | Meaning |
|------------|---------|
| **Tool mode** | `kgc` (default), `decomposed_kgc` (experimental), `baseline`, or `legacy` |
| **Provider / Model / Example** | LLM backend and dataset row |
| **Answer(0) source** | `preset` = flawed `initial_answer`; `generated` = raw-context LLM answer |
| **Run KGc backtracking** | Triggers full KGc path |
| **Run inputs** | Question, trusted context preview, flawed Answer(0) |
| **Correction summary** | Headline + kept/fixed/removed stats + changed claims only |
| **KGc facts** | Graph facts extracted from trusted context |
| **Claim check** | Labels + Fixed/Kept/Removed groups |
| **Feedback** | Keep / Fix / Remove-defer action summary |
| **Answer(1)** | Revised answer after backtracking |
| **Advanced details** | Trace, JSON, KGc reference answer, incompleteness note |

**Baseline comparison** and **Legacy tools** modes: older GraphEval path; hidden unless selected.

**Decomposed iterative KGc** (experimental): splits compound questions, iterates per sub-question, combines answers. Try `apollo_complex` or `patient_d_314_complex`. See `docs/DECOMPOSED_ITERATIVE_KGC_DESIGN.md`.

## Decomposed milestone (frozen)

The prototype now supports decomposing a compound question, projecting an external flawed Answer(0) into atomic sub-answers, enriching a working KGc from trusted context per sub-question, deterministically evaluating claims, revising and re-evaluating each answer until resolved or honestly stopped, and comparing decomposed processing against the monolithic baseline.

| Item | Value |
|------|-------|
| Stress example | `apollo_complex` |
| Generalization example | `patient_d_314_complex` (partially correct Answer(0); selective preserve/correct) |
| Answer(0) mode | `preset_external_projected` (deterministic labeled-field projection when possible) |
| Stable regression | `saturn_v_apollo_11_001` unchanged (5 KGc facts, 4 claims, 1/3/0) |
| Expected decomposed result | **4/5 resolved** on Apollo (Q4 president may stay honestly unresolved); patient case aims for all targets resolved without status inversion |
| Verification | `pytest tests/`, `npm run build`, `scripts/stabilization_milestone_report.py`, `scripts/patient_chart_acceptance.py` |

Key modules: `labeled_field_projection.py`, `date_range_normalize.py`, `collection_amount_extract.py`, `abstention_detection.py`, `composite_claim_slots.py`, `trusted_context_bootstrap.py`, `kgc_matching.py` intent families.

## Output fields I must know

| Field | Short definition |
|-------|------------------|
| `answer_0` | Starting answer being checked (preset or generated) |
| `kgc_facts` | Trusted-context triples (`KgcFact` list) |
| `extracted_claims` | Claims parsed from Answer(0) before schema alignment |
| `aligned_claims` | Claims mapped to KGc canonical subject/relation where possible |
| `evaluated_claims` | Aligned claims + label + reason + KGc match/conflict |
| `backtracking_feedback` | Per-claim instructions for revision |
| `answer_1` / `final_answer` | Revised answer after iteration 0 |
| `revision_effect` | Counts: kept / fixed / removed-deferred |
| `trace` | Provenance strings (sources for answer, KGc, claims, revision) |

Backward-compat aliases: `graph_grounded_answer` = `kgc_reference_answer` (optional comparison answer from KGc only—not the main evaluated answer).

## Apollo demo expected result

Example id: **`saturn_v_apollo_11_001`** (default on page load).

| Item | Value |
|------|-------|
| KGc facts (mock) | **5 facts** |
| Labels (mock) | **1 Supported, 3 Contradicted, 0 No evidence** |
| Summary stats | **1 kept, 3 fixed, 0 removed/deferred** |
| Fixed | Saturn IB rocket → Saturn V rocket |
| Fixed | Cape Canaveral → Launch Complex 39A at Kennedy Space Center |
| Fixed | J-2 engines → F-1 engines |
| Kept | first crewed Moon landing |

**Expected Answer(1) (mock):** “Apollo 11 was launched by the Saturn V rocket from Launch Complex 39A at Kennedy Space Center. Its first stage was powered by five F-1 engines, and the mission achieved the first crewed Moon landing.”

## Limitations to say out loud

- KGc extraction can miss context facts → correct claims may become **NO_EVIDENCE**.
- Claim extraction and revision still use an **LLM** (or mock profiles).
- **Comparator is deterministic**; extraction/revision are not.
- Preset Answer(0) is a **controlled demo**, not proof the model hallucinates on demand.
- Default **`max_iterations=1`** in API/UI; loop exists in runner but UI runs one pass.
- Neo4j is **storage/inspection**, not the evaluator.
- Subject/relation alignment helps but can fail on ambiguous claims.

## 10 most likely questions

1. **Why preset Answer(0)?** — Simulates an external LLM output we audit; makes contradictions visible in a demo.
2. **Is preset cheating?** — No; it's a controlled external answer. Research still needs generated Answer(0) and real LLM runs.
3. **What is KGc?** — Knowledge graph built only from trusted context in `ContextTripleExtractor`.
4. **What gets backtracked?** — Claims in Answer(0), not the KGc reference answer.
5. **SUPPORTED?** — Claim matches a KGc fact (exact or normalized).
6. **CONTRADICTED?** — Same subject+relation, different object than KGc.
7. **NO_EVIDENCE?** — No matching KGc fact (often extraction gap).
8. **What is `aligned_claims`?** — Claims rewritten to KGc schema before compare (`kgc_schema_aligner.py`).
9. **What is KGc reference answer?** — Optional answer generated from question+KGc only; in Advanced details.
10. **How is Answer(1) made?** — `BacktrackingReviser.revise()` with prompt `prompts/backtracking_revision.txt`.
