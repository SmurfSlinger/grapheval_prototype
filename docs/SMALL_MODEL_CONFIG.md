# Small-model testing configuration

## Intent

Use an approximately 7B/8B-class local instruction model so hop-depth experiments
are fast enough to repeat.

## Inspection command

```bash
ollama list
```

Do not invent an installed model.

## Repository default

- `DEFAULT_MODEL=gemma4:e4b`
- `OLLAMA_NUM_CTX=32768`
- `OLLAMA_NUM_PREDICT=4096`

`num_ctx=32768` only reduces cutoff risk for long structured prompts. It does
not improve multi-hop reasoning by itself.

## Selection rule

Choose the smallest locally installed instruction-capable model reasonably close
to the 7B/8B class. Record:

- exact model tag
- reported size when available
- configured `num_ctx`
- why it was selected

If no suitable model is installed, document the recommended pull command and
continue mock/unit work. Do not silently substitute a much larger model.

## Recommended pull when missing

```bash
ollama pull gemma4:e4b
```

Re-check with `ollama list` after the pull.
