# Reproducibility Record — GraphEval Final Experiment Analysis

Compiled 2026-08-02 on branch `research/final-experiment-report`.

## Frozen software state

- Official experiment commit: `b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`
  ("Prevent claim alignment drift and preserve unresolved answers",
  2026-07-27 14:25:40 -0600), branch `debug/8b-hop-validation`
  (= `origin/debug/8b-hop-validation`, PR #5, open/draft/unmerged)
- Research branch: `research/final-experiment-report`, created from that commit
- `master` (`f9ab3b24b75171b9c51b013532c14b434a82b555`) does NOT contain the
  reliability work and was not used

## Artifact hashes (SHA256)

| Artifact | SHA256 |
|---|---|
| `data/test_sets/apollo_multihop_50.json` | `17a13db9b9a7c894af6b0cd869e18a9e6f6272f07eb8dce15be1f2d063521df0` |
| `data/test_sets/nhs_wannacry_multihop_50.json` | `babe0b6c75fa4f644b5fb155a36ebd945a116464e66304dec5b3da41adbbefdd` |
| `results/research/apollo_multihop_llama31_8b_20260727T203028Z.json` | `638a2718ae1e6bff149d96d0f8cfa1761eebfcfa6b38415155fcabcd7d327f46` |
| `results/research/apollo_multihop_llama31_8b_20260727T203028Z.md` | `a82927c33739454fdfa03ea1fbf0c3dcf85fb7a2b575fd9cc96dffde6346f983` |
| `.runtime/research/apollo_multihop_llama31_8b_20260727T203028Z.log` | `86596afc811e07f37c3ecdb3a77758bddbacd71c44676c2e83848c6c776c9a10` |
| `.runtime/debug/20260727T214622Z_nhs_wannacry_h10_q01_attempt_70a052a7.jsonl` | `a71d678c6abd1f6afcdfa1c064823c00a166c34541c8932925cb25efc9c1632a` |
| `.runtime/debug/20260727T190016Z_apollo_hop_046_attempt_7dbf3e1b.jsonl` (pre-fix) | `083e8480f6747f66023385e9882067d0308d1de1c8b86d4c0d8013b66d0bb240` |
| `.runtime/debug/20260727T202312Z_apollo_hop_046_attempt_91bb9b85.jsonl` (post-fix) | `e4c7ecd7d9a4ef5291d1a7b265a8a94da4791f50d30266369e9c13de6ecc1c2c` |

## Model and infrastructure configuration

- Model: `llama3.1:8b` via Ollama; `OLLAMA_NUM_CTX=8192`, `OLLAMA_NUM_PREDICT=4096`,
  `OLLAMA_TEMPERATURE=0`
- Neo4j: `neo4j:5.26.0` (Docker; `scripts/recreate-neo4j.sh`), `NEO4J_ENABLED=true`,
  `NEO4J_REQUIRED=true`, cleared between questions, execution-scoped storage,
  evaluation via Neo4j readback (all 50 rows)
- No secrets are recorded in this file or in the committed artifacts

## Commands

Official benchmark run (2026-07-27, preserved verbatim from shell history — do not
re-run without explicit approval; a new run is a new experimental sample):

```bash
( export NEO4J_ENABLED=true; export NEO4J_REQUIRED=true; export OLLAMA_NUM_CTX=8192; \
  export OLLAMA_NUM_PREDICT=4096; export OLLAMA_TEMPERATURE=0; \
  .venv/bin/python scripts/run_multihop_benchmark.py \
    --provider ollama --model llama3.1:8b --num-ctx 8192 --max-iterations 3 \
    --clear-neo4j --timeout-per-question 180 --continue-on-error \
    --cooldown-seconds 2 --max-consecutive-timeouts 3 \
    --output results/research/apollo_multihop_llama31_8b_20260727T203028Z.json \
    --summary results/research/apollo_multihop_llama31_8b_20260727T203028Z.md; \
  echo $? > .runtime/research/apollo_multihop_llama31_8b_20260727T203028Z.rc; ) \
  > .runtime/research/apollo_multihop_llama31_8b_20260727T203028Z.log 2>&1 &
```

Analysis (2026-08-02, this pass):

```bash
.venv/bin/python scripts/analyze_final_experiment.py
.venv/bin/python scripts/plot_final_experiment.py
```

Report generation (this pass):

```bash
.venv/bin/python scripts/build_experiment_report_docx.py
```

## Validation performed in this research pass

| Check | Command | Result |
|---|---|---|
| Full offline test suite on frozen-branch code | `.venv/bin/pytest tests/ -q` | `430 passed, 16 skipped` (2026-08-02). PR #5 reported `406 passed, 16 skipped` at freeze; the +24 come from the untracked prior-session file `tests/test_decomposed_backtracking_behavior_suite.py` present in the working tree. No failures. |
| Analysis-script unit tests | `.venv/bin/pytest tests/test_analyze_final_experiment.py -q` | `5 passed` |
| Aggregate cross-check | built into `analyze_final_experiment.py` (hard exit on drift) | recomputed aggregates exactly match the runner summary (50/50/0 errors, 27 exact, 43 contains, 33 resolved) |
| Live Apollo depth 1/2/3/10 acceptance after fix | evidenced by `.runtime/benchmarks/apollo_depth_acceptance*.{json,md}` (2026-07-27) | pre-existing artifacts; not re-run |
| Frontend lint/build | reported passing in PR #5 at freeze | not re-run (no frontend changes in this pass) |

## Known missing artifacts

See `research/EXPERIMENT_EVIDENCE_INVENTORY.md` §7: the two professor template DOCX
files and `Pasted text(44).txt` are absent from this environment; official-run
per-question debug traces were never persisted; GitHub PR metadata is not accessible
from this environment.

## Repeatability extension (2026-08-03 UTC)

Executed on branch `research/repeatability-study` at HEAD `3f01ea1` (created from
the report branch; inference-sensitive paths verified identical to `b9608d0` via
`git diff --exit-code b9608d0 -- src api prompts data/test_sets/apollo_multihop_50.json
scripts/run_multihop_benchmark.py scripts/recreate-neo4j.sh scripts/devctl.sh` —
clean before the study). Runs executed sequentially by a bounded wrapper
(command recorded per run in `.runtime/research/repeatability/*.cmd`); each run
used the exact original command shape and environment
(`NEO4J_ENABLED=true NEO4J_REQUIRED=true OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=4096 OLLAMA_TEMPERATURE=0`, flags `--provider ollama --model
llama3.1:8b --num-ctx 8192 --max-iterations 3 --clear-neo4j
--timeout-per-question 180 --continue-on-error --cooldown-seconds 2
--max-consecutive-timeouts 3`). Model digest `46e0c10c039e` (Ollama 0.32.5);
Neo4j 5.26.0 (same `grapheval-neo4j` container). No infrastructure failures
occurred; no run or question was repeated.

| Run | Artifact | Started (UTC) | Exit code | SHA256 |
|---|---|---|---|---|
| Run 2 | `results/research/repeatability/apollo_repeat_run2_llama31_8b_20260803T012414Z.json` | 2026-08-03T01:24:14Z | 0 | `896a8186ccfe525552a556ff55eac26d10fb10779e326e7b7e2792dfb7ae94ee` |
| Run 2 summary | `...apollo_repeat_run2_llama31_8b_20260803T012414Z.md` | — | — | `c2f36964e29bcd13b0a446b61d1a7777b3944ad7603bf5c5c7448176828089c2` |
| Run 3 | `results/research/repeatability/apollo_repeat_run3_llama31_8b_20260803T020637Z.json` | 2026-08-03T02:06:37Z | 0 | `03dbaa696aa8af7cf66fbe608a2c5300e1b06927a5b4cfbb1fc40b4002132c17` |
| Run 3 summary | `...apollo_repeat_run3_llama31_8b_20260803T020637Z.md` | — | — | `f2487a49ba7cb28767a4dc5a2ae09b8cd5a1838882bca32aa2a12d53e4942552` |

Both runs: `full_real`, `is_partial: false`, 50 selected / 50 attempted / 50
completed, 0 errors, validated immediately after completion (validation output in
`.runtime/research/repeatability/wrapper_state.txt`; logs and rc files in
`.runtime/research/repeatability/`). Run 1 remains the unmodified official file
(SHA256 re-verified identical before the study).

Analysis commands:

```bash
.venv/bin/python scripts/analyze_repeatability_experiment.py \
  results/research/apollo_multihop_llama31_8b_20260727T203028Z.json \
  results/research/repeatability/apollo_repeat_run2_llama31_8b_20260803T012414Z.json \
  results/research/repeatability/apollo_repeat_run3_llama31_8b_20260803T020637Z.json
.venv/bin/python scripts/plot_repeatability_experiment.py
```

Headline: all 50 questions byte-identical on every compared output dimension in
all three runs; only runtime varied (means 48.42 / 46.73 / 45.79 s).

## Run-class separation

- Official run: `apollo_multihop_llama31_8b_20260727T203028Z` (only quantitative sample)
- Pre-fix diagnostics: `apollo_hop_046__20260727T190016Z__0e37a955` and related
  master-era baselines under `results/` (2026-07-26)
- Post-fix diagnostics: `apollo_hop_046__20260727T202312Z__50843932`,
  `.runtime/benchmarks/apollo_depth_acceptance*`
- Qualitative case exports: `nhs_wannacry_h10_q01__20260727T214622Z__4adc0f88`
  (local JSONL trace; UI export absent)
