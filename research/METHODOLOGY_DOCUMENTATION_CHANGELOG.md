# Methodology documentation change log

Branch: `research/methodology-and-code-documentation`

## Summary

Documentation-and-methodology revision only. No inference, prompt, benchmark data,
or frozen experiment result mutations.

## Added

- `research/METHODOLOGY_DOCUMENTATION_AUDIT.md` — Phase 1 audit table + call sequence
- `research/NEO4J_DATA_MODEL.md` — verified Neo4j schema and persistence behavior
- `research/ALGORITHM_WORKED_EXAMPLES.md` — real SUPPORTED / CONTRADICTED / NO_EVIDENCE / hop_036 / WannaCry examples
- `research/NEO4J_SCREENSHOT_GUIDE.md` — Cypher queries 1–6 for Browser screenshots
- `docs/diagrams/source/*.mmd` + `docs/diagrams/rendered/*.svg` — four required diagrams
- `docs/source/` Sphinx MyST site + `docs/requirements-docs.txt` + `docs/SPHINX_BUILD.md`
- `docs/build/SPHINX_BUILD_LOG.txt` — local build record (HTML itself under ignored `build/`)

## Updated

- `reports/GraphEval Experiment Report.md` — Methodology rewritten as §§2.1–2.9 with diagrams and screenshot placeholders; Results and later sections preserved
- `reports/GraphEval Experiment Report.docx` — regenerated via `scripts/build_experiment_report_docx.py`
- `scripts/build_experiment_report_docx.py` — heading list aligned to new methodology subsections

## Verified non-changes

- No edits under `src/`, `prompts/`, or frozen Apollo result JSON content for this pass
- Inference-sensitive paths match freeze intent relative to documentation work (diff empty for comparator/iteration/store/prompts vs `b9608d0` on this check)
- Offline tests: `417 passed, 16 skipped` (behavior-suite file left untracked/ignored for this run)

## Sphinx build command (successful)

```bash
.venv/bin/sphinx-build -b html docs/source docs/build/html
```

Result: `build succeeded` (0 image warnings after path fix).

## Author-only remaining

- Capture Neo4j Browser screenshots using `research/NEO4J_SCREENSHOT_GUIDE.md` (Queries 1–6) and replace report placeholders
- Optional: resolve GraphEval paper attribution TODO in References
