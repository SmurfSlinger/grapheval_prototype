# Algorithm overview

Live path: `DecomposedBacktrackingRunner.run_example` driven by
`scripts/run_multihop_benchmark.py` or the API.

```{figure} ../diagrams/rendered/grapheval_algorithm_overview.svg
:alt: Algorithm overview with LLM, Python, Neo4j, and scoring lanes

Simplified conceptual overview. Exact Neo4j properties are in neo4j_persistence.
```

## Lane responsibilities

| Lane | Responsibilities |
|---|---|
| LLM | Question split, FACT extract, answer/projection, CLAIM extract, revision |
| Python | Validation, schema alignment, comparison/labels, feedback, target, path, stop |
| Neo4j | MERGE FACTs, optional FACT readback, CREATE CLAIM appends, working FACT writes |
| Post-inference | Exact/contains scoring vs expected answers (never during inference) |

## Iteration engine

Per sub-question, `KgcIterationEngine` (`src/pipeline/kgc_iteration.py`) runs
extract → align → compare → target/path → feedback → revise until
`determine_stop_reason` returns a stop or the iteration budget is exhausted
(official experiment: 3).

See also `research/METHODOLOGY_DOCUMENTATION_AUDIT.md` for the verified call sequence.
