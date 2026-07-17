# Local Neo4j custom runs

## Current storage flow

The decomposed path is `POST /run-decomposed-kgc-backtracking` for built-in
examples and `POST /run-decomposed-kgc-backtracking-custom` for custom runs.
`DecomposedBacktrackingRunner` in
`src/pipeline/decomposed_backtracking_runner.py` orchestrates question
decomposition, context extraction, per-sub-question comparison/revision, and
answer combination.

- `ContextTripleExtractor.extract_with_trace()` creates the base KGc from the
  trusted context.
- `WorkingKgcState` keeps the run's base, focused, and deterministically
  derived trusted facts in memory. Generated answer claims are candidate
  records only and are not promoted into the KGc.
- `Neo4jStore` in `src/storage/neo4j_store.py` writes trusted facts as `FACT`
  relationships and evaluated answer claims as separate `CLAIM`
  relationships.
- Built-in decomposed runs compare against the in-memory KGc and use Neo4j for
  persistence/visualization when enabled.
- Custom decomposed runs strictly write base `FACTS`, read those scoped facts
  back from Neo4j, and initialize the comparator's working KGc from that
  readback. Focused and derived facts added later are used from the in-memory
  working KGc and persisted at the end of a successful run.
- `GraphComparator.compare_claims()` receives a Python list of `KgcFact`
  objects. It never queries Neo4j itself. Neo4j therefore affects custom-run
  evaluation through the initial readback, not through per-comparison queries.
- Scope is stored as `example_id` on `FACT` and `CLAIM` relationships. The
  custom `run_id` is used as `example_id`. Entity nodes are shared and are not
  run-scoped.
- Base facts use `provenance=trusted_context` and
  `extraction_stage=context_triple_extraction`. Focused facts retain trusted
  provenance plus `sub_question_id` and their focused extraction stage.
  Derived facts use `provenance=derived_from_trusted_context` plus derivation
  type, evidence spans, explanation, and sub-question ID.
- Claims use `CLAIM`, never `FACT`, and include label, reason, evidence,
  answer stage, iteration, and run/example ID.
- `Neo4jStore.get_kgc_facts(example_id)` reconstructs scoped facts. There is no
  public HTTP graph-reconstruction route.
- Because entity nodes are shared across runs, the safe implemented clear is a
  full local-database clear: `MATCH (n) DETACH DELETE n`. It only runs when the
  visible custom-run checkbox is enabled.

Frontend entry points are `frontend/app/page.tsx`,
`frontend/components/ControlsPanel.tsx`, and
`frontend/components/DecomposedKgcFlowView.tsx`. API request types live in
`frontend/lib/api.ts`; backend routes live in `api/server.py`. Research Trace
and Advanced / Raw Trace remain available in the decomposed result view.

Context extraction uses `src/pipeline/context_triple_extractor.py`; answer
claim extraction uses `src/pipeline/triple_extractor.py`; deterministic labels
come from `src/pipeline/graph_comparator.py`; the revision loop is in
`src/pipeline/kgc_iteration.py`. UI mode `decomposed_kgc` maps to
“Decomposed Backtracking.”

## Model and context length

Copy the environment template, then inspect what is actually available:

```bash
cp .env.example .env
./scripts/check_local_models.sh
```

The audit reports the Ollama version, installed tags, Gemma 4-related tags,
`DEFAULT_MODEL`, `OLLAMA_BASE_URL`, and `OLLAMA_NUM_CTX`. It does not infer
that an unlisted full-precision model exists.

Configure `.env`:

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
DEFAULT_MODEL=gemma4:12b
OLLAMA_NUM_CTX=32768
OLLAMA_NUM_PREDICT=4096
OLLAMA_REQUEST_TIMEOUT=600
```

`OLLAMA_NUM_PREDICT` caps generation length so large context-triple JSON is not
truncated mid-object and so replies cannot run unbounded. The Ollama provider
also sends `think: false` so thinking-capable tags such as Gemma 4 return
final answer text through `/api/generate`.

Install a locally available tag only when needed:

```bash
ollama serve
ollama pull gemma4:12b
ollama show gemma4:12b
```

`OLLAMA_NUM_CTX`, when set, is sent to `/api/generate` as
`options.num_ctx`. Successful calls record model, configured context,
prompt characters, an approximate `characters / 4` token count, response
characters, and retry count in the raw trace. Stage names are not currently
attached at the provider boundary.

Recommended progression:

1. `gemma4:12b` with a moderate context.
2. `gemma4:12b` with a larger context such as 32768.
3. A larger Gemma model only if local memory and latency are acceptable.

A larger context reduces cutoff risk but is slower and consumes more memory.
Quantization and full-precision availability depend entirely on locally
installed Ollama tags.

## Professor run instructions

1. Check out the feature branch:

   ```bash
   git switch feature/local-neo4j-custom-runs
   ```

2. Install dependencies if they are not already present:

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   cd frontend
   npm install
   cd ..
   ```

3. Create `.env` and select the installed model:

   ```bash
   cp .env.example .env
   ./scripts/check_local_models.sh
   ```

4. Start Ollama in a separate terminal:

   ```bash
   ollama serve
   ```

5. Start Neo4j, backend, and frontend:

   ```bash
   ./scripts/start-dev.sh
   ```

   This repository does not contain a Docker Compose file. The script starts
   or creates the `grapheval-neo4j` container, loads `.env`, and starts
   FastAPI and Next.js.

   Manual alternatives are:

   ```bash
   docker start grapheval-neo4j
   set -a; source .env; set +a
   .venv/bin/python -m uvicorn api.server:app --reload --port 8000
   cd frontend && npm run dev
   ```

6. Open `http://localhost:3000` (or the alternate port printed by Next.js).
7. Select **Decomposed Backtracking**.
8. Set **Input source** to **Custom local run**.
9. Paste trusted context and a compound question.
10. Optionally paste a flawed initial answer and enter a run label.
11. Leave **Clear Neo4j before run** checked for an isolated local graph.
12. Run. The Research Trace shows the run ID, readback mode, clear status,
    and persisted FACT count. Advanced / Raw Trace shows full metadata.
13. Open `http://localhost:7474` and sign in with the configured Neo4j
    credentials. Inspect:

    ```cypher
    MATCH (s)-[r]->(o)
    RETURN s, r, o
    ```

    To inspect one run:

    ```cypher
    MATCH (s)-[r]->(o)
    WHERE r.example_id = 'your-run-id'
    RETURN s.name, type(r), r, o.name
    ```

14. Change the context/run ID and rerun. Keeping clear enabled removes the
    prior local graph first.

Manual full clear:

```cypher
MATCH (n) DETACH DELETE n
```

## Custom smoke test

Trusted context:

> Test System Alpha uses Service A. Service A depends on Database B. Database
> B runs on Host C. Host C is located in Rack R7.

Question:

> Which rack contains the host that runs the database depended on by the
> service used by Test System Alpha?

Expected answer: `Rack R7`.

Run this through the custom UI with Ollama. Then inspect the `FACT` path and
Research Trace. This fixture is documentation/test input only; its answer is
not encoded in pipeline logic.

## Verification commands

```bash
cd frontend && npm run build
cd ..
pytest tests/
```

## Multi-hop benchmark reports

Validate the fixed Apollo/NASA set without calling an LLM:

```bash
python scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/apollo_multihop_50.json \
  --validate-only
```

Run the full real benchmark using the convenience wrapper (recommended):

```bash
./scripts/run_apollo_real_baseline.sh
# or choose a model explicitly:
./scripts/run_apollo_real_baseline.sh --model llama3:8b
```

Model selection precedence in the wrapper (highest to lowest):

1. CLI `--model VALUE` or `--model=VALUE`
2. Pre-existing environment variable `MODEL`
3. `MODEL` from `.env` (applied only when `MODEL` was not already set)
4. Default `gemma4:e2b`

The wrapper resolves that effective model **before** checking Ollama, then
passes the same model to `run_multihop_benchmark.py`. It verifies Ollama is
reachable, confirms the requested model tag is installed with an **exact**
match (for example `gemma4:latest` does not satisfy `gemma4:e2b`), validates
the dataset, and runs the benchmark with safe defaults. It does NOT download
any model automatically. If the model is missing it prints the exact
`ollama pull` command and exits.

Note: a mock-provider 50-question run tests runner plumbing only. Fifty
terminal failure records with zero completions are **not** evidence of answer
accuracy.

Or run the Python runner directly with full control:

```bash
python scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/apollo_multihop_50.json \
  --provider ollama \
  --model gemma4:e2b \
  --num-ctx 32768 \
  --clear-neo4j \
  --timeout-per-question 300 \
  --continue-on-error \
  --resume \
  --cooldown-seconds 3 \
  --max-consecutive-timeouts 5 \
  --output results/apollo_multihop_real_report.json \
  --summary results/apollo_multihop_real_summary.md
```

Key flags:

| Flag | Purpose |
|------|---------|
| `--resume` | Skip completed questions; resume after interruption |
| `--retry-errors` | With `--resume`, re-run previously errored questions |
| `--rerun-completed` | With `--resume`, re-run all questions including completed ones |
| `--cooldown-seconds N` | Sleep N seconds between questions (reduces contention) |
| `--max-consecutive-timeouts N` | Stop cleanly after N consecutive timeouts |
| `--stop-after-minutes M` | Stop the run after M wall-clock minutes |
| `--lock-file PATH` | Override the lock file path (default: `.runtime/benchmark.lock`) |
| `--ids Q1,Q2` | Run only these question IDs |
| `--start-at Q_ID` | Start from this ID after other filters |
| `--limit N` | Run at most N questions |
| `--validate-only` | Validate dataset structure without running the LLM |

**Process locking**: the runner acquires an exclusive lock at startup to
prevent two concurrent runs from interleaving writes. A second run will refuse
to start if the lock owner is still alive. Stale locks from crashed runs are
cleaned up automatically.

Reports are written to `results/` and checkpointed after every question.
Mock reports test runner plumbing only and are not model-accuracy evidence.

## What is safe for professor to try

This branch lets you paste a trusted context and compound question, clear
Neo4j, generate a KGc from the context, persist it to Neo4j, run decomposed
backtracking, and inspect both the trace and graph.

## Known limitations

- Custom runs require `NEO4J_ENABLED=true` and a reachable Neo4j instance;
  persistence/readback failures are reported and stop the run.
- The comparator consumes Python `KgcFact` objects. Custom base facts are
  reconstructed from Neo4j first; focused/derived additions then use the
  in-memory working mirror and are persisted after a successful run.
- Built-in examples retain their prior in-memory evaluation behavior.
- Prompt telemetry is approximate and successful-call-only; it has no exact
  tokenizer and no per-stage label yet.
- No real Ollama smoke result should be inferred from mock-provider checks.
- Model quality, runtime, and maximum practical context depend on local
  hardware and installed Ollama tags.
- Benchmark per-question timeouts use in-process `SIGALRM`. The runner does
  not spawn a child process per question, so timeout cannot kill/reap a
  process group for that path. Owned-child helpers terminate process groups
  when a subprocess architecture is used.
