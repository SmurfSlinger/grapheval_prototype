# Manual action: Neo4j Browser screenshot (one step)

Automated Browser login was not completed safely in this environment (Neo4j
Browser requires credentials; password must not appear in screenshots, logs, or
deliverables). Capture this **one** file locally:

**Output path:** `research/neo4j_figures/rendered/neo4j_browser_apollo_execution.png`

**Execution ID (exact):** `apollo_hop_036__20260727T205852Z__c2d8a77c`

## Steps

1. Open Neo4j Browser at `http://localhost:7474` and connect with your usual
   local credentials (do not screenshot the connect form).
2. Paste and run:

```cypher
:param execution_id => 'apollo_hop_036__20260727T205852Z__c2d8a77c'
MATCH (s:Entity)-[r]->(o:Entity)
WHERE r.execution_id = $execution_id
  AND (
    (r:FACT AND s.name IN ['Neil Armstrong','Wapakoneta','Ohio','United States',
      'Washington, D.C.','Potomac River','Chesapeake Bay','Atlantic Ocean']
      AND o.name IN ['Neil Armstrong','Wapakoneta','Ohio','United States',
      'Washington, D.C.','Potomac River','Chesapeake Bay','Atlantic Ocean'])
    OR r:CLAIM
  )
RETURN s, r, o
```

3. Switch to graph view so Entity nodes and FACT/CLAIM edges are visible.
4. Save a PNG screenshot to the path above (crop out any password UI).
5. Optionally re-run `scripts/build_experiment_report_docx.py` so Figure M5 embeds.

Do **not** clear Neo4j, re-run Apollo, or invent graph data.
