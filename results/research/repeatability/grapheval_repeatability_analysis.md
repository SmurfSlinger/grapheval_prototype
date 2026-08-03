# GraphEval Three-Run Repeatability Analysis

Run 1 is the pre-specified official experiment; Runs 2 and 3 are
exact-configuration repetitions executed sequentially on the frozen
inference implementation. The three runs are repeated measurements of the
same 50 questions — they are never pooled as 150 independent questions,
and three runs do not support strong statistical inference.

## Runs

| Run | File | Generated |
|---|---|---|
| run1 | `apollo_multihop_llama31_8b_20260727T203028Z.json` | 2026-07-27T21:12:37.433000+00:00 |
| run2 | `apollo_repeat_run2_llama31_8b_20260803T012414Z.json` | 2026-08-03T02:06:32.431156+00:00 |
| run3 | `apollo_repeat_run3_llama31_8b_20260803T020637Z.json` | 2026-08-03T02:48:22.898298+00:00 |

## Per-run aggregates (n=50 each)

| Metric | Run 1 | Run 2 | Run 3 | Mean | Range |
|---|---|---|---|---|---|
| Completed | 50 | 50 | 50 | 50 | 0 |
| Errors | 0 | 0 | 0 | 0 | 0 |
| Timeouts | 0 | 0 | 0 | 0 | 0 |
| Exact match | 27 | 27 | 27 | 27 | 0 |
| Contains expected | 43 | 43 | 43 | 43 | 0 |
| Normalized match | 43 | 43 | 43 | 43 | 0 |
| Pipeline resolved | 33 | 33 | 33 | 33 | 0 |
| Path complete | 36 | 36 | 36 | 36 | 0 |
| Iterations total | 83 | 83 | 83 | 83 | 0 |
| Revisions total | 33 | 33 | 33 | 33 | 0 |
| Runtime mean (s) | 48.418 | 46.729 | 45.785 | 46.98 | 2.63 |
| Runtime median (s) | 44.911 | 43.816 | 42.539 | 43.76 | 2.37 |

### Stop reasons by run

| Stop reason | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| RESOLVED | 33 | 33 | 33 |
| STALLED | 7 | 7 | 7 |
| UNRESOLVED_NO_EVIDENCE | 3 | 3 | 3 |
| UNRESOLVED_TARGET_NOT_SATISFIED | 7 | 7 | 7 |

### Final claim labels by run

| Label | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| SUPPORTED | 65 | 65 | 65 |
| CONTRADICTED | 1 | 1 | 1 |
| NO_EVIDENCE | 12 | 12 | 12 |

## Per-question stability across all three runs (n=50 questions)

| Dimension | Stable in all 3 runs |
|---|---|
| Identical normalized final answer | 50/50 |
| Same exact-match status | 50/50 |
| Same contains-expected status | 50/50 |
| Same resolved/unresolved status | 50/50 |
| Same stop reason | 50/50 |
| Same evidence-path completeness | 50/50 |
| Same terminal claim | 50/50 |
| Same final label-count tuple | 50/50 |

## Primary stability categories

| Category | Count |
|---|---|
| stable_correct_resolved | 28 |
| stable_correct_unresolved | 15 |
| stable_incorrect_resolved | 5 |
| stable_incorrect_unresolved | 2 |

Change flags (a question may carry several):

| Flag | Count |
|---|---|

## Pairwise agreement (fraction of 50 questions agreeing)

| Dimension | R1 vs R2 | R1 vs R3 | R2 vs R3 |
|---|---|---|---|
| exact_match | 1.0 | 1.0 | 1.0 |
| contains_expected | 1.0 | 1.0 | 1.0 |
| resolved | 1.0 | 1.0 | 1.0 |
| path_complete | 1.0 | 1.0 | 1.0 |
| stop_reason | 1.0 | 1.0 | 1.0 |
| normalized_answer | 1.0 | 1.0 | 1.0 |
| terminal_claim | 1.0 | 1.0 | 1.0 |

Cohen's kappa (booleans; reference only — raw agreement is primary because
n = 50 and imbalanced categories can distort kappa):

| Dimension | R1 vs R2 | R1 vs R3 | R2 vs R3 |
|---|---|---|---|
| exact_match | 1.0 | 1.0 | 1.0 |
| contains_expected | 1.0 | 1.0 | 1.0 |
| resolved | 1.0 | 1.0 | 1.0 |
| path_complete | 1.0 | 1.0 | 1.0 |

## Depth-level variability

Each run contains only five questions per designed depth.

| Depth | Exact (R1/R2/R3) | Contains (R1/R2/R3) | Resolved (R1/R2/R3) | Path (R1/R2/R3) | Resolved range |
|---|---|---|---|---|---|
| 1 | 4/4/4 | 5/5/5 | 4/4/4 | 4/4/4 | 0 |
| 2 | 3/3/3 | 5/5/5 | 3/3/3 | 4/4/4 | 0 |
| 3 | 3/3/3 | 3/3/3 | 4/4/4 | 4/4/4 | 0 |
| 4 | 2/2/2 | 4/4/4 | 2/2/2 | 4/4/4 | 0 |
| 5 | 4/4/4 | 4/4/4 | 5/5/5 | 5/5/5 | 0 |
| 6 | 4/4/4 | 5/5/5 | 4/4/4 | 4/4/4 | 0 |
| 7 | 1/1/1 | 4/4/4 | 2/2/2 | 2/2/2 | 0 |
| 8 | 1/1/1 | 4/4/4 | 3/3/3 | 3/3/3 | 0 |
| 9 | 3/3/3 | 4/4/4 | 4/4/4 | 4/4/4 | 0 |
| 10 | 2/2/2 | 5/5/5 | 2/2/2 | 2/2/2 | 0 |

## Revision variability

- Never revised in any run: 27
- Revised in all three runs: 23
- Revision behavior changed between runs: 0
- Consistently resolved without revision in all runs: 27
- Resolved after revision in at least one run: 6
- Revised runs with inconsistent resolution outcomes: 0

Result rows do not preserve intermediate answers or claim-label transitions, so whether a specific revision corrected or regressed an answer cannot be inferred from these files alone.

