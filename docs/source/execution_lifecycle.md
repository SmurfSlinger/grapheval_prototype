# Execution lifecycle

1. `ExecutionScope.begin` → `execution_id`
2. Optional clear of that execution only
3. Optional decomposition
4. Context FACT extract → validate → Neo4j MERGE FACT → optional readback
5. Answer / project
6. Per sub-question iteration loop (`KgcIterationEngine`)
7. Append CLAIM edges for all iterations in history
8. Combine answers; store working FACTs
9. Benchmark scoring (post-inference)

## Isolation

Cross-question isolation is primarily by unique `execution_id`. Official Apollo
runs also used `--clear-neo4j` so each question’s clear targets that execution’s
entities. A full database wipe is `clear_all` / volume recreate — not the normal
per-question path.

## Official Apollo limitation

Aggregate result rows have `debug_log_path: null`, so per-iteration debug JSONL was
not retained for the 50-question official sample.
