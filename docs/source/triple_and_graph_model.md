# Triple and graph model

## Triple

Subject — Relation → Object.

## FACT vs CLAIM

- **FACT:** from trusted context; stored as `:FACT`; usable in evidence-path checks.
- **CLAIM:** from answer text; stored as `:CLAIM` with a Python-computed `label`.

Supported CLAIMs are **not** converted into FACTs.

## Normalization and validation

- Structured parsing / validation: `src/pipeline/structured_triple_validation.py`,
  `structured_output.py`
- Schema alignment: `src/pipeline/kgc_schema_aligner.py`
- Matching helpers: `src/pipeline/kgc_matching.py`

Malformed examples observed in traces include empty objects
(`structured_triple_anomaly` / `empty_object`).

## Worked examples

See `research/ALGORITHM_WORKED_EXAMPLES.md` (SUPPORTED, CONTRADICTED, NO_EVIDENCE,
official hop_036 limits, WannaCry regression).
