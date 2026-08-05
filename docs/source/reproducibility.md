# Reproducibility

Authoritative record: `research/REPRODUCIBILITY_RECORD.md` and
`research/EXPERIMENT_PROTOCOL.md`.

## Frozen software

- Inference commit: `b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`
- Model: `llama3.1:8b` via Ollama, temperature 0, `num_ctx` 8192, max iterations 3

## Documentation build

```bash
.venv/bin/pip install -r docs/requirements-docs.txt
sphinx-build -b html docs/source docs/build/html
```

## Report DOCX

```bash
.venv/bin/python scripts/build_experiment_report_docx.py
```

Do not modify inference prompts, benchmark data, or frozen result files when
updating documentation.
