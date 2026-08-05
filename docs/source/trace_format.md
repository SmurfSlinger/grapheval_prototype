# Trace format

Debug traces are JSONL files (typically under `.runtime/debug/`, gitignored).
Each line is one event with fields such as `stage`, `event`, `sub_question_id`,
and `data`.

## Observed stages (non-exhaustive)

`request_received`, `example_constructed`, `question_split_parsed`,
`context_fact_extraction`, `structured_triple_validated`,
`structured_triple_anomaly`, `context_fact_parsed`, `neo4j_fact_write`,
`neo4j_fact_readback`, `claim_extraction`, `claim_parsed`, `claim_alignment`,
`claim_comparison`, `feedback_built` / revision stages, `sub_question_finished`,
`combined_answer`, `run_finished`.

## Recommended walks

| Purpose | Artifact |
|---|---|
| Short SUPPORTED / RESOLVED | `.runtime/debug/20260727T202312Z_apollo_hop_046_attempt_91bb9b85.jsonl` |
| Full regression + CONTRADICTED / NO_EVIDENCE | `.runtime/debug/20260727T214622Z_nhs_wannacry_h10_q01_attempt_70a052a7.jsonl` |

Hashes: `research/REPRODUCIBILITY_RECORD.md`.

Official Apollo 50 rows often have `debug_log_path: null` — do not invent missing
intermediate answers.
