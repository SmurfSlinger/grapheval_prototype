# Apollo multi-hop benchmark summary

This is a measurement report, not a tuned success criterion.

- Date/time: `2026-07-17T14:52:08.450445+00:00`
- Branch: `cursor/cloud-agent-1784294800421-ztfpf`
- Provider/model: `ollama` / `gemma4:e2b`
- Configured num_ctx: `8192`
- Run type: **partial_real**
- Attempted/completed/errored: 15 / 15 / 0
- Exact-match accuracy: 53.3%
- Contains-expected accuracy: 93.3%
- Pipeline-resolved count: 13
- Resolved and matched: 12
- Unresolved but answer contained expected: 2
- Average iterations: 1.13
- Average runtime: 256.51s

## Accuracy by hop count

| Hop count | Questions | Completed | Exact match | Contains expected | Pipeline resolved | Avg iterations | Avg runtime | Common failures |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 5 | 5 | 4 | 5 | 5 | 1.00 | 236.74s | — |
| 2 | 5 | 5 | 2 | 5 | 5 | 1.00 | 218.90s | — |
| 3 | 5 | 5 | 2 | 4 | 3 | 1.40 | 313.89s | answer_matched_textually_but_pipeline_unresolved (2) |

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
- Max prompt characters: 6095
- Approximate max prompt tokens: 1524
- Largest prompt stage: `None`
- Any prompt approached window: False
- Recommendation: The configured window covered observed prompts; increase it only if later questions show cutoff evidence and hardware permits.

## Failure categories

- `answer_matched_textually_but_pipeline_unresolved`: 2

## Interpretation

Textual answer matching and deterministic pipeline resolution are reported separately. An answer may contain the expected entity while the pipeline remains unresolved, or resolve without matching the benchmark answer. No expected answer is supplied to inference and no pipeline labels are overridden by this report.
