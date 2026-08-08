# Figure captions and provenance

Generated (UTC): 2026-08-07T04:48:17.819110+00:00

**Question ID:** `apollo_hop_036`
**Execution ID (official July 27):** `apollo_hop_036__20260727T205852Z__c2d8a77c`

All rendered figures are controlled-layout visualizations of relationships queried from the live Neo4j database. They are **not** Neo4j Browser screenshots unless explicitly named `neo4j_browser_apollo_execution`.

## Visual conventions

- FACT: green, solid
- CLAIM SUPPORTED: blue, solid
- CLAIM CONTRADICTED: red, solid
- CLAIM NO_EVIDENCE: orange, dashed

## apollo_trusted_fact_graph

- **Figure title:** Trusted FACT evidence path for Apollo hop_036
- **Files:** `research/neo4j_figures/rendered/apollo_trusted_fact_graph.png`, `research/neo4j_figures/rendered/apollo_trusted_fact_graph.svg`, source `research/neo4j_figures/source/apollo_trusted_fact_graph.dot`
- **Execution ID:** `apollo_hop_036__20260727T205852Z__c2d8a77c`
- **Question ID:** `apollo_hop_036`
- **Iteration filter:** `None`
- **Sub-question filter:** `None`

### Cypher query

```cypher
:param execution_id => 'apollo_hop_036__20260727T205852Z__c2d8a77c'
:param path_names => ["Neil Armstrong", "Wapakoneta", "Ohio", "United States", "Washington, D.C.", "Potomac River", "Chesapeake Bay", "Atlantic Ocean"]
MATCH (s:Entity)-[f:FACT]->(o:Entity)
WHERE f.execution_id = $execution_id
  AND s.name IN $path_names AND o.name IN $path_names
RETURN elementId(f) AS rel_id, s.name AS subject, f.relation AS relation, o.name AS object
ORDER BY f.created_order
```

**What to notice:** A single directed chain of green FACT edges from Neil Armstrong through geographic entities to Atlantic Ocean.

**Conclusion supported:** GraphEval stores trusted context as FACT relationships before claim evaluation; the 7-edge path needed for evidence-path resolution is present in Neo4j.

**Does not prove:** Does not show CLAIMs, iterations, or that this path alone caused RESOLVED; pipeline resolution also requires claim labels and target satisfaction.

## apollo_initial_claim_state

- **Figure title:** Initial CLAIM state (iteration 0) over trusted FACTs
- **Files:** `research/neo4j_figures/rendered/apollo_initial_claim_state.png`, `research/neo4j_figures/rendered/apollo_initial_claim_state.svg`, source `research/neo4j_figures/source/apollo_initial_claim_state.dot`
- **Execution ID:** `apollo_hop_036__20260727T205852Z__c2d8a77c`
- **Question ID:** `apollo_hop_036`
- **Iteration filter:** `0`
- **Sub-question filter:** `1`

### Cypher query

```cypher
:param execution_id => 'apollo_hop_036__20260727T205852Z__c2d8a77c'
:param path_names => ["Neil Armstrong", "Wapakoneta", "Ohio", "United States", "Washington, D.C.", "Potomac River", "Chesapeake Bay", "Atlantic Ocean"]
MATCH (s:Entity)-[r]->(o:Entity)
WHERE r.execution_id = $execution_id
  AND (
    (r:FACT AND s.name IN $path_names AND o.name IN $path_names)
    OR (r:CLAIM AND r.iteration = 0 AND r.sub_question_id = 1)
  )
RETURN type(r) AS rel_type, elementId(r) AS rel_id, s.name AS subject,
       r.relation AS relation, o.name AS object,
       r.label AS label, r.iteration AS iteration, r.sub_question_id AS sub_question_id
```

**What to notice:** Iteration-0 CLAIMs overlay the FACT path. One CLAIM is NO_EVIDENCE: Washington, D.C. — has_capital_in → United States (direction reversed vs FACT).

**Conclusion supported:** Earlier-iteration CLAIMs coexist in Neo4j with later ones (CREATE append). Unsupported structure is labeled NO_EVIDENCE rather than written as FACT.

**Does not prove:** Does not show the free-text answer for iteration 0 (answer text is not stored on Neo4j relationships).

## apollo_feedback_problem

- **Figure title:** NO_EVIDENCE CLAIM next to the trusted capital FACT
- **Files:** `research/neo4j_figures/rendered/apollo_feedback_problem.png`, `research/neo4j_figures/rendered/apollo_feedback_problem.svg`, source `research/neo4j_figures/source/apollo_feedback_problem.dot`
- **Execution ID:** `apollo_hop_036__20260727T205852Z__c2d8a77c`
- **Question ID:** `apollo_hop_036`
- **Iteration filter:** `0`
- **Sub-question filter:** `1`

### Cypher query

```cypher
:param execution_id => 'apollo_hop_036__20260727T205852Z__c2d8a77c'
:param path_names => ["Neil Armstrong", "Wapakoneta", "Ohio", "United States", "Washington, D.C.", "Potomac River", "Chesapeake Bay", "Atlantic Ocean"]
MATCH (s:Entity)-[r]->(o:Entity)
WHERE r.execution_id = $execution_id
  AND (
    (r:CLAIM AND r.iteration = 0 AND s.name = 'Washington, D.C.'
     AND r.relation = 'has_capital_in' AND o.name = 'United States')
    OR (r:FACT AND (
         (s.name = 'United States' AND r.relation = 'has_capital_in' AND o.name = 'Washington, D.C.')
      OR (s.name IN ['Ohio','United States','Washington, D.C.','Potomac River']
          AND o.name IN ['Ohio','United States','Washington, D.C.','Potomac River'])
    ))
  )
RETURN type(r) AS rel_type, elementId(r) AS rel_id, s.name AS subject,
       r.relation AS relation, o.name AS object, r.label AS label, r.iteration AS iteration
```

**What to notice:** Green FACT United States — has_capital_in → Washington, D.C. versus orange dashed CLAIM Washington, D.C. — has_capital_in → United States.

**Conclusion supported:** Graph comparison can reject a reversed capital relation as NO_EVIDENCE when no matching FACT exists for that subject/relation/object.

**Does not prove:** Does not prove CONTRADICTED labeling (this stored edge is NO_EVIDENCE). Does not show the feedback string sent to the reviser LLM.

## apollo_revised_claim_state

- **Figure title:** Revised CLAIM state (iteration 1)
- **Files:** `research/neo4j_figures/rendered/apollo_revised_claim_state.png`, `research/neo4j_figures/rendered/apollo_revised_claim_state.svg`, source `research/neo4j_figures/source/apollo_revised_claim_state.dot`
- **Execution ID:** `apollo_hop_036__20260727T205852Z__c2d8a77c`
- **Question ID:** `apollo_hop_036`
- **Iteration filter:** `1`
- **Sub-question filter:** `1`

### Cypher query

```cypher
:param execution_id => 'apollo_hop_036__20260727T205852Z__c2d8a77c'
:param path_names => ["Neil Armstrong", "Wapakoneta", "Ohio", "United States", "Washington, D.C.", "Potomac River", "Chesapeake Bay", "Atlantic Ocean"]
MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
WHERE c.execution_id = $execution_id AND c.iteration = 1 AND c.sub_question_id = 1
OPTIONAL MATCH (fs:Entity)-[f:FACT]->(fo:Entity)
WHERE f.execution_id = $execution_id
  AND (fs.name = s.name OR fo.name = o.name OR fs.name = o.name OR fo.name = s.name)
  AND fs.name IN $path_names AND fo.name IN $path_names
RETURN elementId(c) AS claim_id, s.name AS subject, c.relation AS relation, o.name AS object,
       c.label AS label, c.iteration AS iteration,
       elementId(f) AS fact_id, fs.name AS fact_s, f.relation AS fact_r, fo.name AS fact_o
```

**What to notice:** Iteration-1 CLAIMs: Potomac/DC edges SUPPORTED; Atlantic Ocean — opens_into → Chesapeake Bay is NO_EVIDENCE (reversed vs FACT).

**Conclusion supported:** CLAIM structure changed across iterations while FACT edges remained; a new NO_EVIDENCE defect appears when the model reverses opens_into.

**Does not prove:** Does not claim iteration 1 was terminal; final iteration is 2.

## apollo_final_supported_state

- **Figure title:** Final SUPPORTED CLAIM state (iteration 2)
- **Files:** `research/neo4j_figures/rendered/apollo_final_supported_state.png`, `research/neo4j_figures/rendered/apollo_final_supported_state.svg`, source `research/neo4j_figures/source/apollo_final_supported_state.dot`
- **Execution ID:** `apollo_hop_036__20260727T205852Z__c2d8a77c`
- **Question ID:** `apollo_hop_036`
- **Iteration filter:** `2`
- **Sub-question filter:** `1`

### Cypher query

```cypher
:param execution_id => 'apollo_hop_036__20260727T205852Z__c2d8a77c'
:param path_names => ["Neil Armstrong", "Wapakoneta", "Ohio", "United States", "Washington, D.C.", "Potomac River", "Chesapeake Bay", "Atlantic Ocean"]
MATCH (s:Entity)-[r]->(o:Entity)
WHERE r.execution_id = $execution_id
  AND (
    (r:FACT AND s.name IN $path_names AND o.name IN $path_names)
    OR (r:CLAIM AND r.iteration = 2 AND r.sub_question_id = 1)
  )
RETURN type(r) AS rel_type, elementId(r) AS rel_id, s.name AS subject,
       r.relation AS relation, o.name AS object, r.label AS label, r.iteration AS iteration
```

**What to notice:** All iteration-2 CLAIMs are SUPPORTED, including terminal Chesapeake Bay — opens_into → Atlantic Ocean on the trusted path.

**Conclusion supported:** Stored Neo4j state is consistent with a successful revision ending at Atlantic Ocean for this execution.

**Does not prove:** Does not by itself prove the textual exact-match score or stop reason; those come from the result JSON, not Neo4j edge labels alone.

## apollo_iteration_sequence

- **Figure title:** Multi-panel iteration sequence for Apollo hop_036
- **Files:** `research/neo4j_figures/rendered/apollo_iteration_sequence.png`, `research/neo4j_figures/rendered/apollo_iteration_sequence.svg`, source `research/neo4j_figures/source/apollo_iteration_sequence.dot`
- **Execution ID:** `apollo_hop_036__20260727T205852Z__c2d8a77c`
- **Question ID:** `apollo_hop_036`
- **Iteration filter:** `0-2`
- **Sub-question filter:** `1`

### Cypher query

```cypher
:param execution_id => 'apollo_hop_036__20260727T205852Z__c2d8a77c'
:param path_names => ["Neil Armstrong", "Wapakoneta", "Ohio", "United States", "Washington, D.C.", "Potomac River", "Chesapeake Bay", "Atlantic Ocean"]
MATCH (s:Entity)-[r]->(o:Entity)
WHERE r.execution_id = $execution_id
  AND (
    (r:FACT AND s.name IN $path_names AND o.name IN $path_names)
    OR (r:CLAIM AND r.sub_question_id = 1)
  )
RETURN type(r) AS rel_type, elementId(r) AS rel_id, s.name AS subject,
       r.relation AS relation, o.name AS object, r.label AS label,
       r.iteration AS iteration, r.sub_question_id AS sub_question_id
ORDER BY type(r), r.iteration, s.name
```

**What to notice:** Left-to-right: trusted FACTs → iter-0 CLAIMs → focused feedback problem → iter-1 CLAIMs → iter-2 final SUPPORTED claims.

**Conclusion supported:** A professor-readable story of graph-based feedback using only relationships actually stored for the July 27 official execution.

**Does not prove:** Does not reconstruct omitted answer text; panels are labeled from CLAIM/FACT state only.

## neo4j_browser_apollo_execution

- **Figure title:** Neo4j Browser proof — Apollo hop_036 FACT+CLAIM subset
- **File:** `research/neo4j_figures/rendered/neo4j_browser_apollo_execution.png`
- **Execution ID:** `apollo_hop_036__20260727T205852Z__c2d8a77c`

### Cypher query (run in Neo4j Browser)

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

**What to notice:** Live Browser canvas showing Entity nodes with FACT and CLAIM relationships for this execution_id.

**Conclusion supported:** The rendered Graphviz/matplotlib figures are backed by relationships that exist in the running Neo4j database.

**Does not prove:** Algorithm correctness; only storage presence.

**Status:** Not yet captured. Manual author action (only remaining screenshot step):

See `research/neo4j_figures/MANUAL_BROWSER_SCREENSHOT.md`. Summary:

1. Open Neo4j Browser at `http://localhost:7474` (already authenticated locally).
2. Paste the Cypher above and run it.
3. Expand the graph view so FACT and CLAIM edges are visible.
4. Save a PNG screenshot to `research/neo4j_figures/rendered/neo4j_browser_apollo_execution.png`.
5. Do not include passwords in the screenshot or filename.

