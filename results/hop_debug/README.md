# Hop debug results

Generated runtime result directories under `results/hop_debug/<timestamp>/`
remain local unless intentionally committed.

Use:

```bash
./scripts/run_hop_debug_sample.sh \
  --model <installed-small-model> \
  --num-ctx 32768 \
  --timeout-per-question 300
```

Each run writes:

- one JSON/Markdown report per selected Apollo question
- `summary.json` with exact-match, pipeline resolution, anomalies, runtime, and
  debug-log paths
- per-run JSONL logs in `.runtime/debug/` when `GRAPHEVAL_DEBUG_LOGS=true`
