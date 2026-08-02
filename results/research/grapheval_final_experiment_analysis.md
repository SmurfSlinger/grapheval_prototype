# GraphEval Final Experiment Analysis

- Source: `results/research/apollo_multihop_llama31_8b_20260727T203028Z.json`
- Test set: `apollo_multihop_50` — run generated 2026-07-27T21:12:37.433000+00:00
- Branch: `debug/8b-hop-validation` | provider/model: ollama / llama3.1:8b
- num_ctx 8192, timeout 180.0 s/question, Neo4j enabled: True, cleared between questions: True

All numbers below are recomputed from the raw per-question rows; the recomputed
aggregates match the runner's summary block exactly.

Sample-size note: each designed depth contains only five questions. Per-depth
values are descriptive counts, not statistically established trends.

## Completion and runtime

| Metric | Value |
|---|---|
| Questions | 50 |
| Completed | 50 |
| Errors | 0 |
| Timeouts | 0 |
| Total iterations | 83 |
| Total revisions | 33 |
| Runtime s (min/Q1/median/Q3/max) | 37.526 / 40.918 / 44.911 / 52.816 / 72.492 |
| Runtime s (mean) | 48.418 |

## Textual-answer results (overall, n=50, Wilson 95% CI)

| Metric | Count | Rate | 95% CI |
|---|---|---|---|
| Exact match | 27 | 0.54 | [0.40, 0.67] |
| Contains expected | 43 | 0.86 | [0.74, 0.93] |
| Normalized match | 43 | 0.86 | [0.74, 0.93] |
| Pipeline resolved | 33 | 0.66 | [0.52, 0.78] |
| Evidence path complete | 36 | 0.72 | [0.58, 0.83] |

## Stop-reason distribution

| Stop reason | Count |
|---|---|
| RESOLVED | 33 |
| STALLED | 7 |
| UNRESOLVED_TARGET_NOT_SATISFIED | 7 |
| UNRESOLVED_NO_EVIDENCE | 3 |

## Joint textual-correctness × pipeline-resolution outcomes

Textual correctness here uses contains-expected (exact-match variant in parentheses).

| Joint category | Contains-expected basis | Exact-match basis |
|---|---|---|
| textually correct and pipeline resolved | 28 | 27 |
| textually correct but pipeline unresolved | 15 | 0 |
| textually incorrect but pipeline resolved | 5 | 6 |
| textually incorrect and pipeline unresolved | 2 | 17 |

Runner `resolved_and_matched_count` (28) uses the runner's
permissive `answer_match` flag; strict exact-and-resolved is 27.

## Results by designed depth (five questions per depth)

| Depth | Exact | Contains | Resolved | Path complete | Avg iter | Avg rev | Mean runtime s |
|---|---|---|---|---|---|---|---|
| 1 | 4/5 | 5/5 | 4/5 | 4/5 | 1.2 | 0.2 | 40.72 |
| 2 | 3/5 | 5/5 | 3/5 | 4/5 | 1.6 | 0.6 | 46.913 |
| 3 | 3/5 | 3/5 | 4/5 | 4/5 | 1.4 | 0.4 | 43.434 |
| 4 | 2/5 | 4/5 | 2/5 | 4/5 | 1.8 | 0.8 | 51.954 |
| 5 | 4/5 | 4/5 | 5/5 | 5/5 | 1.4 | 0.4 | 47.739 |
| 6 | 4/5 | 5/5 | 4/5 | 4/5 | 1.4 | 0.4 | 46.78 |
| 7 | 1/5 | 4/5 | 2/5 | 2/5 | 1.8 | 0.8 | 48.136 |
| 8 | 1/5 | 4/5 | 3/5 | 3/5 | 2.2 | 1.2 | 53.924 |
| 9 | 3/5 | 4/5 | 4/5 | 4/5 | 2 | 1 | 51.95 |
| 10 | 2/5 | 5/5 | 2/5 | 2/5 | 1.8 | 0.8 | 52.636 |

## Initial-to-final behavior (bounded by available data)

Official-run rows do not store initial answers or per-iteration claim labels (debug_log_path is null for all rows), so initial-to-final answer transitions and claim-label transitions cannot be computed for the official sample. Rows with revisions == 0 are first-pass answers by construction. Trace-level transition evidence comes from the separately preserved qualitative executions in research/REPRESENTATIVE_TRACE_CASES.md.

| Group | Count | Exact | Contains | Resolved |
|---|---|---|---|---|
| First-pass (0 revisions) | 27 | 24 | 25 | 27 |
| Revised (≥1 revision) | 23 | 3 | 18 | 6 |

- Revised and resolved: 6
- Revised but unresolved: 17
- Revised and final answer still does not contain expected: 5

## Final claim-label totals (last iteration of each question)

| Label | Total claims | Questions containing label |
|---|---|---|
| SUPPORTED | 65 | 44 |
| CONTRADICTED | 1 | 1 |
| NO_EVIDENCE | 12 | 10 |

Initial claim-label counts and label transitions are not recoverable from the
official-run rows (see limitation above); trace-level examples appear in
`research/REPRESENTATIVE_TRACE_CASES.md`.

## Runner failure categories

| Category | Count |
|---|---|
| answer_matched_textually_but_pipeline_unresolved | 15 |
| target_not_satisfied | 1 |
| pipeline_unresolved | 1 |

