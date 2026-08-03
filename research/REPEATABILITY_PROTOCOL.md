# Repeatability and Nondeterminism Study Protocol

Extension of the completed GraphEval Experiment Report. Executed 2026-08-02/03 on
branch `research/repeatability-study` (created from report HEAD `3f01ea1`).

## Hypothesis / goal

Descriptive goal: quantify which outputs of the frozen GraphEval instrument remain
consistent and which vary when the identical 50-question Apollo experiment is
executed three times with an identical configuration. The study characterizes
measurement stability; it does not test a causal hypothesis.

## Design

- Exactly three complete runs of `data/test_sets/apollo_multihop_50.json`:
  - **Run 1** — the pre-specified official run
    (`results/research/apollo_multihop_llama31_8b_20260727T203028Z.json`,
    2026-07-27), retained unmodified as the primary experiment.
  - **Run 2** and **Run 3** — new complete repetitions executed sequentially
    (never in parallel) on 2026-08-03 UTC via a bounded wrapper that validated
    Run 2 (exit code 0, complete 50-row `full_real` sample) before starting Run 3.
- No more than two additional complete runs; no individual questions rerun; no
  selective reruns of unfavorable results.

## Fixed variables (identical across all three runs)

- Inference implementation frozen at `b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`
  (verified before the study: `git diff --exit-code b9608d0 -- src api prompts
  data/test_sets/apollo_multihop_50.json scripts/run_multihop_benchmark.py
  scripts/recreate-neo4j.sh scripts/devctl.sh` reported no differences).
- Model `llama3.1:8b` via Ollama (same local model digest `46e0c10c039e`),
  `OLLAMA_NUM_CTX=8192`, `OLLAMA_NUM_PREDICT=4096`, `OLLAMA_TEMPERATURE=0`.
- Runner flags: `--max-iterations 3 --clear-neo4j --timeout-per-question 180
  --continue-on-error --cooldown-seconds 2 --max-consecutive-timeouts 3`.
- Neo4j 5.26.0 (same `grapheval-neo4j` Docker container), enabled and required,
  cleared between questions, execution-scoped storage.
- Dataset, expected answers, prompts, thresholds: untouched.
- No UI use and no concurrent Neo4j-clearing process during runs.

Temperature 0 reduces but does not eliminate nondeterminism (GPU scheduling and
floating-point reduction order can still vary token choices; the pipeline also
has order-sensitive components downstream of any wording change).

## Comparison measures

- Per-run aggregates with across-run mean/min/max/range.
- Per-question stability across all three runs for: normalized final answer,
  exact match, contains-expected, resolved status, stop reason, evidence-path
  completeness, terminal claim, final label tuple.
- Primary stability categories per question (documented precedence in
  `scripts/analyze_repeatability_experiment.py:classify`).
- Pairwise raw agreement (primary) with Cohen's kappa for booleans (reference
  only).
- Depth-level counts (five questions per depth per run — always stated).
- Revision-behavior variability.

## Limitations stated in advance

- n = 50 questions and 3 runs: adequate for descriptive stability counts, not
  strong statistical inference.
- The three runs are repeated measurements of the same 50 questions — never
  pooled as 150 independent questions.
- Result rows do not preserve intermediate answers or claim-label transitions;
  correction-vs-regression within a specific revision cannot be inferred from
  these files (official-run trace limitation documented in the Experiment Report
  §3.5 applies to all three runs).
- Result rows alone do not isolate the causal stage of any observed variation.

## Infrastructure-failure handling

A run may be repeated only if it failed to produce a valid complete sample for
clearly infrastructure-related reasons (transport/process/service); any failed
artifact is preserved under `results/research/repeatability/` and documented, and
no rows from a failed run are pooled. (No such failure occurred; see
REPRODUCIBILITY_RECORD.md.)

## Separation from the official analysis

The official Run 1 numbers remain the report's headline results. Repeatability
results are reported separately as an extension (per-run values plus across-run
range/mean), never replacing or pooling with the original headline numbers.
