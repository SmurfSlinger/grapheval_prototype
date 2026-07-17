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
  --rerun-errors \
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

Task 1 re-verification passed, including the frontend build, 184 backend
tests, custom endpoint/UI controls, FACT readback, separate CLAIMS, and raw
trace availability.

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
question, and resumes safely. A real `gemma4:e2b` baseline is running with
honest metrics; cite the baseline report as complete only when it is marked
`full_real`.
