# Sphinx documentation

## Build (verified command)

```bash
cd /path/to/grapheval_prototype
.venv/bin/pip install -r docs/requirements-docs.txt
.venv/bin/sphinx-build -b html docs/source docs/build/html
```

Verified on branch `research/methodology-and-code-documentation`: **build succeeded**
(exit 0). Local log: `docs/build/SPHINX_BUILD_LOG.txt`. Open
`docs/build/html/index.html`.

Generated HTML under `docs/build/` is covered by the repo `build/` gitignore pattern
and is not committed.

## Layout

- Handwritten MyST pages: `docs/source/*.md`
- Autodoc: `docs/source/api_reference.md`
- Diagrams: `docs/diagrams/`
- Research evidence companions: `research/METHODOLOGY_DOCUMENTATION_AUDIT.md`, etc.
