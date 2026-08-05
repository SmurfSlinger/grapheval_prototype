# Algorithm Worked Examples (Preserved Artifacts Only)

Companion to `research/METHODOLOGY_DOCUMENTATION_AUDIT.md` and `research/NEO4J_DATA_MODEL.md`.  
Every triple and label below is taken from a preserved debug JSONL or from an official result row.  
Where intermediate state was not saved, that is stated explicitly.

**Frozen inference:** `b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`  
**Official Apollo aggregate:** `results/research/apollo_multihop_llama31_8b_20260727T203028Z.json`

---

## A. Clean SUPPORTED example (Apollo post-fix trace)

| Field | Value |
|---|---|
| Question ID | `apollo_hop_046` |
| Execution ID | `apollo_hop_046__20260727T202312Z__50843932` |
| Artifact | `.runtime/debug/20260727T202312Z_apollo_hop_046_attempt_91bb9b85.jsonl` |
| Question | Which field studies the global body containing the ocean reached through Neil Armstrong's birthplace and the Potomac watershed? |
| Role | Qualitative / instrumentation example of a clean SUPPORTED claim under frozen code; not a claim that official aggregate rows retained JSONL |

**Trusted FACT (from context extraction in this trace):**

- `Global Ocean — is_studied_by → Oceanography`

**CLAIM (final comparison event):**

- `Global Ocean — is_studied_by → Oceanography`
- **Label:** `SUPPORTED`
- **Reason (exact):** `Claim matches KGc fact in question-scoped evaluation frame.`
- **Comparison function:** `GraphComparator.compare_claims` → target-frame path (`_evaluate_claim_target_frame`) when a question target with expected relations is active

**Outcome:** sub-question finished `RESOLVED`; final answer `Oceanography`; 1 iteration; 0 revisions; labels 1 SUPPORTED / 0 / 0.

**Feedback / revised answer:** not applicable (resolved on first pass).

**Note:** Supported CLAIMs remain CLAIMs; they are not written as FACT relationships.

---

## B. CONTRADICTED claim (Apollo complex preset; clear object conflict)

| Field | Value |
|---|---|
| Question / example ID | `apollo_complex` |
| Execution ID | `apollo_complex__20260727T010636Z__22c8fcc4` |
| Artifact | `.runtime/debug/20260727T010636Z_apollo_complex_attempt_c8a1631c.jsonl` |
| Domain note | Apollo-themed qualitative example; **not** one of the official 50 hop rows |

**Question (from `run_started`):** compound Apollo 11 questions (when / crew / launch / president / lunar material).

**Trusted FACT (context extraction):**

- `Apollo 11 — mission_dates → July 16-24, 1969`
- (also present: crew, launch vehicle, lunar material FACTs)

**Model CLAIM (sub-question 1, `claim_comparison`):**

- `Apollo 11 — occurred_during → July 16-August 5, 1985`
- **Label:** `CONTRADICTED`
- **Reason (exact):** `Claim object 'July 16-August 5, 1985' conflicts with KGc fact 'July 16-24, 1969' for relation family 'occurrence_date'.`

**Why CONTRADICTED:** target-frame comparison treats `occurred_during` and `mission_dates` as the same relation family (`occurrence_date`); subjects match; objects conflict under the intent rules (`objects_conflict_for_intent`).

**Trusted FACT retained:** the FACT edge is unchanged; only the CLAIM is labeled.

**Feedback:** built by `BacktrackingFeedbackBuilder` from CONTRADICTED evaluations (preserve SUPPORTED; instruct correction using conflicting FACT). Exact feedback string is in the same JSONL at the following `feedback_built` event for sub-question 1.

**Additional CONTRADICTED claims in the same execution (same artifact):** crew names including invented members; launch site `John F. Kennedy Airport` vs FACT launch site; `7 ounces` vs `21.5 kg` lunar material — each with explicit conflict reasons in `claim_comparison` events.

---

## C. NO_EVIDENCE claim (WannaCry regression trace; separate from Apollo n=50)

| Field | Value |
|---|---|
| Question ID | `nhs_wannacry_h10_q01` |
| Execution ID | `nhs_wannacry_h10_q01__20260727T214622Z__4adc0f88` |
| Artifact | `.runtime/debug/20260727T214622Z_nhs_wannacry_h10_q01_attempt_70a052a7.jsonl` |
| SHA256 | `a71d678c6abd1f6afcdfa1c064823c00a166c34541c8932925cb25efc9c1632a` (see `research/REPRODUCIBILITY_RECORD.md`) |

**Question:** In the May 2017 NHS WannaCry attack, along the technical malware-propagation chain, which Microsoft security bulletin supplied the final fix?

**Trusted FACT (excerpt):**

- `Microsoft Security Bulletin MS17-010 — supplied_correction_to_vulnerability → how SMBv1 handled crafted requests`

**Earlier in Q1:** the bulletin claim was **SUPPORTED** (iteration with MS17-010 present).

**Final Q1 CLAIM:**

- `WannaCry ransomware campaign — affected_by_final_fix → patching`
- **Label:** `NO_EVIDENCE`
- **Reason (exact):** `KGc has no matching fact for this claim.`
- **Path:** legacy or target-frame fall-through to no matching FACT (`GraphComparator`)

**Stop:** `UNRESOLVED_NO_EVIDENCE` after 3 iterations; final answer `The NHS's final fix in May 2017 was patching.`

**Must remain separate** from Apollo quantitative rates.

---

## D. Multi-iteration correction — official `apollo_hop_036` (partial preservation)

| Field | Value |
|---|---|
| Question ID | `apollo_hop_036` |
| Execution ID | `apollo_hop_036__20260727T205852Z__c2d8a77c` |
| Artifact | Official row in `results/research/apollo_multihop_llama31_8b_20260727T203028Z.json` |
| `debug_log_path` | **`null`** |

**Question:** Which ocean receives the bay fed by the river beside the capital reached through Neil Armstrong's birthplace?

**Final answer (preserved):** `Atlantic Ocean`  
**Scoring (post-inference):** exact match true; contains expected true; `resolved_by_pipeline` true; stop `RESOLVED`  
**Iterations / revisions (aggregate counters only):** 3 iterations, 2 revisions  
**Final label counts:** 3 SUPPORTED / 0 CONTRADICTED / 0 NO_EVIDENCE  

**Terminal claim (preserved):**

- `Chesapeake Bay — opens_into → Atlantic Ocean`

**Trusted evidence path (preserved on the result row):** 7 FACT edges from `Neil Armstrong` through Wapakoneta → Ohio → United States → Washington, D.C. → Potomac River → Chesapeake Bay → Atlantic Ocean; `complete: true`.

### What was **not** preserved

- Initial answer text before revisions  
- Intermediate CLAIM sets and labels that triggered the two revisions  
- Feedback strings for those revisions  
- Per-iteration Neo4j snapshots  

An older local debug file `20260727T003913Z_apollo_hop_036_attempt_1.jsonl` is a **different** execution (`…35199160`) that resolved each sub-question in **1** iteration and therefore cannot supply the official run’s intermediate revision history.

**Documentation rule:** state that official `apollo_hop_036` demonstrates successful multi-iteration resolution in aggregate metrics and final path, but **do not invent** the missing intermediate answers or labels.

---

## E. WannaCry full trace (regression; separate qualitative sample)

Same artifact as Example C. Use for diagrams that need a fully preserved sequence of FACT write → CLAIM labels → feedback → revision → final stop.

**CONTRADICTED example inside this trace (Q2 final comparison):**

- CLAIM: `Microsoft Security Bulletin MS17-010 — supplied_correction_to_vulnerability → allowing remote code execution when specially crafted SMBv1 messages were sent`
- FACT object retained: `how SMBv1 handled crafted requests`
- **Label:** `CONTRADICTED`
- **Reason (exact):** `Claim object 'allowing remote code execution when specially crafted SMBv1 messages were sent' conflicts with KGc fact 'how SMBv1 handled crafted requests' for relation 'supplied_correction_to_vulnerability'.`

This is suitable for the contradiction diagram when an Apollo-complex screenshot is unavailable; caption must say **WannaCry qualitative execution**, not Apollo official sample.

---

## Code functions referenced

| Step | Module | Symbol |
|---|---|---|
| Compare / label | `src/pipeline/graph_comparator.py` | `GraphComparator.compare_claims` |
| Feedback | `src/pipeline/backtracking_feedback_builder.py` | `BacktrackingFeedbackBuilder` |
| Stop | `src/pipeline/kgc_iteration.py` | `determine_stop_reason` |
| Path | `src/pipeline/evidence_path_resolver.py` | `resolve_evidence_path` |
| Persist CLAIM | `src/storage/neo4j_store.py` | `_create_kgc_claim` (CREATE append) |
| Persist FACT | `src/storage/neo4j_store.py` | `_create_fact` (MERGE) |
| Orchestration | `src/pipeline/decomposed_backtracking_runner.py` | `DecomposedBacktrackingRunner.run_example` |
