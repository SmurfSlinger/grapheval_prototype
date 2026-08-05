# Project overview

GraphEval Prototype is an undergraduate research instrument for observing
LLM answers as knowledge-graph claims evaluated against trusted context facts.

It is **not** a complete conversational memory system. It runs an external loop:
extract triples from answers, label them against FACTs, feed structured feedback,
revise, and validate targets and trusted evidence paths.

## Core distinctions

| Term | Meaning |
|---|---|
| FACT | Trusted subject–relation–object triple from supplied context (or working enrichment with provenance) |
| CLAIM | Subject–relation–object triple from a model answer |
| Labels | `SUPPORTED`, `CONTRADICTED`, `NO_EVIDENCE` — computed in Python |
| Supported CLAIM | Remains a CLAIM; never promoted to a FACT |

## Primary code entry points

- Benchmark: `scripts/run_multihop_benchmark.py`
- Live runner: `src.pipeline.decomposed_backtracking_runner.DecomposedBacktrackingRunner`
- Persistence: `src.storage.neo4j_store.Neo4jStore`
- Comparison: `src.pipeline.graph_comparator.GraphComparator`

## Experiment outcomes (official Apollo sample)

50 complete / 0 errors / 0 timeouts; 27 exact; 43 contain expected; 33 pipeline
resolved; 36 complete evidence paths. Model: `llama3.1:8b` via Ollama at commit
`b9608d0`. See the Experiment Report under `reports/`.
