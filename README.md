# GraphEval Prototype

GraphEval is an undergraduate research prototype for evaluating and revising LLM answers against trusted context. The project explores whether graph-grounded feedback can make factual errors easier to detect, explain, and correct than simply asking a model to reconsider its answer.

## How it works

GraphEval represents trusted context as **FACT** triples and statements from the model's answer as **CLAIM** triples.

Python compares the claims against trusted facts and labels them:

- `SUPPORTED`
- `CONTRADICTED`
- `NO_EVIDENCE`

It also checks whether the answer satisfies the question being asked and whether the final answer can be connected through a complete path of trusted facts.

If an answer is unresolved, GraphEval builds structured feedback and gives the model another chance to revise. The loop is bounded rather than open-ended.

The main responsibilities are separated:

- **LLM:** question decomposition, triple extraction, answer generation, and revision
- **Python:** validation, claim comparison, target/path checks, feedback, and stop decisions
- **Neo4j:** execution-scoped storage of FACT and CLAIM relationships and trusted FACT readback

Neo4j stores graph state; it does not decide whether a claim is correct.

A supported CLAIM also remains a CLAIM. Model output is never promoted into the trusted FACT set just because it was supported.

## Experiment

The main experiment used 50 Apollo questions, with five questions at each designed graph-path depth from 1 through 10.

The frozen run used:

- `llama3.1:8b` through Ollama
- temperature 0
- up to 3 iterations per sub-question
- Neo4j enabled and required

Results:

- 50/50 questions completed
- 0 errors
- 0 timeouts
- 27/50 exact answers
- 43/50 contained the expected answer
- 33/50 were pipeline-resolved
- 36/50 had a complete trusted evidence path

The experiment was repeated three times under the same frozen configuration, with the same discrete outcomes for all 50 questions across all three runs.

This was a prototype feasibility study. It does not establish that graph feedback causally reduces hallucinations because the completed experiment did not include a no-feedback or generic self-correction control condition.

## Repository

- `src/pipeline/` — GraphEval pipeline and evaluation logic
- `src/storage/neo4j_store.py` — Neo4j persistence and readback
- `scripts/run_multihop_benchmark.py` — benchmark runner
- `data/test_sets/` — benchmark data
- `results/research/` — official results and analyses
- `reports/` — final experiment report
- `research/` — protocols, reproducibility records, and Neo4j evidence
- `docs/source/` — Sphinx documentation
- `frontend/` and `api/` — local demo interface

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..

cp .env.example .env
./scripts/devctl.sh start ollama
```

## Useful Commands

```bash
./scripts/devctl.sh status
./scripts/devctl.sh smoke
./scripts/devctl.sh logs
./scripts/devctl.sh stop
```

## Building the Sphinx Documentation

The documentation under `docs/source/` is a Sphinx site generated with Sphinx, MyST Markdown, autodoc, and the Furo theme.

From the repository root:

```bash
source .venv/bin/activate
pip install -r docs/requirements-docs.txt

sphinx-build -W --keep-going -b html docs/source docs/build/html

python3 -m http.server 9000 -d docs/build/html
```

Then open:

```text
http://localhost:9000
```

The generated HTML under `docs/build/` is not committed to the repository.
