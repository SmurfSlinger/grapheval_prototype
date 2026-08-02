# GraphEval Official Experiment Protocol (as executed)

This document records the protocol of the completed official experiment as verified
from artifacts. It documents what was done; it is not a proposal for new runs.

## Experiment identity

- Name: Apollo 50-question multihop benchmark, official post-fix measurement run
- Result ID: `apollo_multihop_llama31_8b_20260727T203028Z`
- Executed: 2026-07-27, finishing 21:12:37 UTC (run window ≈ 20:30–21:12 UTC)
- Software state: branch `debug/8b-hop-validation`, frozen reliability commit
  `b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`
- Run type: `full_real`, `is_partial: false`, exit code 0

## Dataset

- `data/test_sets/apollo_multihop_50.json` (Git-tracked)
- 50 questions, exactly 5 per designed graph-path depth 1–10 (validator-confirmed)
- Designed graph: 42 nodes, 48 edges, 1 connected component, root `Apollo 11`,
  5 branches reaching depth 10, average expected hop count 5.5
- Expected answers and expected paths are used only for post-inference scoring;
  they are never provided to the LLM (enforced by `tests/test_expected_answer_leakage.py`)

"Designed hop depth" means root-to-answer graph-path depth in the fixed benchmark
graph. It does not dictate visible reasoning steps, LLM call counts, or decomposition.

## System configuration (verified)

| Component | Value | Verified from |
|---|---|---|
| LLM provider | Ollama (`OllamaProvider` at every LLM stage) | result JSON + traces |
| Model | `llama3.1:8b` | result JSON |
| Context window | `num_ctx` 8192 (max observed prompt ≈ 1670 tokens; never approached limit) | result JSON prompt telemetry |
| Sampling | `OLLAMA_TEMPERATURE=0`, `OLLAMA_NUM_PREDICT=4096` | preserved shell history |
| Iteration limit | 3 per sub-question (`--max-iterations 3`) | shell history |
| Timeout | 180 s per question (`--timeout-per-question 180`); 0 timeouts occurred | result JSON |
| Neo4j | enabled and required; `neo4j:5.26.0` (Docker, per `scripts/recreate-neo4j.sh`); cleared between questions (`--clear-neo4j`); evaluation source `neo4j_readback` for all 50 rows | result JSON |
| Python | `.venv` CPython 3.12.3 (current environment; interpreter version at run time not separately recorded) | environment |
| Hardware | local WSL2/Ubuntu workstation hosting Ollama; detailed hardware specs were not recorded in run artifacts and are therefore not claimed | absence recorded |
| Runner | `scripts/run_multihop_benchmark.py` with `--continue-on-error --cooldown-seconds 2 --max-consecutive-timeouts 3` | shell history |

Exact command: see `research/EXPERIMENT_EVIDENCE_INVENTORY.md` §1.

## Pipeline procedure per question (component responsibilities)

LLM stages (nondeterministic, via Ollama): question decomposition, context FACT
extraction, initial answer generation, sub-answer projection, CLAIM extraction,
answer revision.

Deterministic Python stages: decomposition validation, structured-triple validation
(anomaly rejection), schema-alignment safety checks, claim comparison and label
assignment (SUPPORTED / CONTRADICTED / NO_EVIDENCE), question-target derivation and
validation, trusted evidence-path resolution, stop-condition logic, answer
combination, post-inference benchmark scoring, trace and metric construction.

Neo4j: persists FACT and CLAIM relationships scoped by execution ID; serves the
working graph readback; never generates answers, never sees expected answers, never
promotes a supported CLAIM into a FACT.

Steps: (1) load question + trusted context; (2) optionally decompose; (3) extract
FACTs from context, validate triples, write to Neo4j, read back working graph;
(4) generate initial answer; (5) project the compound answer onto sub-questions;
(6) extract CLAIMs from each sub-answer; (7) apply safe schema alignment;
(8) compare CLAIMs to FACTs; (9) assign labels; (10) build structured feedback;
(11) revise the answer; (12) validate the derived question target; (13) validate
the trusted evidence path; (14) stop (RESOLVED / STALLED / UNRESOLVED_*) or iterate
up to the limit; (15) combine sub-answers; (16) score textually after inference;
(17) persist row + metrics (and, when enabled, a JSONL debug trace).

## Analysis procedure

1. Quantitative: `.venv/bin/python scripts/analyze_final_experiment.py`
   reads the raw result JSON, recomputes every aggregate from the 50 rows, hard-fails
   if any recomputed aggregate disagrees with the runner's summary block, and writes
   `results/research/grapheval_final_experiment_analysis.{json,md}`.
2. Figures: `.venv/bin/python scripts/plot_final_experiment.py` reads the analysis
   JSON and writes `results/research/figures/*.png` + `figure_data.json`.
3. Qualitative: representative cases selected from official rows and preserved
   debug traces (selection criteria and full excerpts in
   `research/REPRESENTATIVE_TRACE_CASES.md`); no new model executions were performed.

## Sample separation rules

- Official quantitative sample: the 50 rows of the official result JSON only.
- Pre-fix diagnostics (e.g. `apollo_hop_046__20260727T190016Z__0e37a955`) and
  depth-acceptance runs: instrument-development evidence only.
- WannaCry execution `nhs_wannacry_h10_q01__20260727T214622Z__4adc0f88`: qualitative
  case study only (different benchmark, single execution).
- Nondeterminism: a repeated execution is a new sample, not a correction of a
  previous one; no problematic run was rerun to obtain a preferred outcome, and
  pre-fix and post-fix rows are never pooled.

## Human participants

None. All data are synthetic benchmark questions (Apollo/NASA public history) or
questions grounded in public UK government and Microsoft/CISA documents (WannaCry).
