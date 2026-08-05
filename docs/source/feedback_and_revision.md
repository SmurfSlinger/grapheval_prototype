# Feedback and revision

## Feedback

`BacktrackingFeedbackBuilder` (`src/pipeline/backtracking_feedback_builder.py`)
builds one item per evaluation:

- SUPPORTED → preserve
- CONTRADICTED → correct using conflicting FACT object
- NO_EVIDENCE → omit or mark for retrieval/adjudication

## Revision

`BacktrackingReviser` sends the structured feedback to the LLM. Only answer text
is revised; Neo4j FACT edges are not rewritten by the reviser.

## Stop conditions

`determine_stop_reason` in `src/pipeline/kgc_iteration.py` (max iterations = 3 in
the official experiment). RESOLVED requires clean labels, satisfied target, and
non-incomplete evidence path.
