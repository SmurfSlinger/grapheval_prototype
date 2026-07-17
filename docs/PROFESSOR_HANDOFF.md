# Professor handoff

## What is ready

This branch continues the local custom-context Neo4j-backed GraphEval
workstream. Decomposed Backtracking supports custom trusted context and
compound questions: optional flawed initial answer, intentional local Neo4j
clear, trusted FACT persistence, base KGc readback from Neo4j, separate
evaluated CLAIM relationships, and both Research Trace and Advanced / Raw
Trace.

The branch also contains a validated 50-question Apollo/NASA measurement set
with five questions at each designed path length from 1 through 10, plus a
checkpointing/resumable benchmark runner and JSON/Markdown reports.

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

Task 1 re-verification passed, including the frontend build, 205 backend
tests (up from 184), custom endpoint/UI controls, FACT readback, separate
CLAIMS, raw trace availability, and the new benchmark runner tests.

---

## Task 1 — Local custom Neo4j workflow

**Status: READY**

Evidence:
- Frontend `npm run build` passes.
- `pytest tests/` passes (205 tests).
- Custom route tests in `tests/test_local_neo4j_custom_run.py`.
- FACT persistence and readback tested.
- CLAIM separation tested.
- Clear-before-run flag propagation tested.
- Research Trace and Advanced / Raw Trace available in the UI.
- `OLLAMA_NUM_CTX` propagates through the provider to the request payload.
- `scripts/start-dev.sh` sources `.env` and starts Neo4j, backend, and
  frontend.

Remaining local acceptance (requires user's Fedora machine):
- Live Ollama + Neo4j smoke using a real model (cannot be verified in the
  GitHub cloud environment).

---

## Task 2 — Apollo multi-hop benchmark

**Repository implementation status: READY**

**Real local baseline status: PARTIAL**
(15 questions completed on the user's local machine; full 50-question
baseline still requires running `./scripts/run_apollo_real_baseline.sh` on
the user's home machine.)

Evidence:
- 50 questions validated: 5 per hop count, 1–10.
- `--validate-only` exits 0.
- Full mock run: 50 terminal plumbing records, **0 successful completions**,
  **50 projection failures**. Records are unique, hop distribution is correct,
  JSON parses, and Markdown totals match. This validates runner plumbing only.
- Process locking: `BenchmarkLock` uses exclusive file creation (`O_CREAT|O_EXCL`)
  and refuses to overwrite malformed/unreadable lock files.
- All new runner flags functional: `--retry-errors`, `--rerun-completed`,
  `--cooldown-seconds`, `--max-consecutive-timeouts`, `--stop-after-minutes`,
  `--lock-file`.
- Terminal states tracked: `completed`, `timeout`, `error`, `interrupted`.
- Result schema includes: `terminal_state`, `error_type`, `error_message`,
  `attempt_number`, `resumed` (persisted across resume/retry attempts).
- `scripts/run_apollo_real_baseline.sh` requires an **exact** Ollama model-tag
  match (for example `gemma4:latest` does not satisfy `gemma4:e2b`).
- Real baseline: `results/apollo_multihop_real_baseline.json` (partial; cite
  as complete only when `run_type=full_real`). This cloud corrective pass did
  **not** re-run the real local Ollama baseline.

A COMPLETE real baseline requires terminal records for all 50 questions
(completed, timeout, or error). Accuracy is not the readiness criterion;
reliable measurement is.

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
Apollo multi-hop measurement path. Custom runs can clear Neo4j, extract a
graph from pasted context, persist trusted FACTS, keep answer CLAIMS
separate, and evaluate from Neo4j-read base facts. The 50-question benchmark
validates cleanly, reports match and resolve separately, checkpoints every
question, and resumes safely. The mock plumbing run yields 50 terminal
records with 0 successful completions and 50 projection failures. A partial
real baseline checkpoint exists from an earlier local run; this pass did not
re-run the real Ollama baseline.