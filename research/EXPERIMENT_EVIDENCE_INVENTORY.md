# GraphEval Experiment Evidence Inventory

Compiled: 2026-08-02
Branch: `research/final-experiment-report` (created from frozen reliability commit
`b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`, "Prevent claim alignment drift and preserve
unresolved answers", committed 2026-07-27 14:25:40 -0600).

This inventory records every artifact used by the final experiment analysis, whether it
is tracked in Git, what it contains, and whether it is sufficient for reproducible
analysis. Absent artifacts are recorded as absent; nothing below is inferred from
UI exports alone unless explicitly marked.

## 1. Authoritative primary-experiment artifacts (Apollo 50-question official run)

| Artifact | Path | Size | Type | Git-tracked | Contents |
|---|---|---|---|---|---|
| Raw result JSON | `results/research/apollo_multihop_llama31_8b_20260727T203028Z.json` | 204,849 B | JSON | untracked at time of inventory (committed on this research branch) | Full run metadata + 50 per-question raw rows (answers, labels, stop reasons, evidence paths, runtimes, execution IDs) |
| Summary Markdown | `results/research/apollo_multihop_llama31_8b_20260727T203028Z.md` | 2,719 B | Markdown | untracked at time of inventory (committed on this research branch) | Runner-generated aggregate summary and per-hop table |
| Runner log | `.runtime/research/apollo_multihop_llama31_8b_20260727T203028Z.log` | 7,666 B | text | not tracked (`.runtime/` gitignored) | Per-question progress lines + final aggregate JSON echo |
| Return code | `.runtime/research/apollo_multihop_llama31_8b_20260727T203028Z.rc` | 2 B | text | not tracked | Contains `0` (clean exit) |
| PID file | `.runtime/research/apollo_multihop_llama31_8b_20260727T203028Z.pid` | 5 B | text | not tracked | Run process id 9442 |
| Run env pointer | `.runtime/research/current-run.env` | 350 B | text | not tracked | OUT/SUMMARY/LOG/RC/PID paths for the official run |

SHA256 (raw JSON): `638a2718ae1e6bff149d96d0f8cfa1761eebfcfa6b38415155fcabcd7d327f46`
SHA256 (summary MD): `a82927c33739454fdfa03ea1fbf0c3dcf85fb7a2b575fd9cc96dffde6346f983`
SHA256 (runner log): `86596afc811e07f37c3ecdb3a77758bddbacd71c44676c2e83848c6c776c9a10`

Sufficiency: the raw JSON contains complete per-question rows for all 50 questions
(no errors, no truncation; `is_partial: false`). It is sufficient for reproducible
quantitative analysis. It does NOT preserve initial (pre-revision) answers or
per-iteration claim-label sequences; those exist only in per-execution debug traces,
which the official benchmark run did not persist per question (`debug_log_path: null`
in all 50 rows). This limits initial-to-final transition analysis for the official
run (documented in the analysis and report).

### Exact run command (verified from shell history, line 274 of `~/.bash_history`)

```bash
( export NEO4J_ENABLED=true; export NEO4J_REQUIRED=true; export OLLAMA_NUM_CTX=8192; \
  export OLLAMA_NUM_PREDICT=4096; export OLLAMA_TEMPERATURE=0; \
  .venv/bin/python scripts/run_multihop_benchmark.py \
    --provider ollama --model llama3.1:8b --num-ctx 8192 --max-iterations 3 \
    --clear-neo4j --timeout-per-question 180 --continue-on-error \
    --cooldown-seconds 2 --max-consecutive-timeouts 3 \
    --output "$OUT" --summary "$SUMMARY"; \
  echo $? > "$RC"; ) > "$LOG" 2>&1 &
```

with `OUT/SUMMARY/LOG/RC` as recorded in `.runtime/research/current-run.env`.
Note `OLLAMA_TEMPERATURE=0` and `OLLAMA_NUM_PREDICT=4096` were set for the run.

### Verified aggregates (from raw JSON `summary` block; independently recomputed by
`scripts/analyze_final_experiment.py`)

- attempted 50, completed 50, errored 0
- exact match 27 (54.0%)
- contains expected 43 (86.0%)
- pipeline resolved 33 (66.0%)
- average iterations 1.66, average runtime 48.42 s

## 2. Benchmark dataset

| Artifact | Path | Git-tracked | Notes |
|---|---|---|---|
| Apollo 50-question set | `data/test_sets/apollo_multihop_50.json` | yes | SHA256 `17a13db9b9a7c894af6b0cd869e18a9e6f6272f07eb8dce15be1f2d063521df0` |
| NHS WannaCry 50-question set | `data/test_sets/nhs_wannacry_multihop_50.json` | yes | SHA256 `babe0b6c75fa4f644b5fb155a36ebd945a116464e66304dec5b3da41adbbefdd` |
| WannaCry audit | `data/test_sets/nhs_wannacry_multihop_50.audit.json` | yes | hop-semantics audit |
| Depth acceptance ID lists | `data/test_sets/apollo_depth_acceptance_ids.json`, `nhs_depth_acceptance_ids.json` | yes | used by diagnostic depth runs |

Dataset validation embedded in the official result JSON confirms: 50 questions,
5 per designed depth 1–10 (`hop_distribution` all = 5), valid, no errors,
42 nodes, 48 edges, 1 connected component, root `Apollo 11`, 5 branches reaching
depth 10.

## 3. Qualitative case debug traces (runtime evidence, `.runtime/debug/`, not Git-tracked)

| Execution ID | Trace file | Size | Verified |
|---|---|---|---|
| `apollo_hop_046__20260727T190016Z__0e37a955` (pre-fix diagnostic) | `.runtime/debug/20260727T190016Z_apollo_hop_046_attempt_7dbf3e1b.jsonl` | 118,863 B | execution_id read from trace; STALLED; unsafe alignment events present |
| `apollo_hop_046__20260727T202312Z__50843932` (post-fix diagnostic) | `.runtime/debug/20260727T202312Z_apollo_hop_046_attempt_91bb9b85.jsonl` | 78,435 B | execution_id read from trace; RESOLVED, answer "Oceanography" |
| `nhs_wannacry_h10_q01__20260727T214622Z__4adc0f88` (qualitative case) | `.runtime/debug/20260727T214622Z_nhs_wannacry_h10_q01_attempt_70a052a7.jsonl` | 121,656 B | execution_id read from trace; UNRESOLVED_NO_EVIDENCE + STALLED; 21 anomalies |

SHA256:
- pre-fix Apollo trace: `083e8480f6747f66023385e9882067d0308d1de1c8b86d4c0d8013b66d0bb240`
- post-fix Apollo trace: `e4c7ecd7d9a4ef5291d1a7b265a8a94da4791f50d30266369e9c13de6ecc1c2c`
- WannaCry trace: `a71d678c6abd1f6afcdfa1c064823c00a166c34541c8932925cb25efc9c1632a`

Companion raw-model-output artifacts (same directory, `*_context_fact_extraction_raw.txt`,
`*_claim_extraction_raw.txt`) exist for the post-fix Apollo and WannaCry executions and
partially for others.

Note: these three executions do NOT appear as rows in any checkpointed benchmark
result file; they were standalone API/diagnostic executions. The jsonl traces are the
preserved evidence.

## 4. Diagnostic / acceptance benchmark artifacts (`.runtime/benchmarks/`, not Git-tracked)

- `apollo_depth_acceptance.json/.md` plus `attempt1`–`attempt4` variants: bounded
  depth-{1,2,3,10} live acceptance runs performed during reliability validation before
  the official experiment (post-fix instrument validation).
- `nhs_depth_acceptance.json/.md` + run log: the WannaCry depth-acceptance run from the
  same session as execution `...214622Z__4adc0f88`.

These are pre-experiment or diagnostic samples; they are kept separate from the
official quantitative sample throughout the analysis.

## 5. Pre-fix baseline result files (tracked in Git, from master-era runs)

- `results/apollo_multihop_real_baseline.json/.md` (2026-07-26)
- `results/nhs_wannacry_multihop_real_baseline.json/.md` (2026-07-26)
- `results/apollo_multihop_report.json`, smoke/partial variants

These pre-date the frozen reliability commit and are used only as historical context;
they are never combined with the official post-fix sample.

## 6. Analysis artifacts generated on this research branch

- `scripts/analyze_final_experiment.py` → `results/research/grapheval_final_experiment_analysis.json/.md`
- `scripts/plot_final_experiment.py` → `results/research/figures/*.png` + `figure_data.json`
- `tests/test_analyze_final_experiment.py` (analysis-script unit tests)
- `research/REPRESENTATIVE_TRACE_CASES.md`, `research/EXPERIMENT_PROTOCOL.md`,
  `research/REPRODUCIBILITY_RECORD.md`
- `reports/GraphEval Experiment Report.md/.docx`, handoff documents

Pre-existing untracked artifacts from an earlier analysis session
(`scripts/analyze_benchmark_results.py`,
`results/research/apollo_multihop_llama31_8b_20260727T203028Z.analysis.json/.md`) are
preserved unmodified; the new analysis supersedes them for the report and its numbers
were cross-checked against them.

## 6b. Repeatability extension artifacts (added 2026-08-03, branch `research/repeatability-study`)

| Artifact | Type | Git-tracked | Contents |
|---|---|---|---|
| `results/research/repeatability/apollo_repeat_run2_llama31_8b_20260803T012414Z.{json,md}` | raw rows + summary | committed on the repeatability branch | Run 2: complete 50-row exact-configuration repetition (exit 0) |
| `results/research/repeatability/apollo_repeat_run3_llama31_8b_20260803T020637Z.{json,md}` | raw rows + summary | committed on the repeatability branch | Run 3: complete 50-row exact-configuration repetition (exit 0) |
| `results/research/repeatability/grapheval_repeatability_analysis.{json,md}` | aggregate + per-question comparison | committed | Three-run stability analysis (`scripts/analyze_repeatability_experiment.py`) |
| `results/research/repeatability/figures/figR1–figR4 + figure_data.json` | figures | committed | Generated by `scripts/plot_repeatability_experiment.py` |
| `.runtime/research/repeatability/*.{log,rc,cmd}`, `wrapper_state.txt` | run logs / exit codes / exact commands | not tracked (`.runtime/` gitignored) | Per-run execution evidence; SHA256s of results recorded in REPRODUCIBILITY_RECORD.md |
| `research/REPEATABILITY_PROTOCOL.md`, `research/REPEATABILITY_CASES.md` | protocol + cases | committed | Study design and reproduced representative cases |

Run 1 of the study is the unmodified official artifact of §1 (SHA256 re-verified
before the study). No failed or partial runs occurred; nothing was rerun.

## 7. Missing / absent artifacts (recorded, not fabricated)

| Expected artifact | Status | Impact |
|---|---|---|
| `Experiment Template-verJuly272026.docx` | ABSENT from repository, WSL home, Windows user folders, and agent mounts (searched by filename) | Report built from the professor's template section structure specified in the task; reference copy could not be placed in `docs/templates/`. TODO: obtain the original DOCX to confirm styling/header/footer expectations. |
| `Research Project Report Template-verJuly102026.docx` | ABSENT (same searches) | Project-report handoff uses the specified 8-section structure. |
| `Pasted text(44).txt` (WannaCry UI export) | ABSENT | The local runtime trace `.runtime/debug/20260727T214622Z_..._70a052a7.jsonl` independently preserves the execution and is used as the primary evidence. Fields reported only in the UI export and NOT locally verifiable: per-subquestion `question_target` = true, evidence-path `missing_intermediate_edge`, exact runtime ~1 min 31 s. These are cited as UI-export-only observations in the case study. |
| Per-question debug traces for the official 50-question run | Never persisted (`debug_log_path: null` in all rows) | Initial-vs-final answer transitions for the official run are only partially derivable (revisions == 0 implies unchanged); documented as a limitation. |
| GitHub PR #5 check metadata | Not accessible from this environment (no `gh` CLI/credentials) | PR-reported test counts (26 focused / 93+1 pipeline / 406+16 offline) verified instead by re-running the offline suite on the frozen branch (see REPRODUCIBILITY_RECORD.md). |

## 8. Instrument validation evidence

- Full offline test suite re-run on this branch (2026-08-02): see
  `research/REPRODUCIBILITY_RECORD.md` for exact command and result.
- Frontend lint/build: reported passing in PR #5 at freeze time; not re-run in this
  research pass because no frontend code was changed (per scope).
- Live depth acceptance (Apollo depths 1, 2, 3, 10) after the reliability fix:
  evidenced by `.runtime/benchmarks/apollo_depth_acceptance*.{json,md}`.
- Execution isolation & FACT/CLAIM separation: covered by tracked tests
  (`tests/test_local_neo4j_custom_run.py`, `tests/test_neo4j_live_integration.py`,
  `tests/test_expected_answer_leakage.py`, `tests/test_pipeline_alignment_and_unresolved_integrity.py`).
