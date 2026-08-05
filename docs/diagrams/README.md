# Diagram sources

Editable Mermaid sources for the methodology revision.

| Source | Rendered asset | View type |
|---|---|---|
| `grapheval_algorithm_overview.mmd` | `../rendered/grapheval_algorithm_overview.svg` | Simplified conceptual |
| `grapheval_kg_iteration_walkthrough.mmd` | `../rendered/grapheval_kg_iteration_walkthrough.svg` | Simplified conceptual; WannaCry real execution |
| `fact_claim_contradiction_example.mmd` | `../rendered/fact_claim_contradiction_example.svg` | Exact triples/reason; simplified layout |
| `neo4j_logical_schema.mmd` | `../rendered/neo4j_logical_schema.svg` | Exact labels/types/primary properties |

## Re-render (optional)

If `@mermaid-js/mermaid-cli` is installed:

```bash
mmdc -i docs/diagrams/source/grapheval_algorithm_overview.mmd \
     -o docs/diagrams/rendered/grapheval_algorithm_overview.svg
```

The checked-in SVGs were authored to match these sources when `mmdc` was unavailable in the documentation environment.
