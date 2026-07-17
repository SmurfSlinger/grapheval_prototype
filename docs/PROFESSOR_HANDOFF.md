# Professor handoff

## What is ready

This branch continues the local custom-context Neo4j-backed GraphEval
workstream. Decomposed Backtracking supports custom trusted context and
compound questions: optional flawed initial answer, intentional local Neo4j
clear, trusted FACT persistence, base KGc readback from Neo4j, separate
evaluated CLAIM relationships, and both Research Trace and Advanced / Raw
Trace.

The branch also contains:

- a validated 50-question Apollo/NASA measurement set
- a second validated 50-question **NHS WannaCry** measurement set grounded in
  authoritative public sources (NAO, DHSC/NHS CIO lessons learned, CISA/US-CERT,
  Microsoft MS17-010)
- checkpointing/resumable benchmark runners and JSON/Markdown reports for both

See `docs/NHS_WANNACRY_BENCHMARK.md` for WannaCry source policy, graph metrics,
and commands.

## Exact local startup

```bash
cp .env.example .env
```

Use an installed Ollama tag. Template default is `gemma4:12b`. For the
verified cloud baseline tag:

```dotenv
DEFAULT_MODEL=gemma4:e2b
OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=4096
OLLAMA_REQUEST_TIMEOUT=600
```

Or pull the configured 12b tag:

```bash
ollama pull gemma4:12b
```

Start Ollama in one terminal:

```bash
ollama serve
```

Start Neo4j, FastAPI, and Next.js in another:

```bash
./scripts/check_local_models.sh
./scripts/start-dev.sh
```

Open `http://localhost:3000`.

If Ollama segfaults on load with `libggml-cpu-sapphirerapids.so` (some CPU
VMs advertise AMX incorrectly), move that library out of Ollama's `lib/ollama`
directory so it falls back to a compatible CPU backend, then restart
`ollama serve`.

## Run a custom context and question

1. Select **Decomposed Backtracking**.
2. Set **Input source** to **Custom local run**.
3. Enter an optional run label.
4. Paste the trusted context and compound question.
5. Optionally paste a flawed initial answer. Blank means GraphEval generates
   and projects Answer(0).
6. Leave **Clear Neo4j before run** selected for an isolated local graph.
7. Run and inspect Research Trace or Advanced / Raw Trace.

The clear option is visible and executes the approved full local clear:

```cypher
MATCH (n) DETACH DELETE n
```

## Inspect Neo4j

Open `http://localhost:7474` and use the credentials configured in `.env`.

```cypher
MATCH (s)-[r]->(o)
WHERE r.example_id = 'your-run-id'
RETURN s.name, type(r), r, o.name
```

Trusted context facts use `FACT`. Evaluated answer statements use `CLAIM`.
Generated answer claims are not promoted into trusted FACTS. Base custom FACTS
are read back from Neo4j before evaluation; focused and derived additions use
the provenance-aware in-memory working KGc and are persisted after a
successful run.

## Model and context tested

- Real baseline / smoke model: `gemma4:e2b`
- Context setting used for the cloud baseline: `OLLAMA_NUM_CTX=8192`
- Generation cap: `OLLAMA_NUM_PREDICT=4096` (prevents truncation of large
  context-triple JSON and unbounded multi-thousand-token replies)
- Provider disables thinking mode (`think: false`) so Gemma 4 returns final
  answer text through `/api/generate`
- Real hop-1 smoke: exact match and pipeline-resolved (~228s on CPU)
- Real baseline stopped at **15/50** (`partial_real`): contains-expected
  93.3%, exact-match 53.3%, pipeline-resolved 13/15. Resume from
  `results/apollo_multihop_real_baseline.json` with `--resume`.

Model quality and speed depend on local hardware.

## Benchmark

Dataset:

```text
data/test_sets/apollo_multihop_50.json
```

Validate without an LLM:

```bash
python scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/apollo_multihop_50.json \
  --validate-only
```

Run or resume the complete real benchmark:

```bash
python scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/apollo_multihop_50.json \
  --provider ollama \
  --model gemma4:e2b \
  --num-ctx 8192 \
  --clear-neo4j \
  --timeout-per-question 1200 \
  --continue-on-error \
  --resume \
  --retry-errors \
  --output results/apollo_multihop_real_baseline.json \
  --summary results/apollo_multihop_real_baseline.md
```

The runner writes a checkpoint after every question. Use `--ids` for selected
questions or `--start-at` with `--resume` to continue while keeping earlier
rows. `--prompt-profile compact` is accepted for experiment labeling but
currently uses the unchanged, validated prompts.

Reports:

- `results/apollo_multihop_report.json` — mock plumbing only
- `results/apollo_multihop_real_smoke.json` — single real hop-1 smoke
- `results/apollo_multihop_real_baseline.json` — real baseline (cite as full
  only when `run_type` is `full_real`)

## Benchmark interpretation

The report keeps deterministic pipeline resolution separate from textual
answer matching:

- `resolved_by_pipeline` comes from pipeline stop reasons.
- `exact_match` compares stripped answer text.
- `contains_expected_answer` checks normalized expected text within the final
  answer.
- An unresolved answer can still contain the expected entity; the runner
  records that category without overriding pipeline labels.

Expected answers are used only after inference for scoring. They are not
passed into prompts or the comparator.

## Verification

```bash
cd frontend && npm run build
cd ..
pytest tests/
```

Task 1 re-verification passed, including the frontend build, 255 backend
tests, custom endpoint/UI controls, FACT readback, separate CLAIMS, raw
trace availability, Apollo benchmark tests, and NHS WannaCry provenance /
hop-semantics / wrapper tests.

---

## Task 1 — Local custom Neo4j workflow

**Status: READY**

Evidence (verified on this branch):
- Frontend `npm run build` passes.
- `pytest tests/` passes (**255 tests**).
- Custom route tests in `tests/test_local_neo4j_custom_run.py`.
- FACT persistence and readback tested.
- CLAIM separation tested.
- Clear-before-run flag propagation tested.
- Research Trace and Advanced / Raw Trace available in the UI.
- `OLLAMA_NUM_CTX` propagates through the provider to the request payload.
- `scripts/start-dev.sh` sources `.env` and starts Neo4j, backend, and
  frontend.

Remaining local acceptance (requires a machine with Ollama + Neo4j):
- Live Ollama + Neo4j smoke using a real model (cannot be verified in this
  cloud environment).

---

## Task 2 — Apollo multi-hop benchmark

**Repository implementation status: READY**

**Real local baseline status: PARTIAL**
(15 questions completed on an earlier local run; full 50-question baseline
still requires running `./scripts/run_apollo_real_baseline.sh` where Ollama
and Neo4j are available.)

Evidence (re-verified on this commit):
- Dataset validation: `--validate-only` exits 0 (50 questions; 5 per hop
  count for hops 1–10).
- Full mock plumbing run (`--provider mock --continue-on-error`): **50
  terminal `error` records**, **0 successful completions**, **50 projection
  failures**. This is **not** a successful accuracy result; it confirms
  runner plumbing (unique IDs, hop distribution, checkpoint/summary writers,
  separate answer-match vs pipeline-resolution fields, populated
  `attempt_number` / `resumed`). No lock or benchmark process remained
  afterward.
- Process locking: `BenchmarkLock` uses exclusive file creation (`O_CREAT|O_EXCL`)
  and refuses to overwrite malformed/unreadable lock files.
- All new runner flags functional: `--retry-errors`, `--rerun-completed`,
  `--cooldown-seconds`, `--max-consecutive-timeouts`, `--stop-after-minutes`,
  `--lock-file`.
- Terminal states tracked: `completed`, `timeout`, `error`, `interrupted`.
- Result schema includes: `terminal_state`, `error_type`, `error_message`,
  `attempt_number`, `resumed` (persisted across resume/retry attempts).
- `scripts/run_apollo_real_baseline.sh` resolves the effective model **before**
  Ollama checks and uses that same model for the runner. Precedence:
  1) CLI `--model VALUE` / `--model=VALUE`, 2) pre-existing `MODEL` env var,
  3) `MODEL` from `.env` only when unset, 4) default `gemma4:e2b`. Exact
  Ollama tag match is required (`gemma4:latest` does not satisfy `gemma4:e2b`).
- Canonical real-baseline checkpoint paths (wrapper + docs agree; resume
  depends on these exact files):
  - `results/apollo_multihop_real_baseline.json`
  - `results/apollo_multihop_real_baseline.md`
- Wrapper protected args (rejected): `--provider`, `--test-set`, `--output`,
  `--summary`. Safe forwardable tuning includes `--limit`, `--ids`,
  `--start-at`, `--stop-after-minutes`, `--retry-errors`, `--rerun-completed`,
  and timeout/cooldown/`--num-ctx` controls. `--model` is resolved by the
  wrapper and not duplicated in forward-args.
- Real baseline command (local machine with Ollama + Neo4j):
  `./scripts/run_apollo_real_baseline.sh`
  or with an explicit model: `./scripts/run_apollo_real_baseline.sh --model llama3:8b`
- Real baseline artifact: `results/apollo_multihop_real_baseline.json`
  (partial; cite as complete only when `run_type=full_real`). This pass did
  **not** re-run the full real Ollama baseline.

A COMPLETE real baseline requires terminal records for all 50 questions
(completed, timeout, or error). Accuracy is not the readiness criterion;
reliable measurement is.

---

## Task 3 — NHS WannaCry multi-hop benchmark

**Repository implementation status: READY**

**Real local baseline status: NOT RUN IN THIS ENVIRONMENT**
(Ollama is not reachable here; Neo4j/Ollama real execution must be done on a
machine with those services. Leave PR draft until that run completes.)

Evidence (verified on this commit):
- Dataset: `data/test_sets/nhs_wannacry_multihop_50.json`
- Source manifest: `data/sources/nhs_wannacry/source_manifest.json`
- Authoritative sources: NAO HC 414; DHSC/NHS CIO lessons learned; CISA
  TA17-132A; Microsoft MS17-010
- Hop semantics: declared hop count equals **minimum required directed path
  length** from `reasoning_anchor_entities` to the answer; audit artifacts at
  `data/test_sets/nhs_wannacry_multihop_50.audit.json` and
  `docs/NHS_WANNACRY_HOP_AUDIT.md` report **0 unresolved shortcuts** (15
  shortcuts were present before redesign)
- `--validate-only` exits 0 for NHS WannaCry (structural + shortcut checks)
- Apollo `--validate-only` still exits 0 (no regression)
- Mock plumbing: 50 terminal `error` records, 0 completions, 50 projection
  failures (plumbing only; not accuracy evidence)
- Wrapper: `./scripts/run_nhs_wannacry_real_baseline.sh`
- Canonical outputs:
  - `results/nhs_wannacry_multihop_real_baseline.json`
  - `results/nhs_wannacry_multihop_real_baseline.md`
- Backend tests: **255 passed**
- Frontend `npm run build` passes
- Real Ollama baseline: **not run** in this environment (Ollama unavailable).
  Do not start the expensive real run unless shortcut audit remains green.

Exact Fedora/local command when Ollama + Neo4j are available:

```bash
./scripts/run_nhs_wannacry_real_baseline.sh
```

---

## Known limitations

- `gemma4:12b` may not be installed; select `gemma4:e2b` or pull 12b.
- Prompt token telemetry is approximate and the provider boundary does not yet
  attach a stage name.
- The comparator receives Python `KgcFact` objects reconstructed from Neo4j;
  it does not issue Cypher per comparison.
- Focused/derived additions are evaluated from the in-memory working mirror
  and persisted after success.
- Entity nodes are globally named, so safe isolation currently uses a full
  local-database clear rather than scope-only deletion.
- A full 50-question real-model benchmark on CPU is lengthy (~4 minutes per
  early hop observed). Partial checkpoints must not be described as full
  benchmark performance until `run_type=full_real`.
- Per-question timeouts use in-process `SIGALRM` / `ITIMER_REAL`. The runner
  does not spawn a child process per question, so there is no process group to
  kill/reap on timeout. A timed-out HTTP call raises `TimeoutError` in the
  runner process; work already accepted by the Ollama *server* may continue
  until that server request ends. A separate helper
  (`run_subprocess_with_timeout`) terminates and reaps owned child process
  groups when a subprocess architecture is used.

## Next recommended work

Let the resumable real baseline finish, inspect hop groups where pipeline
resolution or textual matching degrades, and investigate general
target/schema failures. Do not tune against expected answers or alter
deterministic labels merely to raise benchmark scores.

## Spoken update

I finished the local custom-context Neo4j-backed workflow and hardened the
Apollo multi-hop measurement path, then added a second source-grounded
benchmark for the NHS WannaCry incident. Backend tests: 246 passed.
Frontend production build passes. Apollo and NHS WannaCry datasets both
validate. NHS mock plumbing yields 50 terminal failure records and is not
accuracy evidence. Real Ollama baselines were not rerun here because Ollama
is unavailable in this environment; the NHS real wrapper is ready for a
local machine with Ollama and Neo4j.