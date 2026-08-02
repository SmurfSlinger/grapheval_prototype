# Representative Trace Cases

All cases below are observed executions taken from existing artifacts (the official
Apollo 50-question result JSON, preserved `.runtime/debug/*.jsonl` traces, and
depth-acceptance diagnostics). No new model outputs were generated for this document.
Trace excerpts are compact; full evidence lives at the cited paths.

Classification vocabulary: primarily model behavior / primarily pipeline behavior /
mixed / unclear. The classification asks where the first unsupported transformation
occurred, not who "deserves blame."

Evidence-source note: official-run rows (Cases 1–8) come from
`results/research/apollo_multihop_llama31_8b_20260727T203028Z.json`; that run did not
persist per-question debug traces (`debug_log_path: null`), so per-iteration claim-label
history is unavailable for those cases and is never inferred. Cases 9–10 have full
local JSONL traces.

Category coverage map (categories from the research protocol):

| # | Category | Case(s) |
|---|---|---|
| 1 | Correct first-pass answer, immediate resolution | 1, 2 |
| 2 | Successful revision after adverse labels | 3 (partial: labels not preserved) |
| 3 | Appropriate rejection after NO_EVIDENCE | 4, 6 |
| 4 | Supported information preserved during revision | 9 (Q2 SUPPORTED claims persisted) |
| 5 | Wrong answer correctly rejected by pipeline | 6 |
| 6 | Correct textual answer left unresolved | 4, 5, 8 |
| 7 | Answer regression during revision | 9 |
| 8 | STALLED behavior | 4, 9 |
| 9 | High-depth resolved case | 2, 3 |
| 10 | High-depth unresolved case | 8, 9 |
| 11 | Decomposition helping | no clear observed instance in examined artifacts (recorded honestly) |
| 12 | Decomposition harming | 9 |
| — | Instrument-development pre-fix/post-fix pair | 10 |

---

## Case 1 — Clean first-pass success at depth 1 (`apollo_hop_001`)

- Benchmark: `apollo_multihop_50`; question ID `apollo_hop_001`; designed depth 1
- Execution: `apollo_hop_001__20260727T203028Z__656bf325`
- Source: official result JSON row (no debug trace persisted)
- Question: "Who crewed Apollo 11?" — expected: "Neil Armstrong"
- Initial = final answer: "Neil Armstrong" (0 revisions, 1 iteration)
- Terminal claim: `Apollo 11 — was_crewed_by → Neil Armstrong` (SUPPORTED, 1/0/0)
- Evidence path: complete, length 2 (`Apollo Missions — includes → Apollo 11`, then the terminal claim)
- Target: intent `crew_members`, canonical relation `was_crewed_by`; stop reason RESOLVED
- Interpretation: baseline behavior — a correct compact answer whose single claim matches a trusted FACT and connects to the graph root.
- Classification: n/a (success); demonstrates the intended happy path of both model and pipeline.

## Case 2 — High-depth resolved on first pass (`apollo_hop_046`, official run)

- Execution: `apollo_hop_046__20260727T210803Z__c3c7849e`; designed depth 10
- Question: "Which field studies the global body containing the ocean reached through Neil Armstrong's birthplace and the Potomac watershed?" — expected: "Oceanography"
- Final answer: "Oceanography"; exact match; RESOLVED; 1 iteration, 0 revisions
- Terminal claim `Global Ocean — is_studied_by → Oceanography` (SUPPORTED); complete trusted path of length 9 from `Neil Armstrong` through Wapakoneta → Ohio → United States → Washington, D.C. → Potomac River → Chesapeake Bay → Atlantic Ocean → Global Ocean → Oceanography
- Interpretation: designed ten-hop questions are resolvable end-to-end by the post-fix pipeline in one pass; depth alone did not prevent resolution.
- Classification: n/a (success). This same question failed pre-fix (Case 10), which is why it matters.

## Case 3 — Revision leading to resolution at depth 8 (`apollo_hop_036`)

- Execution: `apollo_hop_036__20260727T205852Z__c2d8a77c`; designed depth 8
- Question: "Which ocean receives the bay fed by the river beside the capital reached through Neil Armstrong's birthplace?" — expected: "Atlantic Ocean"
- Final answer: "Atlantic Ocean"; exact match; RESOLVED after 3 iterations / 2 revisions; final labels 3 SUPPORTED / 0 / 0; complete 7-edge trusted path ending `Chesapeake Bay — opens_into → Atlantic Ocean`; runtime 70.1 s (second-longest in the run)
- Interpretation: the first pass did not resolve; two feedback-driven revisions produced an answer whose claims all became SUPPORTED and graph-connected. This is the clearest official-run example of iterative graph feedback ending in resolution.
- Limitation: the intermediate labels that triggered the revisions were not persisted, so whether the trigger was CONTRADICTED or NO_EVIDENCE cannot be stated (category 2 evidence is therefore partial).
- Classification: successful mixed behavior (model revision + pipeline feedback loop).

## Case 4 — Correct answer stalled by degenerate claim extraction (`apollo_hop_005`)

- Execution: `apollo_hop_005__20260727T203315Z__738dc7cf`; designed depth 1
- Question: "Which program included Apollo 11?" — expected: "Apollo Program"
- Final answer: "The Apollo Program." — contains expected, exact-match fails only on the article/period; STALLED after 2 iterations / 1 revision; final labels 0/0/1
- Terminal claim extracted from the answer: `Apollo Program — includes → The Apollo Program.` — a degenerate self-referential triple whose object is the answer sentence, not an entity; evidence-path failure `terminal_claim_not_a_trusted_fact`
- Interpretation: the model's text was right; the claim extractor emitted a semantically invalid triple, comparison correctly found NO_EVIDENCE for it, and the run stalled. The textual answer was fine; the structured representation of it was not.
- Classification: mixed — LLM claim-extraction instability produced the invalid triple (model), and the deterministic layer then treated it literally with no recovery (pipeline). The stop was honest: nothing untrusted was promoted.

## Case 5 — Correct, path-complete, yet unresolved (`apollo_hop_007`)

- Execution: `apollo_hop_007__20260727T203443Z__2506492e`; designed depth 2
- Question: "What was the first stage of the rocket that launched Apollo 11?" — expected: "S-IC"
- Final answer: "The S-IC was the first stage of the Saturn V rocket that launched Apollo 11." — contains expected; UNRESOLVED_NO_EVIDENCE after 3 iterations / 2 revisions; final labels 1 SUPPORTED / 0 / 1 NO_EVIDENCE
- Terminal claim `Apollo 11 — was_launched_by → Saturn V` is SUPPORTED with a complete length-1 path, but a residual NO_EVIDENCE claim kept the aggregate unresolved; note the terminal claim answers "which rocket," not "which first stage"
- Interpretation: conservative stop logic — one unresolvable residual claim blocks resolution even when the visible answer text is correct and a supported path exists. Also shows the terminal claim landing on the wrong semantic target.
- Classification: primarily pipeline behavior (claim selection/stop-condition strictness), with model claim phrasing as a contributing factor.

## Case 6 — Wrong answer correctly rejected (`apollo_hop_014`)

- Execution: `apollo_hop_014__20260727T204021Z__ae6eabf6`; designed depth 3
- Question: "Which landing region is associated with the body holding Eagle's descent stage?" — expected: "Sea of Tranquility"
- Final answer: "...is part of the Apollo Program." — does not contain the expected answer; UNRESOLVED_TARGET_NOT_SATISFIED after 3 iterations / 2 revisions; final labels 1/0/0; evidence-path failure `missing_intermediate_edge`
- The only supported claim (`Apollo 11 — was_part_of → Apollo Program`) is true but irrelevant to the location-containment target the deterministic layer derived (intent `location_containment`, canonical relation `is_located_in`)
- Interpretation: the model drifted to a generic true statement; revisions did not recover the landing-region entity; the pipeline correctly refused to resolve. This is the desired behavior on a wrong answer: textual scoring and pipeline verdict agree the answer failed, and target validation identified why.
- Classification: primarily model behavior (wrong/evasive answer, revision non-recovery); pipeline behaved as designed.

## Case 7 — Pipeline resolved but textually wrong (`apollo_hop_037`)

- Execution: `apollo_hop_037__20260727T210004Z__a2533d6c`; designed depth 8
- Question: "Which body of water borders the region containing the state containing the city where Apollo 11's first stage was assembled?" — expected: "Gulf of Mexico"
- Final answer: "state" (a single generic word); exact/contains both false; RESOLVED after 2 iterations / 1 revision; labels 3/0/0
- Terminal claim `Louisiana — is_located_in → state` sits at the end of a complete 7-edge trusted path (Apollo 11 → Saturn V → S-IC → Boeing → Michoud → New Orleans → Louisiana → "state"), but the terminal object is a generic category noun, not the asked-for body of water
- Interpretation: resolution here is technically honest (every edge is trusted) but semantically wrong: the derived compound target accepted a path that stops one concept short of the designed answer, and the final combination surfaced the degenerate terminal object as the whole answer. A conventional final-answer-only evaluation would just say "wrong"; the trace shows the wrongness was manufactured by target interpretation plus answer combination, not by a hallucinated claim.
- Classification: primarily pipeline behavior (target validation accepted the wrong semantic target; combiner projected the terminal object), with the model's mid-path claim focus as a contributing factor.

## Case 8 — High-depth, correct text, unresolved target (`apollo_hop_050`)

- Execution: `apollo_hop_050__20260727T211145Z__8a7c71f9`; designed depth 10
- Question: "In which city is the organization archiving the report about the procedure that resolved Gemini 8's emergency headquartered?" — expected: "Washington, D.C."
- Final answer: multi-sentence prose ending "...headquartered is: Washington, D.C." — contains expected; UNRESOLVED_TARGET_NOT_SATISFIED after 2 iterations / 1 revision; labels 1/0/0; evidence-path failure `missing_intermediate_edge` from start entity `Gemini 8`
- Terminal claim `National Air and Space Museum — is_located_in → Washington, D.C.` is supported but the resolver could not connect `Gemini 8` to it through the trusted graph
- Interpretation: at high depth, the model's prose can be right while the ten-edge trusted chain cannot be assembled from the claims the extractor produced; the answer is textually correct but graph-unverifiable in this run.
- Classification: mixed — the model answered with (correct) prose whose claims skip intermediate edges; the resolver requires every intermediate edge and had no mechanism to elicit the missing ones.

## Case 9 — REQUIRED WannaCry ten-hop regression case (`nhs_wannacry_h10_q01`)

- Benchmark: `nhs_wannacry_multihop_50`; question ID `nhs_wannacry_h10_q01`; designed depth 10
- Execution: `nhs_wannacry_h10_q01__20260727T214622Z__4adc0f88`
- Source trace (verified locally, SHA256 `a71d678c...`): `.runtime/debug/20260727T214622Z_nhs_wannacry_h10_q01_attempt_70a052a7.jsonl`
- The `Pasted text(44).txt` UI export referenced by the research protocol is absent from this environment; the fields reported only there (per-subquestion `question_target: true`, evidence-path `missing_intermediate_edge`, runtime ≈ 1 min 31 s) are cited as UI-export observations. `missing_intermediate_edge` is standard pipeline vocabulary (it appears in official-run rows, e.g. Cases 6 and 8), so the report is plausible but not locally re-verifiable for this execution.
- Question: "In the May 2017 NHS WannaCry attack, along the technical malware-propagation chain, which Microsoft security bulletin supplied the final fix?"
- Expected: "Microsoft Security Bulletin MS17-010"

Observed sequence (all from the local trace):

1. Decomposition split the single nested question into:
   - Q1: "What was the final fix provided by in the May 2017 NHS WannaCry attack?" (malformed English; retargets the task from a bulletin identifier to a vague "fix")
   - Q2: "Which Microsoft security bulletin supplied this fix along the technical malware-propagation chain?"
2. Context FACT extraction accepted 7 base facts and rejected 21 triples as `empty_object` anomalies (`structured_triple_anomaly` events) — the trusted graph for this question was thin, dropping most NHS-report content including several propagation-chain edges.
3. Q1 iteration 1: the projected answer named the bulletin. Claim extraction sourced from sentences including "Microsoft Security Bulletin MS17-010 supplied correction to the vulnerability"; after safe alignment, the claim `Microsoft Security Bulletin MS17-010 — supplied_correction_to_vulnerability → how SMBv1 handled crafted requests` was SUPPORTED.
4. Q1 final iteration (after revision): final answer "The NHS's final fix in May 2017 was patching." Its only claim, `WannaCry ransomware campaign — affected_by_final_fix → patching` (a relation the extractor admitted it invented), received NO_EVIDENCE. Sub-question ended UNRESOLVED_NO_EVIDENCE after 3 iterations — the MS17-010 identifier was gone.
5. Q2 iteration 1: three claims all SUPPORTED, including two explicit MS17-010 claims. These SUPPORTED MS17-010 claims persisted into iteration 2 (category 4: supported information preserved).
6. Q2 final iteration: claim extraction over-expanded the prose into six near-duplicate `MS17-010 — supplied_correction_to_vulnerability → ...` variants; two remained SUPPORTED, four were CONTRADICTED as over-expanded objects. Sub-question ended STALLED after 2 iterations with final answer "This bulletin was published on 14 March 2017 and corrected how SMBv1 handled crafted requests, ..." — explanatory prose whose referent ("This bulletin") lost the identifier.
7. Final combined answer: `[UNRESOLVED_NO_EVIDENCE] The NHS's final fix in May 2017 was patching.` + `[STALLED] This bulletin was published on 14 March 2017...` — contains-expected FALSE, exact-match FALSE, pipeline unresolved. Totals: 5 sub-question iterations, 3 revisions, final labels 2 SUPPORTED / 4 CONTRADICTED / 1 NO_EVIDENCE, 21 anomalies.

- Classification: **mixed pipeline-mediated model regression.** The model initially generated the expected bulletin, but unnecessary decomposition, projection loss, incomplete graph connectivity (21 dropped context triples), claim-extraction instability, and unsuccessful revision caused the final combined answer to lose the correct entity.
- Why research-useful: the correct information was demonstrably present at iteration 1; the graph evaluation separately identified supported, contradicted, and unsupported components; the trace localizes exactly where the identifier was lost (Q1 revision and Q2 final projection); and a conventional final-answer-only evaluation would have recorded only "wrong answer," hiding all of this. This case must not be read as evidence that an 8B model cannot answer a ten-hop question — the same model produced the correct entity inside this very execution.

## Case 10 — Apollo depth-10 pre-fix/post-fix instrument pair (`apollo_hop_046` diagnostics)

Same question and expected answer as Case 2. These are development diagnostics, kept
out of the official quantitative sample.

Pre-fix execution `apollo_hop_046__20260727T190016Z__0e37a955`
(trace `.runtime/debug/20260727T190016Z_apollo_hop_046_attempt_7dbf3e1b.jsonl`):

- The model's prose contained the correct answer: "Oceanography studies the Global Ocean, which contains the Atlantic Ocean. ..."
- The claim extractor emitted the reversed triple `Oceanography — is_studied_by → Global Ocean`.
- Schema alignment then performed two unsafe transformations (`canonicalize_subject_to_unique_kgc_match`, `canonicalize_relation_to_unique_kgc_match`), turning it into the intermediate relationship `Atlantic Ocean — is_part_of → Global Ocean` — destroying the terminal claim.
- The evidence path consequently ended at Global Ocean, the unresolved combiner projected the wrong terminal object, and the combined answer became `[STALLED] Global Ocean` (final labels 3 SUPPORTED / 0 / 2 NO_EVIDENCE, 2 iterations).

Post-fix execution `apollo_hop_046__20260727T202312Z__50843932`
(trace `.runtime/debug/20260727T202312Z_apollo_hop_046_attempt_91bb9b85.jsonl`,
run at the frozen reliability commit `b9608d0`):

- Claim extracted in correct orientation: `Global Ocean — is_studied_by → Oceanography`; alignment left it untouched; label SUPPORTED ("matches KGc fact in question-scoped evaluation frame").
- RESOLVED in 1 iteration; combined answer "Oceanography"; complete ten-hop trusted path; no cross-execution relationship contamination (fresh 46-fact working graph).

- Classification of the pre-fix failure: primarily pipeline behavior (unsafe claim alignment plus unresolved-combiner projection), triggered by a model-side reversed extraction.
- Role in the study: this pair is the concrete justification for freezing the official experiment at `b9608d0` ("Prevent claim alignment drift and preserve unresolved answers") and is presented as instrument development, never merged into the official run's statistics.

---

## Cross-case observations

- The pipeline never promoted untrusted content: every unresolved stop in these cases was honest, and 0 of the official run's 50 rows show a CLAIM becoming a FACT.
- The dominant divergence is "textually correct but pipeline unresolved" (15/50 official rows); Cases 4, 5, and 8 show its three main mechanisms (degenerate claim extraction, residual NO_EVIDENCE claims, missing intermediate edges).
- Regression during revision was observed (Case 9 Q1) and successful revision was observed (Case 3); with 3 revisions in one and 2 in the other, neither direction is rare, matching the official-run finding that only 6 of 23 revised questions eventually resolved.
- No examined artifact shows decomposition clearly helping; the strongest high-depth successes (Cases 2, 3) treated the nested question as a single unit.
