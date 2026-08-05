# Neo4j persistence

```{figure} ../diagrams/rendered/neo4j_logical_schema.svg
:alt: Entity nodes with FACT and CLAIM relationships

Exact labels and primary properties from neo4j_store.py.
```

## Roles

Neo4j persists and returns execution-scoped graph data. It does **not** label
claims, decide stop reasons, or call the LLM.

## Write patterns

| Edge | Pattern | When |
|---|---|---|
| `:FACT` | `MERGE` | Context extract; working additions |
| `:CLAIM` | `CREATE` (append) | After each sub-question, for every iteration in history |

Earlier-iteration CLAIMs remain unless the execution’s entities are deleted.

## Key API

- `Neo4jStore.store_kgc_facts` / `get_kgc_facts`
- `Neo4jStore.store_kgc_claims` / `get_claims`
- `Neo4jStore.clear_execution` / `clear_all`
- Enabled wrappers: `store_*_if_enabled`, `read_kgc_facts_if_enabled`

Full property tables and Cypher: `research/NEO4J_DATA_MODEL.md`.  
Screenshot queries: `research/NEO4J_SCREENSHOT_GUIDE.md`.
