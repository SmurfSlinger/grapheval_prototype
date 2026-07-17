# nhs wannacry multihop 50 benchmark summary

This is a measurement report, not a tuned success criterion.

- Date/time: `2026-07-17T21:37:58.288901+00:00`
- Branch: `codex/cursor-cloud-agent-branch`
- Provider/model: `ollama` / `gemma4:e2b`
- Configured num_ctx: `32768`
- Run type: **partial_real**
- Attempted/completed/errored: 1 / 1 / 0
- Exact-match accuracy: 0.0%
- Contains-expected accuracy: 100.0%
- Pipeline-resolved count: 1
- Resolved and matched: 1
- Unresolved but answer contained expected: 0
- Average iterations: 1.00
- Average runtime: 71.23s

## Accuracy by hop count

| Hop count | Questions | Completed | Exact match | Contains expected | Pipeline resolved | Avg iterations | Avg runtime | Common failures |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 1 | 1 | 0 | 1 | 1 | 1.00 | 71.23s | — |

## Graph properties

- Node count: 88
- Edge count: 87
- Connected components: 1
- Root node: `WannaCry attack on the NHS`
- Max designed hop depth: 10
- Root branching factor: 12
- Average expected hop count: 5.5
- Branches reaching 10 hops: 5

## Prompt/context size

- Configured num_ctx: `32768`
- Max prompt characters: 9329
- Approximate max prompt tokens: 2333
- Largest prompt stage: `None`
- Any prompt approached window: False
- Recommendation: The configured window covered observed prompts; increase it only if later questions show cutoff evidence and hardware permits.

## Failure categories

- None recorded.

## Interpretation

Textual answer matching and deterministic pipeline resolution are reported separately. An answer may contain the expected entity while the pipeline remains unresolved, or resolve without matching the benchmark answer. No expected answer is supplied to inference and no pipeline labels are overridden by this report.
