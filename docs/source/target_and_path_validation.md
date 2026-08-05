# Target and path validation

## Distinction

| Check | When | Module |
|---|---|---|
| Textual exact/contains | Post-inference only | Benchmark runner / analyzers |
| Target satisfaction | During iteration | `src/pipeline/question_target.py` |
| Evidence path | During iteration | `src/pipeline/evidence_path_resolver.py` |

Expected answers and expected paths are **not** available during inference.

## Evidence path

Walks trusted FACT edges from a start entity to a terminal claim (preferring a
matched FACT for a SUPPORTED claim). Observed failure reasons include
`missing_intermediate_edge` and `terminal_claim_not_a_trusted_fact`.

Official example (final state only): `apollo_hop_036` complete 7-edge path ending
`Chesapeake Bay — opens_into → Atlantic Ocean`.
