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
├── data/examples.json          # Input examples (question, context, optional initial answer)
├── prompts/                    # Prompt templates for each LLM step
├── results/                    # Per-example JSON outputs (gitignored)
└── src/
    ├── main.py                 # CLI entry point
    ├── models.py               # Dataclasses (Example, Triple, VerificationResult, …)
    ├── config.py               # Paths and defaults
    ├── io_utils.py             # Load/save JSON and prompts
    ├── llm/
    │   ├── base.py             # LLMProvider interface
    │   └── mock_provider.py    # Deterministic mock (no API keys)
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

## How to run

From the project root:

```bash
python -m src.main
```

No API keys are required. The default **mock provider** returns deterministic outputs for the sample Hyundai Sonata example.

Results are written to `results/<example_id>.json`.

## Module overview

| Module | Role |
|--------|------|
| `models.py` | Data types: `Example`, `Triple`, `VerificationResult`, `FeedbackItem`, `PipelineResult` |
| `llm/base.py` | Abstract `LLMProvider` — swap in OpenAI, Ollama, etc. later |
| `llm/mock_provider.py` | Fake LLM that drives the demo pipeline end-to-end |
| `pipeline/answer_generator.py` | Answer from question + context (skipped if `initial_answer` is set) |
| `pipeline/triple_extractor.py` | Parse `(subject, relation, object)` triples from the answer |
| `pipeline/triple_verifier.py` | Verify triples with LLM-as-judge; `NLIVerifier` stub for later |
| `pipeline/feedback_builder.py` | Turn failed verifications into revision instructions |
| `pipeline/answer_reviser.py` | Produce a corrected answer using feedback |
| `pipeline/runner.py` | Wire all stages and print a concise summary |
| `evaluation/metrics.py` | Count supported / contradicted / not-enough-info triples |

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

1. **Replace mock provider** with a real local or API LLM (Ollama, OpenAI, etc.).
2. **Compare LLM-as-judge vs NLI verification** — implement `NLIVerifier` and benchmark agreement.
3. **Add graph storage with Neo4j** — persist triples and verification edges for analysis.
4. **Run comparison study** — normal self-correction vs triple-level structured feedback.

## Requirements

Python 3.10+. The first version uses only the standard library. See `requirements.txt` for optional future dependencies.
