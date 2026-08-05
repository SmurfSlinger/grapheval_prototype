# Benchmark and analysis

## Official benchmark

- Dataset: `data/test_sets/apollo_multihop_50.json` (50 questions, depths 1–10 × 5)
- Runner: `scripts/run_multihop_benchmark.py`
- Frozen result: `results/research/apollo_multihop_llama31_8b_20260727T203028Z.json`

## Analysis scripts

| Script | Role |
|---|---|
| `scripts/analyze_final_experiment.py` | Recompute official aggregates; hard-fail on mismatch |
| `scripts/plot_final_experiment.py` | Figures under `results/research/figures/` |
| `scripts/analyze_repeatability_experiment.py` | Three-run comparison |
| `scripts/plot_repeatability_experiment.py` | Repeatability figures |
| `scripts/build_experiment_report_docx.py` | Regenerate report DOCX from Markdown + analysis JSON |

## Scoring note

Exact match, contains-expected, and related textual metrics are applied **after**
inference. Expected answers are excluded from inference prompts
(`tests/test_expected_answer_leakage.py`).
