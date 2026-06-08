# grapheval_prototype

A small **GraphEval-style hallucination feedback** prototype for undergraduate research. The system runs an external loop around an LLM: extract factual triples from an answer, verify them against trusted context, build structured feedback for failures, and revise the answer.

## Goal

Reduce hallucinations by giving the model **triple-level feedback** instead of a generic “try again” prompt. Each unsupported or contradicted fact is flagged with evidence from the trusted context before revision.

The prototype also runs a **self-correction baseline** so you can compare:

- **Self-correction** — generic “check your answer against the context” revision
- **Graph-feedback correction** — revision driven by specific unsupported/contradicted triples

## Architecture diagram

```
User selects example / custom input
        ↓
Next.js frontend
        ↓
FastAPI backend
        ↓
Python GraphEval pipeline
        ↓
Ollama / Gemma4 provider (or mock)
        ↓
Answer → triples → verification → feedback → revision
        ↓
Results returned to frontend
```

## Implementation status

- CLI prototype working with mock and Ollama/Gemma4.
- FastAPI backend working (`/health`, `/examples`, `/run`, `/run-custom`, `/run-all`).
- Next.js frontend working with single-run, run-all, and custom input.
- Pipeline supports triple extraction, verification, graph feedback, revision, and self-correction baseline.
- Post-revision re-verification counts remaining bad triples after graph-feedback revision.
- **Next step:** formal comparison study — self-correction vs triple-level graph feedback.

## Project layout

```
grapheval_prototype/
├── api/server.py               # FastAPI wrapper
├── frontend/                   # Next.js demo UI
├── data/examples.json          # Test examples (6 domains)
├── prompts/                    # LLM prompt templates
├── results/                    # Saved JSON outputs (gitignored)
└── src/                        # Python pipeline (source of truth)
```

## Requirements

Python 3.10+. Node.js 18+ for the web UI.

```bash
pip install -r requirements.txt
```

## Install and run Ollama

```bash
ollama serve
ollama pull gemma4:e2b
ollama pull gemma4:e4b
ollama pull gemma4:12b
```

Text-only prompts — image input is not used even if the model supports it.

## How to run

### Web UI (recommended for demos)

**Backend** (project root):

```bash
pip install -r requirements.txt
uvicorn api.server:app --reload --port 8000
```

**Frontend**:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The UI supports:
- Run one example or **Run all examples**
- Custom question / context / initial answer
- Side-by-side self-correction vs graph-feedback outputs
- Summary cards and triple tables with verification badges

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### CLI

**Mock** (no Ollama):

```bash
python -m src.main --provider mock
```

**Ollama / Gemma4** — runs **all examples** in `data/examples.json` by default:

```bash
python -m src.main --provider ollama --model gemma4:e2b
python -m src.main --provider ollama --model gemma4:e2b --run-all
```

**Compare model sizes**:

```bash
python -m src.main --provider ollama --compare-models
```

Results save to `results/<example_id>.json` or `results/<example_id>_<model>.json`.

### Run all examples via API

```bash
curl -X POST http://localhost:8000/run-all \
  -H "Content-Type: application/json" \
  -d '{"provider": "mock", "model": "gemma4:e2b"}'
```

## Comparison methodology

| Method | Prompt | What it uses |
|--------|--------|--------------|
| **Self-correction** | `prompts/self_correction.txt` | Context + answer; generic faithfulness check |
| **Graph-feedback** | extract → verify → `prompts/answer_revision.txt` | Specific triples with evidence and instructions |

`PipelineResult` includes both outputs plus `metrics`:

- Initial triple counts (supported / contradicted / not enough info)
- Whether graph revision was needed
- Remaining bad triples after graph-feedback re-verification (one pass)

## Module overview

| Module | Role |
|--------|------|
| `pipeline/runner.py` | Orchestrates full loop + self-correction + re-verification |
| `pipeline/self_corrector.py` | Baseline self-correction |
| `pipeline/triple_extractor.py` | Extract triples from answers |
| `pipeline/triple_verifier.py` | LLM-as-judge verification |
| `pipeline/feedback_builder.py` | Build triple-level revision instructions |
| `pipeline/answer_reviser.py` | Graph-feedback answer revision |
| `evaluation/metrics.py` | Scoring / count fields |
| `api/server.py` | HTTP API wrapping the pipeline |
| `frontend/` | Demo UI |

## Ollama error handling

- Server not running → suggests `ollama serve`
- Model missing → suggests `ollama pull <model>`
- Timeout, invalid API JSON, unparseable model JSON output

## Next planned steps

1. **Formal comparison study** — self-correction vs graph-feedback across all examples and models.
2. **LLM-as-judge vs NLI verification** — implement `NLIVerifier`.
3. **Neo4j graph storage** — persist triples and verification edges.
