# Overnight progress report

## Task 1 status — local Neo4j custom runs

**Branch:** `feature/local-neo4j-custom-runs`

**Professor testing status: READY**

The professor can paste trusted context and a compound question, optionally
provide a flawed initial answer, clear the local Neo4j database, create and
persist a trusted KGc, run decomposed backtracking from Neo4j-read base facts,
and inspect Research Trace plus Advanced / Raw Trace.

### Task 1 re-verification: READY

Re-verified on `feature/local-neo4j-custom-runs`:

- `npm run build`: passed.
- `pytest tests/`: 178 passed.
- `timeout 15s ./scripts/check_local_models.sh`: completed; Ollama 0.30.6
  reported `gemma4:e2b` and `gemma4:latest`, while the configured
  `gemma4:12b` tag remains uninstalled.
- Custom decomposed API, optional initial answer, visible Neo4j clear control,
  custom trusted context/question fields, FACT persistence/readback, separate
  CLAIM relationships, and Advanced / Raw Trace are present.
- `docs/LOCAL_NEO4J_RUN.md` still documents that the custom base KGc is read
  back from Neo4j and later focused/derived additions use the in-memory
  working mirror before persistence.

### Completed phases

- Phase 0: storage/API/frontend flow audited in
  `docs/LOCAL_NEO4J_RUN.md`.
- Phase 1: environment-based model/context configuration, bounded local model
  audit, Ollama `num_ctx`, and lightweight call-size telemetry.
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
git switch feature/local-neo4j-custom-runs
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

- Ollama version observed: `0.30.6`.
- Locally visible tags: `gemma4:e2b`, `gemma4:latest`.
- Configured/template target: `gemma4:12b`; this tag was **not** installed
  locally. Pull it first or set `DEFAULT_MODEL=gemma4:e2b`.
- Real smoke model: `gemma4:e2b`.
- Real smoke context setting: `OLLAMA_NUM_CTX=32768`.
- No claim is made that a non-quantized/full-precision Gemma 4 tag is
  available.

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

- Baseline frontend build before edits: passed.
- Baseline backend suite before edits: 175 passed.
- Final frontend production build: passed.
- Final backend suite after Task 2: 178 passed.
- Targeted synthetic custom test: passed; expected `Rack R7`.
- Live Neo4j mock smoke: 5 FACTS, 10 separate CLAIMS,
  `kgc_evaluation_source=neo4j_readback`, clear recorded.
- Real Ollama + Neo4j synthetic smoke: completed in 94.6 seconds with
  `gemma4:e2b`, 32768 context, 4 base FACTS, 12 traced calls, and combined
  answer containing `Rack R7`.
- Apollo, Patient D-314, and stable Saturn behavior are covered by the passing
  regression suite. No repeated real-model demo acceptance was run.

### Known limitations

- The locally installed model is `gemma4:e2b`, not the configured
  `gemma4:12b`; the professor must pull 12b or select an installed tag.
- The real synthetic smoke gave the correct combined result but repeated
  `Rack R7` as over-broad intermediate sub-answers.
- Prompt token counts are approximate (`characters / 4`) and successful-call
  telemetry does not yet identify the pipeline stage.
- Base custom facts are read back from Neo4j; later focused/derived facts use
  the in-memory mirror before being persisted.
- Entity nodes are shared, so scope-only clearing is not safe in the current
  schema; the visible option clears the full local database.

## Task 2 status — Apollo multi-hop benchmark

**Status: scaffold and first measurement set complete.**

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
- Full scaffold report:
  `results/apollo_multihop_report.json` and
  `results/apollo_multihop_summary.md`.
- The full report used the deterministic mock. All 50 failed at projection
  because the mock has no profile for the new context. This validates report
  plumbing only and is explicitly not presented as model accuracy.
- A one-question real runner smoke used `gemma4:e2b`, Neo4j clear/readback, and
  32768 context. It returned the grounded sentence “Apollo 11 was crewed by
  Neil Armstrong,” which passed normalized answer matching. The pipeline
  still marked the sub-question unresolved despite one supported final claim;
  both signals are retained in
  `results/apollo_multihop_real_smoke.json`.
- A full 50-question real-model run was not attempted because the observed
  one-question runtime was about 61 seconds; extrapolation would exceed the
  bounded overnight check budget.

Run the full measurement when time permits:

```bash
set -a; source .env; set +a
python scripts/run_multihop_benchmark.py \
  --provider ollama \
  --model gemma4:12b \
  --clear-neo4j-between-runs
```

Use `gemma4:e2b` instead if 12b has not been installed. The runner does not
tune the pipeline to make the 50 questions pass.

## What to tell the professor tomorrow

Use the feature branch, select an installed Ollama model (or pull
`gemma4:12b`), keep the clear checkbox enabled for isolated runs, and inspect
both Research Trace and Neo4j Browser. The custom base KGc is genuinely read
back from Neo4j; later focused/derived additions are an in-memory mirror that
is persisted after success. The benchmark is ready as a measurement tool, but
its full real-model baseline remains to be run; the existing mock report is
not an accuracy result.
