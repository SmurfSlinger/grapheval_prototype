# Apollo multi-hop benchmark summary

This is a measurement report, not a tuned success criterion.

- Provider/model: `ollama` / `gemma4:e2b`
- Configured context: `32768`
- Questions run: 1
- Overall accuracy: 100.0%

## Accuracy by hop count

| Hops | Questions | Correct | Accuracy | Avg iterations | Unresolved | Retries |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 1 | 100.0% | 1.00 | 1 | 0 |

## Common failure types

- `one_or_more_sub_questions_unresolved`: 1

## Degradation note

Inspect the first hop group where accuracy falls or unresolved counts rise. No pipeline tuning is performed by this runner.

## Prompt-size note

The largest prompt is reported from successful provider calls. Token counts are approximate characters / 4, and stage labels are currently unavailable.
