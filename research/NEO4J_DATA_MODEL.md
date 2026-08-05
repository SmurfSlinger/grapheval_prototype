# Neo4j Data Model (Verified)

**Source of truth:** `src/storage/neo4j_store.py`, `scripts/recreate-neo4j.sh`  
**Audit companion:** `research/METHODOLOGY_DOCUMENTATION_AUDIT.md`  
**Credentials:** not included.

Neo4j is a **persistence and readback store**. Claim labels, stop reasons, target satisfaction, and evidence-path completeness are computed in Python. Neo4j does not call the LLM and does not promote CLAIMs to FACTs.

## 1. Node labels

| Label | Identity / keys | Properties used by GraphEval |
|---|---|---|
| `:Entity` | Composite uniqueness on `(execution_id, name)` when the DB edition supports it; otherwise a composite index | `execution_id` (string), `name` (string entity text) |

There are no separate `:Fact` or `:Claim` **node** labels. Facts and claims are **relationship** types between Entity nodes.

## 2. Relationship types

### 2.1 `:FACT` (trusted or working enrichment)

Written by `Neo4jStore._create_fact` (context) and `_create_working_fact` (focused/derived additions).

**Write pattern:** `MERGE` on endpoints and on the FACT relationship keyed by:

```
execution_id, relation, provenance, extraction_stage
```

Then `SET` additional properties.

**Context FACT properties (verified Cypher):**

| Property | Typical value |
|---|---|
| `execution_id` | scope execution id |
| `relation` | relation string |
| `provenance` | `"trusted_context"` |
| `extraction_stage` | `"context_triple_extraction"` |
| `example_id` | example / question id |
| `benchmark_id` | benchmark id or empty |
| `question_id` | question id |
| `evidence` | evidence string (may be empty) |
| `source` | `"trusted_context"` |
| `created_order` | integer order of write |

**Working FACT additional properties:** `sub_question_id`, `derivation_type`, `evidence_spans`, `derivation_explanation`; `provenance` / `source` / `extraction_stage` come from the working addition object.

### 2.2 `:CLAIM` (answer-sourced)

Written by `Neo4jStore._create_kgc_claim` (decomposed / KGc path) via **`CREATE`** (not MERGE). Each evaluation produces a **new** relationship. Earlier iterations’ CLAIM edges remain unless the execution’s entities are deleted.

**CLAIM properties (verified Cypher):**

| Property | Meaning |
|---|---|
| `execution_id` | execution scope |
| `example_id` | example id |
| `benchmark_id` | benchmark id |
| `question_id` | question id |
| `sub_question_id` | integer or null |
| `relation` | claim relation |
| `label` | `SUPPORTED` / `CONTRADICTED` / `NO_EVIDENCE` (Python-computed, then stored) |
| `reason` | comparison reason string |
| `evidence` | evidence string from evaluation |
| `answer_stage` | e.g. `sub_question_1_answer_0` |
| `iteration` | iteration index |
| `source` | `"answer"` |
| `conflicting_object` | object from conflicting FACT when present |
| `conflicting_fact` | serialized `S -- R --> O` string when present |

A legacy `_create_claim` path exists for older verification results (fewer properties; no `iteration` / `sub_question_id` / conflict fields). The live decomposed runner uses `_create_kgc_claim`.

## 3. Schema sketch (exact labels/types)

```
(:Entity {execution_id, name})
    -[:FACT {execution_id, relation, provenance, extraction_stage, ...}]->
(:Entity {execution_id, name})

(:Entity {execution_id, name})
    -[:CLAIM {execution_id, relation, label, reason, iteration, sub_question_id, ...}]->
(:Entity {execution_id, name})
```

Same entity name in two executions is **two nodes** (different `execution_id`).

## 4. Constraints and indexes

Installed by `scripts/recreate-neo4j.sh`:

```cypher
CREATE CONSTRAINT grapheval_entity_per_execution IF NOT EXISTS
FOR (e:Entity) REQUIRE (e.execution_id, e.name) IS UNIQUE;
-- fallback if composite uniqueness unsupported:
CREATE INDEX grapheval_entity_per_execution_idx IF NOT EXISTS
FOR (e:Entity) ON (e.execution_id, e.name);

CREATE INDEX grapheval_fact_execution_idx IF NOT EXISTS
FOR ()-[f:FACT]-() ON (f.execution_id);

CREATE INDEX grapheval_claim_execution_idx IF NOT EXISTS
FOR ()-[c:CLAIM]-() ON (c.execution_id);
```

## 5. Execution scoping

- Every Entity and every FACT/CLAIM relationship carries `execution_id`.
- Reads (`get_kgc_facts`, `get_claims`, `get_execution_summary`, …) filter on that id.
- `get_claims_for_example` is a **legacy** view across executions sharing `example_id`.

## 6. Write / read lifecycle (one question)

1. Begin scope → new `execution_id`.
2. Optional `clear_execution(execution_id)` — deletes only that id (usually a no-op on a fresh id; used when the flag requests a clear).
3. Write context FACTs (`MERGE`).
4. Optional readback of FACTs into the working KGc used by Python comparison.
5. During iteration: comparison runs in Python on the in-memory / readback FACT list (not via Cypher reasoning).
6. After each sub-question completes: for **each** iteration in history, `CREATE` CLAIM edges for that iteration’s evaluations.
7. Optionally write working FACT additions (`MERGE`).
8. Next benchmark question uses a **new** `execution_id`. Cross-question isolation does not require wiping the entire database; leftover prior executions may remain until an explicit `clear_all` / volume reset.

Official Apollo runs used Neo4j with clearing configured between questions (`clear_neo4j_between_runs` / `--clear-neo4j` in the preserved protocol). That clear is still **per new execution id** as implemented in `clear_execution`, not a global `DETACH DELETE` of all nodes.

## 7. How CLAIMs behave across iterations

| Question | Verified answer |
|---|---|
| Are labels calculated in Neo4j? | **No** — `GraphComparator` in Python |
| Are labels stored in Neo4j? | **Yes** — on CLAIM relationships when persistence is enabled |
| Do previous-iteration CLAIMs remain? | **Yes** — CREATE append; no delete of prior CLAIMs in the iteration loop |
| Do revised claims replace earlier ones? | **No** — they **coexist**, distinguished by `iteration` / `answer_stage` |
| Can SUPPORTED CLAIMs become FACTs? | **No** — no such write path |

## 8. Short verified Cypher fragments (for authors)

Replace `$execution_id` with a real id from a result row or trace (examples in `research/NEO4J_SCREENSHOT_GUIDE.md`).

```cypher
// All FACT edges for one execution
MATCH (s:Entity)-[f:FACT]->(o:Entity)
WHERE f.execution_id = $execution_id
RETURN s.name, f.relation, o.name, f.provenance, f.created_order
ORDER BY f.created_order;
```

```cypher
// All CLAIM edges (all iterations)
MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
WHERE c.execution_id = $execution_id
RETURN s.name, c.relation, o.name, c.label, c.iteration, c.sub_question_id, c.reason
ORDER BY c.sub_question_id, c.iteration;
```

```cypher
// CONTRADICTED only
MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
WHERE c.execution_id = $execution_id AND c.label = 'CONTRADICTED'
RETURN s.name, c.relation, o.name, c.conflicting_fact, c.reason;
```

## 9. What Neo4j does **not** do

- Does not generate answers or extract triples.
- Does not assign SUPPORTED / CONTRADICTED / NO_EVIDENCE (it only stores them).
- Does not decide RESOLVED / STALLED / UNRESOLVED_*.
- Does not compute the trusted evidence path verdict used by the runner (that is `resolve_evidence_path` in Python).
- Does not receive expected answers during inference.
