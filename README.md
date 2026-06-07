# grapheval_prototype

A small **GraphEval-style hallucination feedback** prototype for undergraduate research. The system runs an external loop around an LLM: extract factual triples from an answer, verify them against trusted context, build structured feedback for failures, and revise the answer.

## Goal

Reduce hallucinations by giving the model **triple-level feedback** instead of a generic “try again” prompt. Each unsupported or contradicted fact is flagged with evidence from the trusted context before revision.

```
Question + trusted context
  → generate or accept an LLM answer
  → extract triples from the answer
  → verify each triple against context
  → build feedback for unsupported/contradicted triples
  → revise the answer
  → save results
```

## Architecture

```
grapheval_prototype/
├── api/server.py               # FastAPI wrapper around the Python pipeline
├── frontend/                   # Next.js demo UI
├── data/examples.json          # Input examples (question, context, optional initial answer)
├── prompts/                    # Prompt templates for each LLM step
├── results/                    # Per-example JSON outputs (gitignored)
└── src/
    ├── main.py                 # CLI entry point
    ├── models.py               # Dataclasses (Example, Triple, VerificationResult, …)
    ├── config.py               # Paths, Ollama settings, defaults
    ├── io_utils.py             # Load/save JSON and prompts
    ├── llm/
    │   ├── base.py             # LLMProvider interface
    │   ├── mock_provider.py    # Deterministic mock (no API keys)
    │   └── ollama_provider.py  # Local Ollama / Gemma4 (text-only)
    ├── pipeline/
    │   ├── answer_generator.py
    │   ├── triple_extractor.py
    │   ├── triple_verifier.py  # LLM-as-judge; NLI placeholder included
    │   ├── feedback_builder.py
    │   ├── answer_reviser.py
    │   └── runner.py           # Orchestrates the full loop
    └── evaluation/
        └── metrics.py          # Simple verification counts
```

## Requirements

Python 3.10+. Node.js 18+ for the web UI.

Install Python dependencies (CLI + API):

```bash
pip install -r requirements.txt
```

## Install and run Ollama

1. Install Ollama from [https://ollama.com](https://ollama.com).
2. Start the server (usually runs automatically after install):

```bash
ollama serve
```

3. Pull the Gemma4 models used by this prototype:

```bash
ollama pull gemma4:e2b
ollama pull gemma4:e4b
ollama pull gemma4:12b
```

The prototype is **text-only**. Even if a Gemma4 variant supports images, this project sends plain-text prompts only.

## How to run

### Web UI (recommended for demos)

**Terminal 1 — backend** (from project root):

```bash
pip install -r requirements.txt
uvicorn api.server:app --reload --port 8000
```

**Terminal 2 — frontend**:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The UI lets you pick an example or run a custom question/context/answer, choose `mock` or `ollama`, and inspect triples, verification labels, feedback, and the revised answer.

For `provider=ollama`, Ollama must be running and the model pulled:

```bash
ollama serve
ollama pull gemma4:e2b
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### CLI

From the project root:

#### Mock provider (default, no Ollama needed)

```bash
python -m src.main
python -m src.main --provider mock
```

Returns deterministic outputs for the sample Hyundai Sonata example. Useful for testing the pipeline without a local LLM.

#### Ollama / Gemma4

```bash
python -m src.main --provider ollama
python -m src.main --provider ollama --model gemma4:e2b
python -m src.main --provider ollama --model gemma4:e4b
python -m src.main --provider ollama --model gemma4:12b
```

Results are written to `results/<example_id>.json`, or `results/<example_id>_<model>.json` when a specific Ollama model is selected (e.g. `results/hyundai_sonata_001_gemma4_e2b.json`).

If Ollama is not running or the model is missing, the CLI **falls back to the mock provider** by default and prints a warning. Use `--no-fallback` to fail instead.

#### Compare models

Run the same examples across all configured test models:

```bash
python -m src.main --provider ollama --compare-models
```

Saves separate files per model, e.g.:

- `results/hyundai_sonata_001_gemma4_e2b.json`
- `results/hyundai_sonata_001_gemma4_e4b.json`
- `results/hyundai_sonata_001_gemma4_12b.json`

## Module overview

| Module | Role |
|--------|------|
| `models.py` | Data types: `Example`, `Triple`, `VerificationResult`, `FeedbackItem`, `PipelineResult` |
| `llm/base.py` | Abstract `LLMProvider` — swap backends via CLI |
| `llm/mock_provider.py` | Fake LLM that drives the demo pipeline end-to-end |
| `llm/ollama_provider.py` | Calls `http://localhost:11434/api/generate` (streaming off) |
| `pipeline/answer_generator.py` | Answer from question + context (skipped if `initial_answer` is set) |
| `pipeline/triple_extractor.py` | Parse `(subject, relation, object)` triples from the answer |
| `pipeline/triple_verifier.py` | Verify triples with LLM-as-judge; `NLIVerifier` stub for later |
| `pipeline/feedback_builder.py` | Turn failed verifications into revision instructions |
| `pipeline/answer_reviser.py` | Produce a corrected answer using feedback |
| `pipeline/runner.py` | Wire all stages and print a concise summary |
| `evaluation/metrics.py` | Count supported / contradicted / not-enough-info triples |
| `api/server.py` | FastAPI endpoints: `/health`, `/examples`, `/run`, `/run-custom` |
| `frontend/` | Next.js UI for running examples and viewing results |

## Ollama error handling

`OllamaProvider` reports clear errors for:

- **Server not running** — connection refused; suggests `ollama serve`
- **Model not installed** — suggests `ollama pull <model>`
- **Timeout** — request exceeded `OLLAMA_REQUEST_TIMEOUT` (default 120s)
- **Invalid API response** — malformed JSON from the Ollama HTTP API
- **Invalid model JSON output** — raised when extraction/verification prompts return unparseable JSON

## Sample example

**Context:** “The 2018 Hyundai Sonata SE has a 2.4L engine and was assembled in Alabama.”

**Initial answer:** “The 2018 Hyundai Sonata SE has a 2.4L turbo engine and was assembled in Korea.”

**Expected triples:**
- `(2018 Hyundai Sonata SE, has_engine, 2.4L turbo engine)`
- `(2018 Hyundai Sonata SE, assembled_in, Korea)`

**Expected verification:**
- `has_engine → 2.4L turbo engine` → NOT_ENOUGH_INFO (context says 2.4L, not turbo)
- `assembled_in → Korea` → CONTRADICTED (context says Alabama)

**Expected revised answer:** “The 2018 Hyundai Sonata SE has a 2.4L engine and was assembled in Alabama.”

## Next planned steps

1. **Benchmark Gemma4 sizes** — use `--compare-models` to study speed/quality trade-offs.
2. **Compare LLM-as-judge vs NLI verification** — implement `NLIVerifier` and benchmark agreement.
3. **Add graph storage with Neo4j** — persist triples and verification edges for analysis.
4. **Run comparison study** — normal self-correction vs triple-level structured feedback.
