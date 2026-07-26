# Next-Week Debug Plan

## Current research question

At what designed graph-path depth does the GraphEval decomposed pipeline begin to
fail reliably with the selected small local model?

## Selected small-model configuration

- Preferred local class: ~7B/8B instruction model
- Configured default tag in repo: `gemma4:e4b` (from `.env.example` / `DEFAULT_MODEL`)
- Context length: `OLLAMA_NUM_CTX=32768` (reduces cutoff risk; does not deepen reasoning)
- This environment did not have `ollama` installed at finalization time. Before
  research runs, inspect the real machine with `ollama list` and use the smallest
  installed instruction-capable tag near the 7B/8B class.
- If missing, pull an honestly sized tag, for example:

```bash
ollama pull gemma4:e4b
```

Do not silently substitute a much larger model and call it 8B.

## Daily workflow

1. Select one benchmark family (prefer Apollo first)
2. Select hop depth with the Question depth filter / `--ids`
3. Run fixed questions without modifying them
4. Save result JSON/Markdown and `.runtime/debug/<run_id>.jsonl`
5. Identify the first failing stage in the debug log
6. Categorize the failure
7. Make only general pipeline fixes
8. Rerun the same fixed sample

Bounded sample command:

```bash
export GRAPHEVAL_DEBUG_LOGS=true
export OLLAMA_NUM_CTX=32768
./scripts/run_hop_debug_sample.sh \
  --model <installed-small-model> \
  --num-ctx 32768 \
  --timeout-per-question 300
```

## Failure categories

- question decomposition
- trusted-fact extraction
- malformed structured triple
- wrong triple object
- fact omission
- Neo4j persistence
- Neo4j readback
- working-KGc contamination
- claim extraction
- claim alignment
- unsupported claim
- contradiction
- NO_EVIDENCE
- target satisfaction
- answer revision
- answer combination
- timeout
- context cutoff

## Research discipline

- Do not alter benchmark questions after observing failures
- Do not expose expected answers during inference
- Do not retry until a favorable result appears
- Retain failed runs
- Use the same model and context length for comparable runs
- Separate answer matching from pipeline resolution
- Preserve all structured-triple anomaly logs

## End-of-week target

A stable version that can be demonstrated with:

- very simple UI
- selected small model
- reproducible one-hop through three-hop runs
- structured debug logs
- a clear diagnosis of where three-hop processing fails
- a pushed GitHub branch
