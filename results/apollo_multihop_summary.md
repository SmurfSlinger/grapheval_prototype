# Apollo multi-hop benchmark summary

This is a measurement report, not a tuned success criterion.

- Date/time: `2026-07-17T13:39:39.724072+00:00`
- Branch: `cursor/cloud-agent-1784294800421-ztfpf`
- Provider/model: `mock` / `gemma4:12b`
- Configured num_ctx: `None`
- Run type: **mock_plumbing**
- Attempted/completed/errored: 50 / 0 / 50
- Exact-match accuracy: 0.0%
- Contains-expected accuracy: 0.0%
- Pipeline-resolved count: 0
- Resolved and matched: 0
- Unresolved but answer contained expected: 0
- Average iterations: 0.00
- Average runtime: 0.00s

## Accuracy by hop count

| Hop count | Questions | Completed | Exact match | Contains expected | Pipeline resolved | Avg iterations | Avg runtime | Common failures |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |
| 2 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |
| 3 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |
| 4 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |
| 5 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |
| 6 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |
| 7 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |
| 8 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |
| 9 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |
| 10 | 5 | 0 | 0 | 0 | 0 | 0.00 | 0.00s | projection_failure (5) |

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

- Configured num_ctx: `None`
- Max prompt characters: 0
- Approximate max prompt tokens: 0
- Largest prompt stage: `None`
- Any prompt approached window: False
- Recommendation: No successful real-provider prompt telemetry was recorded; run a real smoke before changing context size.

## Failure categories

- `projection_failure`: 50

## Interpretation

Textual answer matching and deterministic pipeline resolution are reported separately. An answer may contain the expected entity while the pipeline remains unresolved, or resolve without matching the benchmark answer. No expected answer is supplied to inference and no pipeline labels are overridden by this report.

## Mock-provider limitation

The deterministic mock has no profile for this new context. Projection failures validate report plumbing only and are not model-performance results.
