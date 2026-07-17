# Overnight progress report

## Task 1 status — local Neo4j custom runs

**Branch:** `cursor/cloud-agent-1784294800421-ztfpf`
(continues the `feature/local-neo4j-custom-runs` workstream)

**Professor testing status: READY**

The professor can paste trusted context and a compound question, optionally
provide a flawed initial answer, clear the local Neo4j database, create and
persist a trusted KGc, run decomposed backtracking from Neo4j-read base facts,
and inspect Research Trace plus Advanced / Raw Trace.

### Task 1 re-verification: READY

Re-verified on this branch:

- `npm run build`: passed.
- `pytest tests/`: 184 passed.
- Custom decomposed API, optional initial answer, visible Neo4j clear control,
  custom trusted context/question fields, FACT persistence/readback, separate
  CLAIM relationships, and Advanced / Raw Trace are present.
- `docs/LOCAL_NEO4J_RUN.md` documents that the custom base KGc is read back from
  Neo4j and later focused/derived additions use the in-memory working mirror
  before persistence.
- Ollama provider now disables thinking mode (`think: false`) so Gemma 4 returns
  usable final text, and supports `OLLAMA_NUM_PREDICT` so large structured
  extractions are not truncated or left unbounded.

### Completed phases

- Phase 0: storage/API/frontend flow audited in
  `docs/LOCAL_NEO4J_RUN.md`.
- Phase 1: environment-based model/context configuration, bounded local model
  audit, Ollama `num_ctx`, generation cap, and lightweight call-size telemetry.
- Phase 2: custom decomposed input UI and API with optional run ID and initial
  answer.
- Phase 3: visible, opt-in full local Neo4j clear with trace metadata.
- Phase 4: scoped trusted FACT persistence/readback, focused/derived FACT
  provenance, and separate evaluated CLAIM persistence.
- Phase 5: synthetic custom-run test and live Neo4j/custom smoke.
- Phase 6: exact professor instructions and Browser queries.
- Phase 7: frontend and full backend regressions.

### Exact local commands

```bash
cp .env.example .env
./scripts/check_local_models.sh
ollama serve
./scripts/start-dev.sh
```

Open `http://localhost:3000`, select **Decomposed Backtracking**, choose
**Custom local run**, paste the inputs, and run. Full setup and manual startup
commands are in `docs/LOCAL_NEO4J_RUN.md`.

Verification:

```bash
cd frontend && npm run build
cd ..
pytest tests/
```

### Model and context

- Cloud baseline model: `gemma4:e2b` (Q4_K_M, ~7.2 GB).
- Configured/template target remains `gemma4:12b` in `.env.example`; pull it or
  set `DEFAULT_MODEL` to an installed tag.
- Real baseline settings used here: `OLLAMA_NUM_CTX=8192`,
  `OLLAMA_NUM_PREDICT=4096`, `OLLAMA_REQUEST_TIMEOUT=600`.
- On some CPU VMs, Ollama 0.32 may load
  `libggml-cpu-sapphirerapids.so` and segfault. Moving that library aside so
  Ollama falls back to a compatible CPU backend is a host workaround, not a
  GraphEval code change.

### KGc creation, storage, and use

- Base KGc creation:
  `ContextTripleExtractor.extract_with_trace()` from trusted context.
- Base storage:
  `Neo4jStore.store_kgc_facts()` as scoped `FACT` relationships.
- Custom evaluation:
  `Neo4jStore.get_kgc_facts(run_id)` reconstructs the base facts; those Python
  `KgcFact` objects initialize `WorkingKgcState`.
- Comparator:
  reads the Python working KGc. It does not execute Cypher itself. Focused and
  derived additions are used in the in-memory working mirror and persisted
  after a successful run.
- Claims:
  answer claims are written only as `CLAIM` relationships with stage,
  iteration, deterministic label, reason, and evidence. They are not promoted
  into trusted FACTS.

### Clear and inspect

The custom checkbox **Clear Neo4j before run** is enabled by default and
executes a full local clear because entity nodes are shared:

```cypher
MATCH (n) DETACH DELETE n
```

Inspect at `http://localhost:7474`:

```cypher
MATCH (s)-[r]->(o)
WHERE r.example_id = 'your-run-id'
RETURN s.name, type(r), r, o.name
```

### Results actually observed

- Frontend production build: passed.
- Backend suite: 184 passed.
- Targeted synthetic custom test coverage remains in the suite.
- Real Ollama + Neo4j Apollo hop-1 smoke (`gemma4:e2b`): exact match and
  pipeline-resolved in ~228s with Neo4j clear/readback.

### Known limitations

- The configured template model is `gemma4:12b`; use an installed tag if 12b is
  not pulled.
- Prompt token counts are approximate (`characters / 4`) and successful-call
  telemetry does not yet identify the pipeline stage.
- Base custom facts are read back from Neo4j; later focused/derived facts use
  the in-memory mirror before being persisted.
- Entity nodes are shared, so scope-only clearing is not safe in the current
  schema; the visible option clears the full local database.

## Task 2 status — Apollo multi-hop benchmark

**Status: measurement infrastructure READY; real-model baseline IN PROGRESS.**

- `data/test_sets/apollo_multihop_50.json` contains one shared trusted
  context, 50 questions, five questions for each hop count 1 through 10,
  explicit contiguous expected paths, answers, entities, relations, and
  difficulty flags.
- Validated graph metrics: 42 nodes, 48 unique edges, one connected
  component, root `Apollo 11`, root branching factor 5, maximum designed depth
  10, and average expected path length 5.5.
- `scripts/run_multihop_benchmark.py` records normalized answer match,
  resolved state, deterministic final labels, iterations, retries, focused
  extraction, derived facts, failure reason, graph difficulty, model/context,
  and available prompt telemetry.
- Resumable execution: `--resume` loads prior checkpoint rows from `--output`,
  skips completed IDs, optionally `--rerun-errors`, and with `--start-at`
  keeps earlier checkpointed rows in the report.
- Full mock plumbing report:
  `results/apollo_multihop_report.json` /
  `results/apollo_multihop_mock_summary.md` — 50/50 projection failures on the
  deterministic mock (no Apollo profile). Plumbing only, not accuracy.
- Real smoke:
  `results/apollo_multihop_real_smoke.json` — hop-1 question exact match +
  pipeline resolved with `gemma4:e2b`, Neo4j clear/readback.
- Real baseline checkpoint (stopped):
  `results/apollo_multihop_real_baseline.json` /
  `results/apollo_multihop_real_baseline.md` — **partial_real**, 15/50
  questions completed with `gemma4:e2b`, Neo4j clear/readback, resumable
  checkpoints. Observed on the stopped run: contains-expected 93.3%,
  exact-match 53.3%, pipeline-resolved 13/15. This is **not** a full
  50-question baseline (`run_type` remains `partial_real`). Resume with the
  command below when ready.

Run or resume the full measurement:

```bash
set -a; source .env; set +a
python scripts/run_multihop_benchmark.py \
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

The runner does not tune the pipeline to make the 50 questions pass. Expected
answers are used only for post-hoc scoring.

## What to tell the professor tomorrow

Use this branch (or the equivalent local feature branch), select an installed
Ollama model (or pull `gemma4:12b`), keep the clear checkbox enabled for
isolated runs, and inspect both Research Trace and Neo4j Browser. The custom
base KGc is genuinely read back from Neo4j; later focused/derived additions
are an in-memory mirror that is persisted after success. The benchmark dataset,
runner, scoring separation, and mock plumbing report are ready. The real-model
baseline was intentionally stopped at 15/50 (`partial_real`); resume from the
checkpoint before citing full-benchmark numbers.
