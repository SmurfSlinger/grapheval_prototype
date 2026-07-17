# Apollo multi-hop benchmark summary

This is a measurement report, not a tuned success criterion.

- Date/time: `2026-07-17T13:55:58.414066+00:00`
- Branch: `cursor/cloud-agent-1784294800421-ztfpf`
- Provider/model: `ollama` / `gemma4:e2b`
- Configured num_ctx: `8192`
- Run type: **partial_real**
- Attempted/completed/errored: 2 / 2 / 0
- Exact-match accuracy: 100.0%
- Contains-expected accuracy: 100.0%
- Pipeline-resolved count: 2
- Resolved and matched: 2
- Unresolved but answer contained expected: 0
- Average iterations: 1.00
- Average runtime: 238.80s

## Accuracy by hop count

| Hop count | Questions | Completed | Exact match | Contains expected | Pipeline resolved | Avg iterations | Avg runtime | Common failures |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 2 | 2 | 2 | 2 | 2 | 1.00 | 238.80s | — |

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
- Max prompt characters: 6018
- Approximate max prompt tokens: 1505
- Largest prompt stage: `None`
- Any prompt approached window: False
- Recommendation: The configured window covered observed prompts; increase it only if later questions show cutoff evidence and hardware permits.

## Failure categories

- None recorded.

## Interpretation

Textual answer matching and deterministic pipeline resolution are reported separately. An answer may contain the expected entity while the pipeline remains unresolved, or resolve without matching the benchmark answer. No expected answer is supplied to inference and no pipeline labels are overridden by this report.
