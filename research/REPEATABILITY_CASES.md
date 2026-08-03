# Repeatability Study — Representative Cases

Three complete executions of the Apollo 50-question benchmark under the frozen
configuration (Run 1 official 2026-07-27; Runs 2–3 on 2026-08-03 UTC). Source
analysis: `results/research/repeatability/grapheval_repeatability_analysis.json`.

## Headline observation (constrains case selection)

Across these three executions, all 50 questions produced **byte-identical raw
final answers, combined answers, normalized answers, exact/contains statuses,
resolution statuses, stop reasons, evidence-path statuses, terminal claims, final
label tuples, iteration counts, and revision counts**. Execution IDs and Neo4j
execution scopes were distinct in every run, so these are genuinely independent
executions, not replayed artifacts. The only observed variation was wall-clock
runtime (per-run means 48.42 / 46.73 / 45.79 s).

Consequently, the requested instability categories — different wording with same
result, same text with different pipeline status, resolution flips, exact-vs-
contains flips, terminal-claim changes, stop-reason changes, and revision-behavior
changes — have **zero observed instances in this sample**. No such cases are
manufactured below. The result was stable in this small sample of three runs on
one machine; the artifacts do not establish that every future run must be
identical (different hardware, driver, Ollama version, model build, or concurrent
load could behave differently, and the depth-acceptance diagnostics of 2026-07-27
show the same questions answered differently under different execution
conditions).

The cases below therefore illustrate the *reproduced* outcome spectrum: each case
reproduced its entire behavior — including its failure mode or its multi-step
revision — in all three runs.

Per-case statuses (exact / contains / resolved / path, stop reason, iterations,
revisions, terminal claim, final answer) were identical in all three runs and are
stated once.

## Case R1 — Stable correct resolved, depth 1 (`apollo_hop_001`)

- Q: "Who crewed Apollo 11?" — expected "Neil Armstrong"; final answer "Neil Armstrong"
- exact ✓ / contains ✓ / resolved ✓ / path ✓; RESOLVED; 1 iteration, 0 revisions;
  terminal claim `Apollo 11 — was_crewed_by → Neil Armstrong`
- Executions: `...20260727T203028Z__656bf325`, `...20260803T012414Z__9287d5ee`,
  `...20260803T020637Z__b388d915`
- Runtimes 44.2 / 55.5 / 37.4 s — the largest runtime spread in the study (18.1 s,
  first question of each run; model warm-up is the plausible but unproven factor).
- Interpretation: identical output despite the study's largest timing variation —
  runtime and output stability are independent dimensions here.

## Case R2 — Stable correct resolved at depth 10 (`apollo_hop_046`)

- Q: ten-hop Oceanography chain — expected/final "Oceanography"
- exact ✓ / resolved ✓ / complete 9-edge path; RESOLVED; 1 iteration, 0 revisions;
  terminal claim `Global Ocean — is_studied_by → Oceanography`
- Executions: `...20260727T210803Z__c3c7849e`, `...20260803T020159Z__74fc8fa2`,
  `...20260803T024351Z__0da5a977`; runtimes 48.7 / 46.5 / 46.0 s
- Interpretation: the strongest high-depth success was stable in this small
  sample — the ten-hop resolution of Run 1 was not a lucky draw of that
  particular execution.

## Case R3 — Multi-revision resolution reproduced exactly (`apollo_hop_036`, depth 8)

- Expected/final "Atlantic Ocean"; RESOLVED after 3 iterations / 2 revisions in
  every run; 3 SUPPORTED final claims; complete 7-edge path
- Executions: `...20260727T205852Z__c2d8a77c`, `...20260803T015249Z__e3c39c61`,
  `...20260803T023440Z__d3fff44b`; runtimes 70.1 / 67.2 / 66.7 s
- Interpretation: even the report's flagship *iterative correction* trajectory —
  two feedback-driven revisions ending in exact resolution — reproduced its
  iteration count, revision count, final labels, and final answer in every run.
  Intermediate revision texts are not preserved in result rows, so byte-identity
  of the intermediate steps is suggested by the identical endpoints but not
  directly proven.

## Case R4 — Degenerate-extraction stall reproduced (`apollo_hop_005`, depth 1)

- Final answer "The Apollo Program." (contains expected); STALLED; 2 iterations /
  1 revision; final labels 0/0/1; degenerate terminal claim
  `Apollo Program — includes → "The Apollo Program."`; path failure reproduced
- Executions: `...20260727T203315Z__738dc7cf`, `...20260803T012715Z__b0bf2e95`,
  `...20260803T020918Z__0aa9ffa1`; runtimes 45.2 / 45.4 / 43.2 s
- Interpretation: the Experiment Report's Case 4 failure mode (claim-extraction
  instability treated literally by the deterministic layer) is not an occasional
  glitch of one execution — under identical conditions the extractor emitted the
  same degenerate triple every time. "Instability" here means semantic
  malformation, not run-to-run randomness.

## Case R5 — Resolved-but-wrong reproduced (`apollo_hop_037`, depth 8)

- Final answer "state" (wrong); RESOLVED in all runs; 2 iterations / 1 revision;
  terminal claim `Louisiana — is_located_in → state` at the end of a complete
  7-edge trusted path
- Executions: `...20260727T210004Z__a2533d6c`, `...20260803T015402Z__0db9d57b`,
  `...20260803T023554Z__b03ddc22`; runtimes 54.4 / 52.0 / 51.8 s
- Interpretation: the target/combination semantics limitation is systematic, not
  sporadic — three independent executions resolved to the same generic terminal
  object.

## Case R6 — Honest rejection of a wrong answer reproduced (`apollo_hop_014`, depth 3)

- Wrong final answer (Apollo Program instead of Sea of Tranquility);
  UNRESOLVED_TARGET_NOT_SATISFIED after 3 iterations / 2 revisions in every run
- Executions: `...20260727T204021Z__ae6eabf6`, `...20260803T013426Z__601fe962`,
  `...20260803T021619Z__7cd14f8e`; runtimes 48.6 / 47.7 / 46.6 s (smallest spreads
  in the study)
- Interpretation: the pipeline's refusal to resolve this wrong answer — and the
  model's failure to recover across two revisions — reproduced exactly.

## Case R7 — High-depth correct-but-unresolved reproduced (`apollo_hop_050`, depth 10)

- Final prose contains "Washington, D.C." (correct entity);
  UNRESOLVED_TARGET_NOT_SATISFIED; 2 iterations / 1 revision; terminal claim
  `National Air and Space Museum — is_located_in → Washington, D.C.` with a
  missing-intermediate-edge path failure in each run
- Executions: `...20260727T211145Z__8a7c71f9`, `...20260803T020540Z__e2b09d07`,
  `...20260803T024731Z__9879d756`; runtimes 50.1 / 47.6 / 48.3 s
- Interpretation: the dominant divergence class of the official run (textually
  correct but graph-unresolved) is a stable property of these question/pipeline
  pairs under fixed conditions, not sampling noise.

## Case R8 — The only varying dimension: runtime

- Per-run mean runtimes 48.42 / 46.73 / 45.79 s (range 2.63 s); medians
  44.91 / 43.82 / 42.54 s. Largest per-question spread: `apollo_hop_001`
  (18.1 s, first question of each run); most spreads < 4 s.
- Interpretation: timing varied with system conditions while outputs did not; the
  artifacts do not isolate the cause of the timing differences (warm-up and host
  load are plausible but unproven).

## What this small sample suggests

- Under the frozen implementation, fixed dataset, temperature 0, the same model
  digest, the same Ollama build, and the same machine, the full pipeline —
  generation, decomposition, extraction, labeling, revision, and validation — was
  reproducible end-to-end in three of three runs.
- The failure modes documented in the Experiment Report are systematic under
  these conditions; single-run results for this configuration were not distorted
  by run-to-run sampling noise in this sample.
- These three runs cannot certify determinism in general. Variation previously
  observed between *differently configured* executions (e.g. the 2026-07-27
  depth-acceptance diagnostics and pre-fix runs, which used the same questions
  but different software or execution context) shows the system's outputs do
  change when conditions change; the present study holds conditions fixed and
  finds the remaining run-to-run variation to be zero in this sample except for
  runtime.
