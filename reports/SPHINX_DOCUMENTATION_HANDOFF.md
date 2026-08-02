# Sphinx Documentation Handoff

Purpose: identify the pages the later Sphinx site needs and the concrete source
material for each. The site must explain the code and the trace format through
concrete examples — the preserved executions cited below provide those examples.
Do not build the site in the research pass.

## Required pages

1. **Overview** — what GraphEval is (instrument, not memory system); FACT vs CLAIM
   vs triple definitions; the four RQs. Source: Experiment Report §1, README.
2. **Architecture** — LLM stages (question_splitter, context_extractor,
   focused_extractor, answer_generator, sub_answer_projector, claim_extractor,
   reviser — names as recorded in the `example_constructed` trace event) vs
   deterministic Python vs Neo4j. Source: Experiment Report §2.2; `src/`.
3. **Setup** — venv, Ollama, Docker Neo4j (`scripts/recreate-neo4j.sh`,
   `neo4j:5.26.0`), env vars (`OLLAMA_NUM_CTX`, `NEO4J_ENABLED`, ...); offline mock
   mode. Source: README, AGENTS.md, `.env.example`.
4. **Pipeline** — the 17-step per-question procedure with stop conditions
   (RESOLVED / STALLED / UNRESOLVED_TARGET_NOT_SATISFIED / UNRESOLVED_NO_EVIDENCE).
   Source: Experiment Report §2.3.
5. **Prompts** — one page per LLM stage with the actual prompt template and one
   real input/output pair from a preserved raw artifact
   (`.runtime/debug/*_claim_extraction_raw.txt` etc.).
6. **Neo4j data model** — `(:Entity)-[:FACT]->(:Entity)` vs `(:Entity)-[:CLAIM]->`
   with label property; execution-ID scoping; no CLAIM→FACT promotion; readback
   evaluation. Source: `docs/PROFESSOR_HANDOFF.md`, `src/` graph code, tests.
7. **Trace format** (most important page) — explain by walking one real execution.
   Recommended: `apollo_hop_046__20260727T202312Z__50843932` (short, RESOLVED) for
   the happy path and `nhs_wannacry_h10_q01__20260727T214622Z__4adc0f88` for the
   failure path. Must define, each with a concrete excerpt:
   - subject / relation / object;
   - FACT (trusted, from context) and CLAIM (from the answer);
   - SUPPORTED, CONTRADICTED, NO_EVIDENCE labels (from `claim_comparison` events);
   - extracted claims (`claim_parsed`) vs aligned claims (`claim_alignment`,
     including `field_transformed` records with before/after/reason);
   - feedback and revision (Answer(n) → Answer(n+1); show the WannaCry Q1
     "MS17-010 ... " → "patching" regression);
   - target satisfaction (`derived_question_target`, UNRESOLVED_TARGET_NOT_SATISFIED);
   - evidence path (`evidence_path` object: start_entity, terminal_claim, edges,
     complete, failure_reason such as `terminal_claim_not_a_trusted_fact` and
     `missing_intermediate_edge`);
   - stop reason (`sub_question_finished` event names);
   - execution ID format `<question_id>__<UTC timestamp>__<8-hex>` and its role in
     Neo4j scoping;
   - anomaly events (`structured_triple_anomaly` / `empty_object`).
8. **Experiment** — condensed Experiment Report (link the DOCX/MD as the source of
   record); figures from `results/research/figures/`.
9. **API / code reference** — FastAPI endpoints (`/health`, `/dependencies`,
   benchmark UI API) + module autodoc for `src/`, `api/`, `scripts/`.
10. **Limitations** — nondeterminism, 5-per-depth samples, single model/domain,
    no self-correction baseline, official-run traces not persisted per question,
    decomposition validation gaps (WannaCry Q1), target/combination semantics
    (`apollo_hop_037` "state").
11. **Reproducibility** — mirror `research/REPRODUCIBILITY_RECORD.md` (hashes,
    exact commands, run-class separation).

## Practical notes for the future documentation pass

- The debug traces are JSONL with fields `run_id, attempt, debug_log_path,
  question_id, sub_question_id, stage, event, data`; the stage vocabulary observed
  in real traces: request_received, example_constructed, question_split_parsed,
  context_fact_extraction, context_fact_raw_response, structured_triple_validated,
  structured_triple_anomaly, context_fact_parsed, neo4j_fact_write,
  neo4j_fact_readback, working_kgc_initialized, focused_fact_extraction,
  claim_extraction, claim_extraction_raw_response, claim_parsed, schema_alignment,
  claim_alignment, claim_comparison, sub_question_finished, combined_answer,
  run_finished.
- `.runtime/` is gitignored; the three key traces are hash-recorded in
  `research/REPRODUCIBILITY_RECORD.md` — copy them into a docs assets folder (or
  commit excerpts) when building the site so examples do not depend on an
  unversioned directory.
- Keep the professor's report templates out of scope until the original DOCX files
  are supplied; record their absence as in
  `research/EXPERIMENT_EVIDENCE_INVENTORY.md` §7.
