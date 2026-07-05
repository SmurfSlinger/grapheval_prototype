# KGc Backtracking Demo Study Guide

Documentation for the GraphEval / KGc backtracking prototype as of the current codebase. All paths and names below were verified against the repository.

---

## 1. 30-second project explanation

This prototype tests whether a **context knowledge graph (KGc)** can check a flawed LLM answer, label each claim as **supported**, **contradicted**, or **no evidence**, generate **backtracking feedback**, and produce a **revised answer**.

The intended demo story:

1. Start with **Answer(0)** — an external/main LLM answer (or a preset flawed answer standing in for one).
2. Build **KGc** from trusted context only.
3. Extract **claims** from Answer(0).
4. **Evaluate** each claim against KGc.
5. Build **backtracking feedback** from labels.
6. Produce **Answer(1)** (and optionally repeat for Answer(n+1)).

**Demo framing:** Preset flawed Answer(0) is the primary path. Treat it as output from an external LLM that may contain hallucinated claims. This tool **audits and backtracks** that external answer—it does not pretend the preset text was produced by KGc.

---

## 2. Important files and what they do

| File path | What it does | Key functions / classes / components | Receives | Returns / renders |
|-----------|--------------|--------------------------------------|----------|-------------------|
| `api/server.py` | FastAPI backend | `app`, `run_kgc_backtracking()`, `_make_backtracking_runner()`, `list_examples()` | HTTP JSON (`RunKgcBacktrackingRequest`) | `BacktrackingResult.to_dict()` JSON |
| `src/pipeline/backtracking_runner.py` | KGc backtracking orchestrator | `BacktrackingRunner`, `_resolve_answer_0()`, `_enrich_evaluations()` | `Example`, `answer_0_mode` | `BacktrackingResult` |
| `src/pipeline/context_triple_extractor.py` | KGc builder from context | `ContextTripleExtractor.extract()` | Trusted `context` string | `list[KgcFact]` |
| `src/pipeline/kgc_serializer.py` | Serialize KGc for prompts | `serialize_kgc_facts()` | `list[KgcFact]` | Multi-line string |
| `src/pipeline/answer_generator.py` | Answer(0) when mode=`generated` | `AnswerGenerator.generate()` | `question`, `context` | Answer text |
| `src/pipeline/kg_answer_generator.py` | Optional KGc reference answer | `KgAnswerGenerator.generate()` | `question`, serialized KGc | Reference answer string |
| `src/pipeline/triple_extractor.py` | Claim extraction from answers | `TripleExtractor.extract_kgc_claims()` | `answer`, optional `kgc_facts`, `question` | `(extracted_claims, aligned_claims)` |
| `src/pipeline/kgc_schema_aligner.py` | Map claims to KGc schema | `align_claims_to_kgc_schema()`, `_align_claim()` | Claims + KGc facts | Aligned `Triple` list |
| `src/pipeline/kgc_matching.py` | Normalization helpers | `normalize()`, `normalize_relation()`, `subjects_compatible_first_stage()` | Strings | Normalized strings / booleans |
| `src/pipeline/graph_comparator.py` | Deterministic claim vs KGc eval | `GraphComparator.compare_claims()` | Aligned claims, KGc facts | `list[KgcEvaluationResult]` |
| `src/pipeline/backtracking_feedback_builder.py` | Feedback from labels | `BacktrackingFeedbackBuilder.build()`, `backtracking_action_for_label()` | Evaluations | `list[BacktrackingFeedbackItem]` |
| `src/pipeline/backtracking_reviser.py` | Answer(n+1) generation | `BacktrackingReviser.revise()` | question, KGc, answer, feedback | Revised answer string |
| `src/models.py` | Dataclasses | `Example`, `KgcFact`, `BacktrackingResult`, `KgcClaimLabel`, etc. | — | Typed structures + `to_dict()` |
| `src/llm/base.py` | LLM interface | `LLMProvider.complete()` | Prompt string | Completion string |
| `src/llm/mock_provider.py` | Deterministic demo LLM | `MockProvider.complete()`, `PROFILES` | Prompt (pattern-matched) | Canned JSON/text |
| `src/llm/ollama_provider.py` | Local Ollama LLM | `OllamaProvider.complete()` | Prompt | Model completion |
| `src/main.py` | CLI + provider factory | `get_provider()`, `build_parser()` | CLI args | `LLMProvider` instance |
| `src/storage/neo4j_store.py` | Graph storage (optional) | `Neo4jStore.store_kgc_facts()`, `store_kgc_claims()`, `get_claims_for_example()` | Facts, evaluations | Neo4j writes / query rows |
| `src/config.py` | Paths and env config | `NEO4J_ENABLED`, prompt paths, `EXAMPLES_PATH` | Env vars | Constants |
| `src/io_utils.py` | Load examples/prompts | `load_examples()`, `load_prompt()`, `parse_json_response()` | File paths | Parsed data |
| `data/examples.json` | Preset demo examples | JSON records with `id`, `question`, `context`, `initial_answer` | — | Example definitions |
| `prompts/context_triple_extraction.txt` | KGc extraction prompt | — | `{context}` | JSON triples |
| `prompts/kg_claim_extraction.txt` | Claim extraction prompt | — | `{question}`, `{kgc_facts}`, `{answer}` | JSON triples |
| `prompts/kg_answer_generation.txt` | KGc reference answer prompt | — | `{kgc_facts}`, `{question}` | Answer text |
| `prompts/backtracking_revision.txt` | Answer revision prompt | — | `{question}`, `{kgc_facts}`, `{answer}`, `{feedback}` | Revised answer |
| `prompts/answer_generation.txt` | Generated Answer(0) prompt | — | `{context}`, `{question}` | Answer text |
| `frontend/app/page.tsx` | Main UI entry | `HomePage`, `handleRunKgc()`, `toolMode` state | User actions | Renders controls + results |
| `frontend/components/ControlsPanel.tsx` | Left control panel | `ControlsPanel`, tool mode selector | Props / callbacks | Run controls |
| `frontend/lib/api.ts` | Frontend API client | `runKgcBacktracking()`, `fetchExamples()` | HTTP | Typed `BacktrackingResult` |
| `frontend/components/KgcBacktrackingResultView.tsx` | Result wrapper | Wraps `KgcFlowView` + Advanced details | `BacktrackingResult` | Result UI |
| `frontend/components/KgcFlowView.tsx` | Demo result cards | `RunInputsCard`, `CorrectionSummaryCard`, stage cards | `BacktrackingResult` | Run inputs → Answer(1) |
| `frontend/components/kgc/demoSummary.ts` | Summary helpers | `buildChangedClaims()`, `contextPreview()` | Result fields | Display strings |
| `frontend/components/kgc/StageCard.tsx` | Reusable card UI | `StageCard`, `StatChip`, `StatChipRow` | React props | Card layout |
| `frontend/app/globals.css` | Styling | CSS classes (`kgc-*`, `controls-*`) | — | Visual layout |
| `scripts/start-dev.sh` | Dev startup | Starts Neo4j, API, frontend | — | Local demo stack |
| `scripts/run-kgc-tests.sh` | KGc test script | Runs `kgc_test_report.py` | — | Console report |
| `tests/test_backtracking_runner.py` | Integration tests | Apollo/Hyundai/Drone flow tests | Mock provider | Assertions |

**Legacy (not KGc demo path):**

| File | Role |
|------|------|
| `src/pipeline/runner.py` | Original GraphEval pipeline (`PipelineRunner`) |
| `frontend/components/PipelineResultView.tsx` | Baseline / legacy result view |
| `api/server.py` endpoints `POST /run`, `/run-all`, `/run-custom` | Plain LLM baseline path |

---

## 3. What happens when I click Run KGc Backtracking

Assuming **Tool mode = KGc backtracking demo** (default) and **Provider = mock**.

| Step | File | Function / component | Input | Output | Next |
|------|------|----------------------|-------|--------|------|
| 1 | `frontend/components/ControlsPanel.tsx` | Button `onRunKgc` | User click | — | `page.tsx` handler |
| 2 | `frontend/app/page.tsx` | `handleRunKgc()` | `selectedId`, `provider`, `model`, `answer0Mode` | Sets `running=true` | Calls API |
| 3 | `frontend/lib/api.ts` | `runKgcBacktracking()` | `POST /run-kgc-backtracking` body: `{ example_id, provider, model, max_iterations: 1, answer_0_mode }` | Promise | HTTP |
| 4 | `api/server.py` | `run_kgc_backtracking()` | `RunKgcBacktrackingRequest` | — | Loads example |
| 5 | `api/server.py` | `_make_backtracking_runner()` | provider, model, max_iterations | `BacktrackingRunner` | — |
| 6 | `src/main.py` | `get_provider()` | `"mock"` or `"ollama"` | `MockProvider` / `OllamaProvider` | — |
| 7 | `src/pipeline/backtracking_runner.py` | `BacktrackingRunner.run_example()` | `Example`, `answer_0_mode="preset"` | — | Pipeline stages |
| 8 | Same | `_resolve_answer_0()` | `example.initial_answer` (Apollo preset) | `answer_0` text, trace source | — |
| 9 | `context_triple_extractor.py` | `ContextTripleExtractor.extract()` | `example.context` | `kgc_facts` | Mock returns profile `context_facts` |
| 10 | `kgc_serializer.py` | `serialize_kgc_facts()` | `kgc_facts` | `serialized_kgc` string | — |
| 11 | `neo4j_store.py` | `store_kgc_facts_if_enabled()` | facts (if `NEO4J_ENABLED`) | FACT edges | Optional |
| 12 | `kg_answer_generator.py` | `KgAnswerGenerator.generate()` | question + serialized KGc | `kgc_reference_answer` | Not main eval target |
| 13 | `triple_extractor.py` | `TripleExtractor.extract_kgc_claims()` | `answer_0`, kgc_facts | extracted + aligned claims | LLM/mock |
| 14 | `graph_comparator.py` | `GraphComparator.compare_claims()` | aligned claims, kgc_facts | `evaluated_claims` with labels | Deterministic |
| 15 | Same runner | `_enrich_evaluations()` | Adds `source_sentence`, `backtracking_action` | — | — |
| 16 | `neo4j_store.py` | `store_kgc_claims_if_enabled()` | evaluations, `answer_stage="answer_0"` | CLAIM edges | Optional |
| 17 | `backtracking_feedback_builder.py` | `BacktrackingFeedbackBuilder.build()` | evaluations | `backtracking_feedback` | — |
| 18 | `backtracking_reviser.py` | `BacktrackingReviser.revise()` | question, KGc, answer_0, feedback | `answer_1` | LLM/mock |
| 19 | Same runner | Builds `BacktrackingResult` | All stage outputs | `BacktrackingResult` | — |
| 20 | `models.py` | `BacktrackingResult.to_dict()` | Dataclass | JSON dict | HTTP response |
| 21 | `frontend/app/page.tsx` | `setKgcResult(output)` | JSON | React state | Re-render |
| 22 | `KgcBacktrackingResultView.tsx` | Renders `KgcFlowView` | `kgcResult` | Run inputs → Answer(1) cards | User sees demo |

---

## 4. Pipeline explanation

### 1. Answer(0): starting answer

- **Meaning:** External LLM answer being audited. At iteration 0, **Answer(n) = Answer(0)**.
- **Code:** `_resolve_answer_0()` in `backtracking_runner.py`; preset uses `example.initial_answer` from `data/examples.json`; generated uses `AnswerGenerator` + `prompts/answer_generation.txt`.
- **Produces:** `answer_0`, `trace.answer_0_source`, `answer_0_mode`.
- **Say:** “This is the flawed external answer we check—not the graph-generated reference.”

### 2. KGc: trusted graph

- **Meaning:** Facts extracted **only** from trusted context (not from the answer).
- **Code:** `ContextTripleExtractor.extract()` → `KgcFact` list; `serialize_kgc_facts()` for downstream prompts.
- **Produces:** `kgc_facts`, `serialized_kgc`.
- **Say:** “KGc is the ground-truth graph built from the paragraph we trust.”

### 3. Claims from Answer(0)

- **Meaning:** Answer(0) broken into checkable subject–relation–object triples.
- **Code:** `TripleExtractor.extract_kgc_claims()` with `prompts/kg_claim_extraction.txt`; then `align_claims_to_kgc_schema()` in `kgc_schema_aligner.py`.
- **Produces:** `extracted_claims`, `aligned_claims`.
- **Say:** “We parse the answer into claims, then align wording to KGc schema where possible.”

### 4. Eval: Answer(0) vs KGc

- **Meaning:** Each aligned claim compared to KGc; labeled SUPPORTED / CONTRADICTED / NO_EVIDENCE.
- **Code:** `GraphComparator.compare_claims()` — **deterministic**, uses normalization in `kgc_matching.py`.
- **Produces:** `evaluated_claims`, count fields, per-claim `reason`, `matched_kgc_fact` / `conflicting_fact`.
- **Say:** “The comparator is rule-based, not an LLM judge.”

### 5. Backtracking feedback

- **Meaning:** Instructions derived from labels: keep, fix, or remove/defer each claim.
- **Code:** `BacktrackingFeedbackBuilder.build()`.
- **Produces:** `backtracking_feedback` list with `instruction`, `backtracking_action`.
- **Say:** “Labels become structured feedback the reviser must follow.”

### 6. Answer(1): revised answer

- **Meaning:** Corrected answer after applying feedback and KGc as source of truth.
- **Code:** `BacktrackingReviser.revise()` + `prompts/backtracking_revision.txt`.
- **Produces:** `answer_1`, `final_answer`, `answer_n_plus_1` (aliases in `to_dict()`).
- **Say:** “Answer(1) is the backtracked output—we fixed contradictions and kept supported claims.”

### 7. Optional later iterations

- **Meaning:** Loop `Eval(Answer(n), KGc) → feedback → Answer(n+1)` until all supported or `max_iterations`.
- **Code:** `for n in range(self.max_iterations)` in `BacktrackingRunner.run_example()`.
- **Current UI/API default:** `max_iterations=1` in `frontend/lib/api.ts` and `RunKgcBacktrackingRequest`.
- **Note:** First-iteration fields in the API response always reflect **iteration 0** (Answer(0) eval); `iteration_history` records each pass.

### Optional: KGc reference answer

- **Code:** `KgAnswerGenerator.generate()` — **not** the main evaluated answer.
- **Produces:** `kgc_reference_answer` (alias: `graph_grounded_answer`).
- **UI:** Shown only under **Advanced details** in `KgcBacktrackingResultView.tsx`.

---

## 5. UI field explanation

| UI element | Meaning | Why it exists | Code source | If asked, say |
|------------|---------|---------------|-------------|---------------|
| **Tool mode** | Selects KGc demo vs baseline vs legacy | Keeps demo path primary | `ControlsPanel.tsx`, `page.tsx` `toolMode` | “Default is KGc backtracking; other modes are comparison tools.” |
| **KGc backtracking demo** | Primary mode | Professor-facing demo | Default `toolMode="kgc"` | “This is the milestone we’re showing.” |
| **Provider** | `mock` or `ollama` | Swappable LLM backend | `get_provider()` in `src/main.py` | “Mock is deterministic for demos; Ollama runs real local models.” |
| **Model** | Ollama model tag | Used when provider=ollama | Passed to `OllamaProvider` | “Ignored for mock provider.” |
| **Example** | Dataset row from `examples.json` | Preset Q/context/Answer(0) | `GET /examples`, default `saturn_v_apollo_11_001` | “Apollo is the default demo example.” |
| **Answer(0) source** | `preset` or `generated` | Preset simulates external flawed LLM | `answer_0_mode` → `_resolve_answer_0()` | “Preset is our controlled external answer for the demo.” |
| **Run KGc backtracking** | Starts pipeline | Main demo action | `handleRunKgc` → `runKgcBacktracking` | “Runs the full audit loop.” |
| **Run inputs** | Question, context, Answer(0) | Shows what the run evaluated | `KgcFlowView` `RunInputsCard` | “Everything we checked is visible at the top.” |
| **Correction summary** | Headline + stats + changed claims | One-glance demo outcome | `CorrectionSummaryCard`, `demoSummary.ts` | “Three claims fixed, one kept.” |
| **KGc facts** | Trusted graph facts | Ground truth for comparison | `result.kgc_facts` | “Built only from the trusted paragraph.” |
| **Claim check** | Labels + Fixed/Kept groups | Shows audit results | `evaluated_claims` | “Comparator labels each claim.” |
| **Feedback** | Keep/Fix/Remove summary | What reviser sees | `backtracking_feedback` | “Structured instructions for Answer(1).” |
| **Answer(1)** | Revised answer | Demo output | `answer_1` / `final_answer` | “Corrected using KGc feedback.” |
| **Advanced details** | Trace, JSON, reference answer | Debug/research | `KgcBacktrackingResultView.tsx` | “Full payload for digging deeper.” |
| **Baseline comparison** | Tool mode: plain GraphEval | Secondary comparison | `PipelineResultView` when `toolMode="baseline"` | “Original verify-against-raw-context path.” |
| **Legacy tools** | Tool mode: run-all, custom input | Older prototype tools | `toolMode="legacy"` | “Kept for debugging, not the main story.” |

---

## 6. Output field dictionary

| Field | Plain English | Created in | Displayed in UI | If asked |
|-------|---------------|------------|-----------------|----------|
| `example_id` | Which preset example ran | `BacktrackingResult` constructor | Advanced (JSON) | “Apollo is `saturn_v_apollo_11_001`.” |
| `question` | User question | From `Example` | Run inputs | “Same as examples.json.” |
| `context` | Trusted source text | From `Example` | Run inputs (preview + expand) | “Only source for KGc.” |
| `answer_0` | Starting flawed answer | `_resolve_answer_0()` | Run inputs | “External LLM answer we audit.” |
| `answer_n` | Evaluated answer at iteration (alias) | `to_dict()`: equals `evaluated_answer` | Unclear in main UI | “At iter 0, same as answer_0.” |
| `evaluated_answer` | Answer whose claims were evaluated | Set to `answer_0` at iter 0 | Implicit in claim check | “We evaluate Answer(0), not the KGc reference.” |
| `evaluated_answer_iteration` | Which iteration was evaluated | Runner loop index 0 | Advanced | “Currently 0 in default demo.” |
| `kgc_facts` | Context graph triples | `ContextTripleExtractor` | KGc facts card | “4 facts for Apollo mock.” |
| `serialized_kgc` | Text block of facts for prompts | `serialize_kgc_facts()` | Advanced | “Fed to claim extraction and revision prompts.” |
| `kgc_reference_answer` | Answer from question+KGc only | `KgAnswerGenerator` | Advanced details | “Optional comparison—not backtracked.” |
| `graph_grounded_answer` | Backward-compat alias | Same as `kgc_reference_answer` in `to_dict()` | Advanced | “Legacy name for reference answer.” |
| `extracted_claims` | Raw extracted triples | `TripleExtractor` | Advanced | “Before schema alignment.” |
| `aligned_claims` | Schema-aligned triples | `align_claims_to_kgc_schema()` | Advanced | “What comparator actually uses.” |
| `evaluated_claims` | Claims + labels + reasons | `GraphComparator` + enrich | Claim check (+ Advanced) | “Core audit output.” |
| `backtracking_feedback` | Revision instructions | `BacktrackingFeedbackBuilder` | Feedback card | “Drives Answer(1).” |
| `answer_1` | First revised answer | `BacktrackingReviser` | Answer(1) card | “Output after one iteration.” |
| `answer_n_plus_1` | Alias for next answer | `to_dict()` | Same as answer_1 | “General name for revised answer.” |
| `final_answer` | Last answer after loop | `current_answer` at end | Answer(1) (via alias) | “Same as answer_1 when max_iterations=1.” |
| `supported_count` | # SUPPORTED claims | `_count_labels()` | Claim check chips | “Kept claims.” |
| `contradicted_count` | # CONTRADICTED | Same | Correction summary | “Fixed claims.” |
| `no_evidence_count` | # NO_EVIDENCE | Same | Correction summary | “Removed/deferred.” |
| `revision_effect` | `{ preserved, corrected, removed }` counts | `RevisionEffect` from iter 0 | Correction summary, Answer(1) chips | “Summary of revision impact.” |
| `stop_reason` | Why loop stopped | `"all_claims_supported"` or `"max_iterations_reached"` | Advanced | “Often unset early-stop when fixes needed.” |
| `iteration_history` | Per-iteration stats | Appended in runner loop | Advanced | “Useful when max_iterations > 1.” |
| `trace` | Provenance metadata object | `BacktrackingTrace` | Advanced JSON | “Where each stage’s data came from.” |
| `answer_0_mode` | `preset` or `generated` | `_resolve_answer_0()` | Advanced | “Demo uses preset.” |
| `trace.answer_0_source` | e.g. `example.initial_answer` | `_resolve_answer_0()` | Advanced | “Preset path source.” |
| `trace.kgc_source` | `"extracted_from_trusted_context"` | Hardcoded in runner | Advanced | — |
| `trace.claim_extraction_source` | `"extracted_from_answer_n"` | Hardcoded | Advanced | — |
| `trace.revision_source` | Revision provenance string | Hardcoded | Advanced | — |
| `kgc_extraction_notice` | KGc incompleteness warning | `_detect_kgc_extraction_notice()` | Advanced (if detected) | “Research limitation, not fatal.” |
| `answer_0_warning` | Preset fallback warning | When preset selected but no `initial_answer` | Run warning banner | “Rare for bundled examples.” |

---

## 7. Claim labels

### SUPPORTED

- **Condition:** Normalized (subject, relation, object) matches a KGc fact, OR exact match after alignment.
- **Code:** `GraphComparator._evaluate_claim()` exact_index hit.
- **Feedback:** “Preserve this claim…” (`backtracking_action_for_label`).
- **Apollo:** `achieved → first crewed Moon landing` matches KGc.

### CONTRADICTED

- **Condition:** Same normalized subject+relation as a KGc fact but **different object**; or engine-power / polarity conflict rules in `graph_comparator.py`.
- **Feedback:** “Correct or remove using conflicting KGc fact.”
- **Apollo examples:**
  - **Saturn IB vs Saturn V:** `launched_by` same subject, object differs → CONTRADICTED.
  - **Cape Canaveral vs Launch Complex 39A:** `launched_from` object differs → CONTRADICTED.
  - **J-2 vs F-1 engines:** After alignment (`used`≈`powered_by`, `Apollo 11 first stage`≈`Saturn V S-IC stage` via `kgc_schema_aligner.py` + `subjects_compatible_first_stage()`), objects differ → CONTRADICTED (not NO_EVIDENCE).

### NO_EVIDENCE

- **Condition:** No exact match, no same-relation conflict, no engine/polarity rule match.
- **Meaning:** KGc has no fact supporting the claim (often because **KGc extraction missed** the context fact, or subject/relation alignment failed).
- **Feedback:** Omit or defer for retrieval/adjudication.
- **Say:** “A correct Answer(0) claim can be NO_EVIDENCE if KGc doesn’t contain the matching fact—that’s a graph extraction issue we study.”

---

## 8. Neo4j explanation

**Enabled when:** `NEO4J_ENABLED=true` (see `src/config.py`).

### Nodes

- **`(:Entity {name: ...})`** — Subject and object strings from triples (not a rich entity model).

### Relationship types

| Type | Meaning | Created by |
|------|---------|------------|
| **`[:FACT]`** | KGc context fact | `Neo4jStore._create_fact()` via `store_kgc_facts()` |
| **`[:CLAIM]`** | Evaluated answer claim | `Neo4jStore._create_kgc_claim()` via `store_kgc_claims()` |

Legacy GraphEval pipeline also writes `[:CLAIM]` via `_create_claim()` for baseline verification (`store_verified_triples()`).

### FACT edge properties

`relation`, `evidence`, `example_id`, `source: "context"`

### KGc CLAIM edge properties

`relation`, `label`, `reason`, `evidence`, `example_id`, `answer_stage` (e.g. `"answer_0"`), `iteration`, `source: "answer"`, `conflicting_object`, `conflicting_fact`

### Read paths

- `Neo4jStore.get_claims()`, `get_claims_for_example()`, `get_bad_claims()`
- API: `GET /graph/claims`, `GET /graph/bad-claims` in `api/server.py`
- Frontend: `fetchGraphClaims()` in `frontend/lib/api.ts` (used for Neo4j status badge)

### Why reason/evidence on edges

Verification metadata applies to a **specific asserted relationship** (this claim about this subject→object), not to the entity node itself. Multiple claims can share entity nodes with different labels and explanations.

**Neo4j is storage only** — evaluation happens in `GraphComparator`, not in the database.

---

## 9. Prompt templates

| File | When used | Input variables | Expected output | What can go wrong |
|------|-----------|-----------------|-----------------|-------------------|
| `prompts/context_triple_extraction.txt` | Building KGc | `{context}` | JSON `{"triples":[{subject, relation, object, evidence}]}` | Misses facts, wrong relations, drops negation |
| `prompts/answer_generation.txt` | Generated Answer(0) | `{context}`, `{question}` | Plain answer text | May not hallucinate on demand |
| `prompts/kg_claim_extraction.txt` | Claims from Answer(0) | `{question}`, `{kgc_facts}`, `{answer}` | JSON triples + optional `source_sentence` | Wrong subjects, section labels as entities |
| `prompts/kg_answer_generation.txt` | KGc reference answer | `{kgc_facts}`, `{question}` | Plain answer | Incomplete if KGc missing facts → triggers notice |
| `prompts/backtracking_revision.txt` | Answer(1) | `{question}`, `{kgc_facts}`, `{answer}`, `{feedback}` | Revised answer text only | May ignore feedback; adds unsupported text |

**Loaded via:** `load_prompt()` in `src/io_utils.py`; paths in `src/config.py`.

**Note:** `backtracking_revision.txt` still says “Graph-grounded answer (Answer n)” in the template text—the reviser passes **Answer(0)** (or current answer) in the `{answer}` slot.

---

## 10. Known limitations

| Limitation | Meaning | UI appearance | What to say |
|------------|---------|---------------|-------------|
| KGc misses context facts | Extraction incomplete | `kgc_extraction_notice` in Advanced if reference answer looks incomplete | “Graph extraction is part of the research problem.” |
| Correct claim → NO_EVIDENCE | Comparator finds no KGc match | Claim check: “No evidence” chip | “Not always wrong answer—maybe missing KGc fact.” |
| Alignment failures | Claim wording doesn’t map to KGc schema | May stay NO_EVIDENCE or wrong label | “We added normalization for relations/first-stage; not perfect.” |
| LLM-based extraction/revision | Not fully deterministic | Same UI; mock hides variance | “Comparator is deterministic; extraction and revision use LLM.” |
| Preset Answer(0) | Controlled flawed text | Run inputs shows preset answer | “Demo shortcut simulating external LLM; not cheating the comparator.” |
| Generated Answer(0) | May match context too well | Research mode | “Harder to show contradictions without careful examples.” |
| `max_iterations=1` default | Single revision pass | One Answer(1) | “Loop exists in runner; UI defaults to one iteration.” |
| Research scaffold | Not production proof | — | “Prototype to test the KGc backtracking idea.” |
| Neo4j ≠ verifier | Storage/inspection | Neo4j badge in header | “Labels come from Python comparator, not Cypher rules.” |

---

## 11. Apollo demo walkthrough

**Example id:** `saturn_v_apollo_11_001` (default selected in `frontend/app/page.tsx`).

### Question

“What rocket launched Apollo 11, what engines powered its first stage, where did it launch from, and what mission goal did it accomplish?”

### Trusted context (abbreviated)

Saturn V from Launch Complex 39A; S-IC stage with five F-1 engines; first crewed Moon landing.

### Flawed Answer(0) (preset)

Saturn IB, Cape Canaveral, J-2 engines, first crewed Moon landing.

### KGc facts (mock provider — 4 facts)

- Apollo 11 → launched_by → Saturn V  
- Apollo 11 → launched_from → Launch Complex 39A Kennedy Space Center  
- Saturn V S-IC stage → powered_by → five F-1 engines  
- Apollo 11 → achieved → first crewed Moon landing  

### Bad claims found (mock)

| Claim | Label | KGc conflict |
|-------|-------|--------------|
| Saturn IB | CONTRADICTED | Saturn V |
| Cape Canaveral | CONTRADICTED | Launch Complex 39A… |
| five J-2 engines | CONTRADICTED | five F-1 engines |
| first crewed Moon landing | SUPPORTED | (matches) |

### Feedback

Keep Moon landing; fix rocket, site, engines.

### Answer(1) (mock `revised` profile)

Saturn V, Launch Complex 39A, F-1 engines, Moon landing preserved.

---

## 12. Two-minute demo script

> “This prototype tests **KGc backtracking**: can we take a flawed LLM answer, build a knowledge graph from trusted context only, and audit that answer claim by claim?
>
> Here’s **Answer(0)**—we treat it as an external LLM answer. It says Saturn IB, Cape Canaveral, and J-2 engines. The **trusted context** says Saturn V, Launch Complex 39A, and F-1 engines.
>
> We build **KGc** from context—not from the answer. Then we extract **claims from Answer(0)** and compare them to KGc. The **comparator** labels each claim: supported, contradicted, or no evidence. Three contradictions, one supported Moon landing.
>
> Those labels become **backtracking feedback**—keep, fix, remove. The **reviser** produces **Answer(1)** that fixes the rocket, launch site, and engines while keeping the supported claim.
>
> We use a **preset flawed Answer(0)** in demo mode because it reliably shows the audit loop. That’s not the final research claim—it’s a controlled stand-in for an external LLM.
>
> **Next steps:** improve KGc extraction so fewer good claims become no evidence; run generated Answer(0) with real Ollama models; increase iterations; compare against the plain baseline path in Tool mode.”

---

## 13. Likely professor questions and answers

1. **Why use preset flawed Answer(0)?** — Reliable demo of contradictions; simulates an external LLM we audit. Code: `_resolve_answer_0()` with `example.initial_answer`.

2. **Is preset cheating?** — No. It controls the *input* to the auditor. The comparator and feedback logic still run. Research needs generated/real LLM answers too.

3. **What is KGc?** — Context knowledge graph: `ContextTripleExtractor` → `KgcFact` list from trusted context only.

4. **What is Answer(n)?** — The answer being evaluated at iteration n. Iteration 0: Answer(n)=Answer(0). Stored in `evaluated_answer`, `answer_n` alias.

5. **What exactly gets backtracked?** — Claims extracted from Answer(0) (then Answer(n) in later iterations), not the KGc reference answer.

6. **Is this really backtracking or just correction?** — Scaffold for backtracking: eval → feedback → revised answer. One iteration today; runner supports more via `max_iterations`.

7. **What does “route” mean?** — Not a formal code term. Informally: the pipeline path Answer(0)→KGc→eval→feedback→Answer(1). No `route` field in the API.

8. **How are claims extracted?** — LLM prompt `kg_claim_extraction.txt` via `TripleExtractor.extract_kgc_claims()`; mock uses `MockProvider._kg_claim_extraction_response()`.

9. **How is KGc built?** — LLM prompt `context_triple_extraction.txt` via `ContextTripleExtractor.extract()`.

10. **How are claims compared to KGc?** — Deterministic `GraphComparator.compare_claims()` with normalization in `kgc_matching.py`.

11. **What is deterministic?** — Label assignment in `graph_comparator.py` (and alignment helpers). Counts and feedback structure from evaluation results.

12. **What still uses an LLM?** — Context extraction, claim extraction, KGc reference answer, Answer(0) generation (if not preset), Answer(1) revision.

13. **Why use Neo4j?** — Persist FACT/CLAIM edges for inspection/demo when `NEO4J_ENABLED=true`. Not used to compute labels.

14. **What do nodes and edges mean?** — Entity nodes are string names; FACT edges = context facts; CLAIM edges = evaluated answer claims with label metadata.

15. **Why store reason/evidence on edges?** — They describe a specific assertion (subject–relation–object), not the entity alone.

16. **What is SUPPORTED?** — Claim matches a KGc fact after normalization. See §7.

17. **What is CONTRADICTED?** — Same subject+relation (normalized), different object vs KGc.

18. **What is NO_EVIDENCE?** — No matching KGc fact found.

19. **What happens when KGc misses a fact?** — Valid claims may be NO_EVIDENCE; reference answer may look incomplete → `kgc_extraction_notice`.

20. **What is `aligned_claims`?** — Output of `align_claims_to_kgc_schema()`—claims rewritten to canonical KGc subject/relation before compare.

21. **Why did J-2 become CONTRADICTED instead of NO_EVIDENCE?** — `kgc_schema_aligner.py` maps first-stage engine claims to `Saturn V S-IC stage` + `powered_by`; comparator sees object mismatch with F-1.

22. **What is KGc reference answer?** — `KgAnswerGenerator` output; optional; in Advanced details only.

23. **What is `graph_grounded_answer`?** — Backward-compat alias for `kgc_reference_answer` in `BacktrackingResult.to_dict()`.

24. **What is `evaluated_answer`?** — Answer whose claims were evaluated (Answer(0) at iteration 0).

25. **How is Answer(1) generated?** — `BacktrackingReviser.revise()` with `backtracking_revision.txt`; mock returns profile `revised` text.

26. **What happens in a second iteration?** — Runner would re-extract claims from revised answer, re-evaluate, revise again. API/UI default `max_iterations=1` so this is not shown by default.

27. **How compare to normal self-correction?** — Baseline mode uses `PipelineRunner` (verify against raw context, not KGc). Tool mode “Plain LLM baseline.”

28. **Next experiments?** — Better KGc extraction, real Ollama runs, multi-iteration UI, generated Answer(0), compare baseline vs KGc paths.

29. **Biggest limitation now?** — KGc extraction coverage and LLM-dependent extraction/revision; single-iteration default UI.

30. **Where is the API?** — `POST http://localhost:8000/run-kgc-backtracking` (see `api/server.py`).

---

## Ambiguous / unclear areas in the codebase

- **`backtracking_revision.txt`** wording still says “graph-grounded answer” while the runner passes Answer(0)—behavior is correct, prompt text is stale.
- **`answer_n` in `to_dict()`** aliases `evaluated_answer`, not a separate “current loop answer” after revision—naming can confuse when `max_iterations > 1`.
- **Apollo KGc fact count:** mock profile has **4** context facts (not 6); UI shows “4 facts” for mock runs.
- **“Route”** is not a defined API or code concept—use “pipeline” or “flow” instead.
- **`trace.answer_n_source`** and **`kgc_reference_answer_source`** both describe the reference-answer path; the main evaluated path is Answer(0) via `evaluated_answer`.

---

See also: [`DEMO_QUICK_REFERENCE.md`](DEMO_QUICK_REFERENCE.md) for a 5-minute cram sheet.
