# Structured Triple Flow

Documented from code inspection of the canonical `master` application.
This describes **actual** behavior, not aspirational architecture.

## Dataflow

```
UI input
→ API request
→ Example
→ question decomposition
→ context extraction prompt
→ raw model response
→ triple parser + structured validation
→ KgcFact(subject, relation, object)
→ Neo4j FACT persistence
→ Neo4j FACT readback (custom/benchmark routes)
→ WorkingKgcState
→ answer claim extraction
→ Triple(subject, relation, object) as CLAIM
→ deterministic comparison
→ revision
→ final combined answer
```

## Step-by-step (actual code)

### 1. What starts a run

| Entry | File | Symbol |
|---|---|---|
| Frontend default | `frontend/app/page.tsx` | `handleRunDecomposedKgc` |
| Built-in example API | `api/server.py` | `POST /run-decomposed-kgc-backtracking` |
| Custom API | `api/server.py` | `POST /run-decomposed-kgc-backtracking-custom` |
| Benchmark API | `api/server.py` | `POST /run-benchmark-question` |
| CLI | `scripts/run_multihop_benchmark.py` | `run_one` → `DecomposedBacktrackingRunner` |

Frontend helpers live in `frontend/lib/api.ts`.

### 2. Frontend request

Default workflow is Decomposed Backtracking. Depending on source:

- built-in → `runDecomposedKgcBacktracking`
- custom → `runCustomDecomposedKgcBacktracking`
- benchmark → `runBenchmarkQuestion`

### 3. API route → Example

`Example` is defined in `src/models.py`:

```python
@dataclass
class Example:
    id: str
    question: str
    context: str
    initial_answer: Optional[str] = None
```

Benchmark routes set `context = trusted_context(benchmark_id)` from
`src/benchmarks/catalog.py` and never pass expected answers into the runner.

### 4. Trusted context

Trusted text is `Example.context`. Context-fact extraction and focused extraction
read this string. Carry-forward text from resolved sub-answers is **not** written
as FACT edges (`WorkingKgcState.build_carry_forward_context`).

### 5–8. Context-fact extraction

1. `DecomposedBacktrackingRunner.run_example` (`src/pipeline/decomposed_backtracking_runner.py`)
2. `ContextTripleExtractor.extract_with_trace` (`src/pipeline/context_triple_extractor.py`)
3. Prompt templates: `prompts/context_triple_extraction.txt` / `_csv.txt`
4. Provider call: `complete_with_trace(self.provider.complete, …)` in
   `src/pipeline/structured_output.py`
5. Provider implementations: `src/llm/ollama_provider.py`, `src/llm/mock_provider.py`

Raw model output is retained in `StructuredExtractionTrace.attempts[].raw_preview`
(truncated) and, when `GRAPHEVAL_DEBUG_LOGS=true`, in the per-run JSONL log.

### 9–11. Parsing into structured triples

Parser entry points:

- `parse_context_facts_response` / `parse_claims_response`
- JSON path: `parse_context_facts_json` / `parse_claims_json`
- CSV path: `parse_context_facts_csv` / `parse_claims_csv`

Validation boundary:

- `src/pipeline/structured_triple_validation.py` → `coerce_raw_triple_item`

Schema:

| Kind | Type | Fields |
|---|---|---|
| FACT | `KgcFact` | `subject`, `relation`, `object`, `evidence?` |
| CLAIM | `Triple` | `subject`, `relation`, `object`, `source_sentence?` |

There is no separate `KgcClaim` class. Answer claims remain `Triple` values and are
stored in Neo4j as `:CLAIM` relationships.

Assignment is by named keys / validated positional arrays. Safe aliases such as
`predicate→relation` and `obj→object` are recorded as normalizations. Null,
empty, nested, or untraceable objects are rejected as anomalies.

### 12. Normalization / alignment

After claim extraction:

1. `condition_claims_to_question` (`question_target.py`)
2. `ground_claim_objects_in_answer` (`claim_grounding.py`) — may rewrite claim
   object to `source_sentence` or full answer text when the extracted object is
   not found in the answer
3. `dedupe_minimal_claims`
4. `align_claims_to_kgc_schema` (`kgc_schema_aligner.py`) — may rewrite subject /
   relation to a unique KGc match while **keeping claim.object**

### 13–14. Focused and derived facts

- Focused: `RelevantContextFactExtractor` → `WorkingKgcState.merge_focused_facts`
  (provenance `TRUSTED_CONTEXT`)
- Derived: `TargetFactDeriver.derive` → `WorkingKgcState.merge_derived_facts`
  (provenance `DERIVED_FROM_TRUSTED_CONTEXT`)

### 15–16. Answer claims vs FACTS

| | FACTS | CLAIMS |
|---|---|---|
| Source | trusted context / focused / derived | answer text |
| In-memory | `KgcFact` | `Triple` |
| Neo4j | `:FACT` | `:CLAIM` |
| Comparator gold | yes | no |

Supported claims are recorded as candidates by default and are **not**
auto-promoted into FACTS (`working_kgc_auto_promote=False`).

### 17–19. Neo4j write / readback / working KGc

- Write: `Neo4jStore.store_kgc_facts` / `_create_fact`
- Readback: `Neo4jStore.get_kgc_facts` — used when `neo4j_readback=True`
  (custom + benchmark API routes)
- Working memory: `WorkingKgcState.facts_for_comparison()`

### 20. Comparator input

`GraphComparator.compare_claims(aligned_claims, kgc_facts=working_state.facts_for_comparison(), …)`
in `src/pipeline/kgc_iteration.py`.

### 21. Sub-question stop reasons

`determine_stop_reason` in `kgc_iteration.py` yields
`RESOLVED`, `STALLED`, `UNRESOLVED_NO_EVIDENCE`,
`UNRESOLVED_TARGET_NOT_SATISFIED`, `MAX_ITERATIONS`,
`GENERATION_FAILED`, or `NO_CLAIMS_EXTRACTED`.

### 22. Final combined answer

`combine_sub_answers` in `src/pipeline/sub_answer_combiner.py` concatenates
sub-answers deterministically; unresolved rows keep their stop-reason tag.

## Actual vs desired

| Topic | Actual | Desired for research |
|---|---|---|
| Null/`object` coercion | Previously `str(None)→"None"`; now rejected | Reject + anomaly |
| Nested object values | Previously accepted as Python `repr` | Reject + anomaly |
| Claim grounding rewrite | Still active for answer-side claims | Keep, but log |
| FACT/CLAIM separation | Enforced | Keep |
| Expected answers in inference | Not passed | Keep |
