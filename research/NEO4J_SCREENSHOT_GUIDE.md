# Neo4j Screenshot Guide

**Audience:** Kyler, capturing legitimate Neo4j Browser screenshots for the Experiment Report.  
**Schema source:** `src/storage/neo4j_store.py`, `research/NEO4J_DATA_MODEL.md`  
**Selected execution (qualitative, fully traced):**  
`nhs_wannacry_h10_q01__20260727T214622Z__4adc0f88`

> Important: Official Apollo 50-question runs did not leave durable Neo4j state in the
> research artifacts (graphs were execution-scoped and cleared between questions).
> To capture these screenshots you must either (a) re-load triples into Neo4j from the
> preserved debug JSONL / result row using a **documentation-only** import that does
> not change inference code, or (b) re-run that single WannaCry question on frozen
> commit `b9608d0` with Neo4j enabled and note the new `execution_id` if it differs.
> If you re-run, substitute the live `execution_id` into every query below and record
> it next to the screenshot. Do not treat a re-run as part of the Apollo n=50 sample.

Set the parameter once in Neo4j Browser:

```cypher
:param execution_id => 'nhs_wannacry_h10_q01__20260727T214622Z__4adc0f88'
```

Optional styling (Neo4j Browser; ignore if unsupported):

```
:style
node.Entity {
  color: #FFF8E7;
  border-color: #8A6D3B;
  text-color-internal: #222222;
}
relationship.FACT {
  color: #3B7A3B;
  shaft-width: 2px;
}
relationship.CLAIM {
  color: #8A3B3B;
  shaft-width: 2px;
}
```

---

## Query 1 — all FACT relationships

**Supports:** Report §2.3; Figure M1 / M4 state 1.

```cypher
MATCH (s:Entity)-[f:FACT]->(o:Entity)
WHERE f.execution_id = $execution_id
RETURN s, f, o
ORDER BY f.created_order
```

**Expected visible:** `:Entity` nodes for subjects/objects present in context FACTs,
including at least  
`Microsoft Security Bulletin MS17-010` —`supplied_correction_to_vulnerability`→  
`how SMBv1 handled crafted requests` (plus other FACTs from the same extraction).  
Relationship type **FACT** only.

**Suggested Browser caption:**  
“Figure: Trusted FACT graph for WannaCry execution …4adc0f88 (Query 1).”

---

## Query 2 — all CLAIM relationships

**Supports:** Report §2.3, §2.8; Figure M4.

```cypher
MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
WHERE c.execution_id = $execution_id
RETURN s, c, o
ORDER BY c.sub_question_id, c.iteration
```

**Expected visible:** Multiple **CLAIM** edges with properties `label`, `iteration`,
`sub_question_id`, `reason`. Both SUPPORTED and CONTRADICTED / NO_EVIDENCE claims
from different iterations may appear (CREATE append).  

**Suggested caption:**  
“Figure: All CLAIM edges (all iterations) for …4adc0f88 (Query 2).”

---

## Query 3 — combined FACT and CLAIM view

**Supports:** Report §2.3; Figure M4.

```cypher
MATCH (s:Entity)-[r]->(o:Entity)
WHERE r.execution_id = $execution_id AND type(r) IN ['FACT', 'CLAIM']
RETURN s, r, o
```

**Expected visible:** Same entity set with both green FACT and red CLAIM edges
(depending on styling). FACTs remain distinct from CLAIMs.

**Suggested caption:**  
“Figure: Combined FACT + CLAIM graph for …4adc0f88 (Query 3).”

---

## Query 4 — one sub-question / iteration filter

**Supports:** Report §2.6–2.8; Figure M4. Schema supports `sub_question_id` and `iteration` on CLAIM.

```cypher
MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
WHERE c.execution_id = $execution_id
  AND c.sub_question_id = 2
  AND c.iteration = 1
RETURN s, c, o, c.label, c.reason
```

**Expected visible:** Q2 iteration-1 claims from the WannaCry trace (SUPPORTED MS17-010
claims in the preserved comparison). If iteration indexing in a re-run differs,
first list distinct pairs:

```cypher
MATCH ()-[c:CLAIM]->()
WHERE c.execution_id = $execution_id
RETURN DISTINCT c.sub_question_id AS sq, c.iteration AS iter, count(*) AS n
ORDER BY sq, iter
```

**Suggested caption:**  
“Figure: CLAIM edges for sub-question 2, iteration 1 (Query 4).”

---

## Query 5 — trusted evidence path (FACT chain)

**Supports:** Report §2.7; Apollo `apollo_hop_036` path is documented on the result row,
but that execution’s Neo4j graph was not preserved. For the WannaCry execution, show
the trusted MS17-010 FACT (path completeness failed overall; this query shows the
FACT store used by Python path checks, not a Cypher shortestPath claim).

```cypher
MATCH (s:Entity)-[f:FACT]->(o:Entity)
WHERE f.execution_id = $execution_id
  AND s.name CONTAINS 'MS17-010'
RETURN s, f, o, f.relation, f.provenance
```

For Apollo hop_036 **after a documentation-only reload** of that execution’s FACTs
(if performed), the expected FACT chain endpoints are listed on the official result
row (`Neil Armstrong` … `Atlantic Ocean`). Do not invent missing Neo4j state.

**Suggested caption:**  
“Figure: Trusted FACT evidence for MS17-010 (Query 5).”

---

## Query 6 — contradiction example

**Supports:** Report §2.5; Figure M3.

```cypher
MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
WHERE c.execution_id = $execution_id
  AND c.label = 'CONTRADICTED'
RETURN s.name AS subject,
       c.relation AS relation,
       o.name AS object,
       c.conflicting_fact AS conflicting_fact,
       c.reason AS reason,
       c.iteration AS iteration,
       c.sub_question_id AS sub_question_id
```

Graph view of the same:

```cypher
MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
WHERE c.execution_id = $execution_id AND c.label = 'CONTRADICTED'
RETURN s, c, o
```

**Expected visible / table rows:** Over-expanded MS17-010 objects labeled CONTRADICTED
with `conflicting_fact` referencing  
`Microsoft Security Bulletin MS17-010 -- supplied_correction_to_vulnerability --> how SMBv1 handled crafted requests`  
(serialized form may use `--` / `-->` as stored by `_create_kgc_claim`).

**Suggested caption:**  
“Figure: CONTRADICTED CLAIMs vs retained FACT (Query 6).”

---

## Report placeholder checklist

| Placeholder in report | Query |
|---|---|
| Screenshot Guide Query 1 | Query 1 |
| Screenshot Guide Query 2 | Query 2 |
| Screenshot Guide Query 3 | Query 3 |
| Screenshot Guide Query 4 | Query 4 |
| Screenshot Guide Query 5 | Query 5 |
| Screenshot Guide Query 6 | Query 6 |
