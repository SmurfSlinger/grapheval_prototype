# Apollo multi-hop benchmark summary

This is a measurement report, not a tuned success criterion.

- Date/time: `2026-07-17T13:25:22.705000+00:00`
- Branch: `feature/local-neo4j-custom-runs`
- Provider/model: `ollama` / `gemma4:e2b`
- Configured num_ctx: `32768`
- Run type: **partial_real**
- Attempted/completed/errored: 2 / 0 / 2
- Exact-match accuracy: 0.0%
- Contains-expected accuracy: 0.0%
- Pipeline-resolved count: 0
- Resolved and matched: 0
- Unresolved but answer contained expected: 0
- Average iterations: 0.00
- Average runtime: 120.00s

## Accuracy by hop count

| Hop count | Questions | Completed | Exact match | Contains expected | Pipeline resolved | Avg iterations | Avg runtime | Common failures |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 1 | 0 | 0 | 0 | 0 | 0.00 | 120.00s | model_timeout (1) |
| 3 | 1 | 0 | 0 | 0 | 0 | 0.00 | 120.00s | model_timeout (1) |

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

- Configured num_ctx: `32768`
- Max prompt characters: 5928
- Approximate max prompt tokens: 1482
- Largest prompt stage: `None`
- Any prompt approached window: False
- Recommendation: The configured window covered observed prompts; increase it only if later questions show cutoff evidence and hardware permits.

## Failure categories

- `model_timeout`: 2

## Interpretation

Textual answer matching and deterministic pipeline resolution are reported separately. An answer may contain the expected entity while the pipeline remains unresolved, or resolve without matching the benchmark answer. No expected answer is supplied to inference and no pipeline labels are overridden by this report.
