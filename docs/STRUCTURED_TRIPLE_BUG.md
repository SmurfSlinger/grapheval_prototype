# Structured Triple Third-Element Bug

## Symptom

A structured triple is produced, but the third element (`object`) is not the
value the pipeline should have accepted from the provider response.

## Minimal failing input

Trusted context:

```text
System Alpha uses Service A.
Service A depends on Database B.
Database B runs on Host C.
Host C is located in Rack R7.
```

Synthetic provider/JSON response (captured fixture
`tests/fixtures/structured_triple_null_object_failure.json`):

```json
{
  "triples": [
    {
      "subject": "Host C",
      "relation": "located_in",
      "object": null,
      "evidence": "Host C is located in Rack R7."
    },
    {
      "subject": "Database B",
      "relation": "runs_on",
      "object": {"name": "Host C"},
      "evidence": "Database B runs on Host C."
    }
  ]
}
```

Expected parsed structure:

- reject both items (null object / nested object)
- emit structured anomalies
- do not invent `object="None"` or `object="{'name': 'Host C'}"`

## Actual pre-fix behavior

In `src/pipeline/structured_output.py`:

```python
obj = str(item.get("object", "")).strip()
```

| Raw `object` | Parsed object (wrong) |
|---|---|
| `null` | `"None"` |
| `{"name": "Host C"}` | `"{'name': 'Host C'}"` |
| `["Rack R7"]` | `"['Rack R7']"` |

Because `"None"` is a nonempty string, the old required-field check accepted it
as a valid third element. Divergence therefore occurred at **JSON parsing /
dictionary-key value coercion**, not in Neo4j or the comparator.

Exact function: `parse_context_facts_json` / `parse_claims_json`
(`src/pipeline/structured_output.py`), before validation existed.

Secondary CSV issue: Title-Case headers passed lowercase validation in
`parse_csv_rows`, but `DictReader` key lookup used lowercase names, blanking all
fields. That failed closed as “no data rows” rather than swapping object values.
It is fixed with case-insensitive header mapping.

## Root cause

Unsafe `str(...)` coercion of non-string / null `object` values invented a
third element that was not present as a usable string in the provider output.

## Narrow fix

1. Add `src/pipeline/structured_triple_validation.py` with
   `coerce_raw_triple_item`.
2. Reject null, empty, nested list/dict, relation-copied, and untraceable
   objects.
3. Allow safe normalizations only (positional arrays, key aliases) and record
   them.
4. Route parsers through validation; keep valid triples; record anomalies;
   raise only when every triple in the response is rejected.
5. Emit debug events `structured_triple_validated` /
   `structured_triple_anomaly` when `GRAPHEVAL_DEBUG_LOGS=true`.

## Regression tests

`tests/test_structured_triple_validation.py` covers:

1. Correct `[subject, relation, object]` parsing
2. Correct dictionary parsing
3. Missing third element
4. Null object
5. Nested object value
6. Swapped / malformed positional values
7. Captured failure fixture
8. Valid Apollo extraction
9. Valid Patient D-314 extraction

## Related but separate behavior

`ground_claim_objects_in_answer` (`src/pipeline/claim_grounding.py`) can later
rewrite a **claim** object to `source_sentence` or the full answer string when
the extracted object is not found in the answer. That is intentional answer-side
grounding, not the FACT parse bug above. It remains logged for research
inspection and is not auto-promoted into FACTS.
