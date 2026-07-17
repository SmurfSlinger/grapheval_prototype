# Professor handoff

## What is ready

`feature/local-neo4j-custom-runs` supports local custom trusted context and
compound-question runs through Decomposed Backtracking. A custom run can
optionally start from a flawed answer, intentionally clear the local Neo4j
database, persist trusted FACT relationships, read the base KGc back from
Neo4j, keep evaluated answer CLAIM relationships separate, and expose both
Research Trace and Advanced / Raw Trace.

The branch also contains a validated 50-question Apollo/NASA measurement set
with five questions at each designed path length from 1 through 10, plus a
checkpointing benchmark runner and JSON/Markdown reports.

## Exact local startup

```bash
git switch feature/local-neo4j-custom-runs
cp .env.example .env
```

The locally observed tags are `gemma4:e2b` and `gemma4:latest`.
`gemma4:12b` was not installed. Either set:

```dotenv
DEFAULT_MODEL=gemma4:e2b
OLLAMA_NUM_CTX=32768
```

or pull the configured 12b tag before selecting it:

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

- Ollama: `0.30.6`
- Real smoke model: `gemma4:e2b`
- Context setting: `OLLAMA_NUM_CTX=32768`
- Real custom smoke: returned `Rack R7` from the synthetic service/database/
  host/rack context with Neo4j persistence and readback.

Model quality and speed depend on local hardware. The 12b tag remains a
configuration target, not a locally verified installed model.

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

Run the complete real benchmark:

```bash
python scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/apollo_multihop_50.json \
  --provider ollama \
  --model gemma4:e2b \
  --num-ctx 32768 \
  --clear-neo4j \
  --limit 50 \
  --timeout-per-question 180 \
  --continue-on-error \
  --output results/apollo_multihop_report.json \
  --summary results/apollo_multihop_summary.md
```

The runner writes a checkpoint after every question. Use `--ids` for selected
questions or `--start-at` to resume from a particular ID. `--prompt-profile
compact` is accepted for experiment labeling but currently uses the unchanged,
validated prompts.

Reports are written under `results/`. The full mock report is plumbing-only:
the deterministic mock has no profile for this new context and its projection
failures are not model-accuracy evidence. Real results are explicitly labeled
partial or full.

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

Task 1 re-verification passed, including the frontend build, 178 backend tests,
bounded model audit, custom endpoint/UI controls, FACT readback, separate
CLAIMS, and raw trace availability.

## Known limitations

- `gemma4:12b` was not installed locally; select `gemma4:e2b` or pull 12b.
- Prompt token telemetry is approximate and the provider boundary does not yet
  attach a stage name.
- The comparator receives Python `KgcFact` objects reconstructed from Neo4j;
  it does not issue Cypher per comparison.
- Focused/derived additions are evaluated from the in-memory working mirror
  and persisted after success.
- Entity nodes are globally named, so safe isolation currently uses a full
  local-database clear rather than scope-only deletion.
- A full 50-question real-model benchmark is lengthy. Partial results must not
  be described as full benchmark performance.

## Next recommended work

Run the full real benchmark with checkpointing, inspect the first hop groups
where pipeline resolution or textual matching degrades, and investigate
general target/schema failures. Do not tune against expected answers or alter
deterministic labels merely to raise benchmark scores.

## Spoken update

I implemented the local custom-context Neo4j-backed branch. It can clear
Neo4j, extract a graph from a pasted context, persist trusted FACTS, keep
answer CLAIMS separate, and run decomposed backtracking over the custom input.
I also added a 50-question Apollo multi-hop benchmark from 1 to 10 hops and a
runner/report so we can measure where the process starts failing. Current
benchmark results should be treated as measurement infrastructure unless the
full real-model run has completed.
