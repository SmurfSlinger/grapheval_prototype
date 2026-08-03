# apollo multihop 50 benchmark summary

This is a measurement report, not a tuned success criterion.

- Date/time: `2026-08-03T02:06:32.431156+00:00`
- Branch: `research/repeatability-study`
- Provider/model: `ollama` / `llama3.1:8b`
- Configured num_ctx: `8192`
- Run type: **full_real**
- Attempted/completed/errored: 50 / 50 / 0
- Exact-match accuracy: 54.0%
- Contains-expected accuracy: 86.0%
- Pipeline-resolved count: 33
- Resolved and matched: 28
- Unresolved but answer contained expected: 15
- Average iterations: 1.66
- Average runtime: 46.73s

## Accuracy by hop count

| Hop count | Questions | Completed | Exact match | Contains expected | Pipeline resolved | Avg iterations | Avg runtime | Common failures |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 5 | 5 | 4 | 5 | 4 | 1.20 | 42.57s | answer_matched_textually_but_pipeline_unresolved (1) |
| 2 | 5 | 5 | 3 | 5 | 3 | 1.60 | 45.82s | answer_matched_textually_but_pipeline_unresolved (2) |
| 3 | 5 | 5 | 3 | 3 | 4 | 1.40 | 42.02s | target_not_satisfied (1) |
| 4 | 5 | 5 | 2 | 4 | 2 | 1.80 | 49.84s | answer_matched_textually_but_pipeline_unresolved (2), pipeline_unresolved (1) |
| 5 | 5 | 5 | 4 | 4 | 5 | 1.40 | 45.58s | — |
| 6 | 5 | 5 | 4 | 5 | 4 | 1.40 | 44.27s | answer_matched_textually_but_pipeline_unresolved (1) |
| 7 | 5 | 5 | 1 | 4 | 2 | 1.80 | 45.91s | answer_matched_textually_but_pipeline_unresolved (3) |
| 8 | 5 | 5 | 1 | 4 | 3 | 2.20 | 51.57s | answer_matched_textually_but_pipeline_unresolved (2) |
| 9 | 5 | 5 | 3 | 4 | 4 | 2.00 | 49.67s | answer_matched_textually_but_pipeline_unresolved (1) |
| 10 | 5 | 5 | 2 | 5 | 2 | 1.80 | 50.03s | answer_matched_textually_but_pipeline_unresolved (3) |

## Graph properties

- Node count: 42
- Edge count: 48
- Connected components: 1
- Root node: `Apollo 11`
- Max designed hop depth: 10
- Root branching factor: 5
- Average expected hop count: 5.5
- Branches reaching 10 hops: 5

## Prompt/context size

- Configured num_ctx: `8192`
- Max prompt characters: 6678
- Approximate max prompt tokens: 1670
- Largest prompt stage: `None`
- Any prompt approached window: False
- Recommendation: The configured window covered observed prompts; increase it only if later questions show cutoff evidence and hardware permits.

## Failure categories

- `answer_matched_textually_but_pipeline_unresolved`: 15
- `target_not_satisfied`: 1
- `pipeline_unresolved`: 1

## Interpretation

Textual answer matching and deterministic pipeline resolution are reported separately. An answer may contain the expected entity while the pipeline remains unresolved, or resolve without matching the benchmark answer. No expected answer is supplied to inference and no pipeline labels are overridden by this report.
