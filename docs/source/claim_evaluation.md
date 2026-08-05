# Claim evaluation

Implemented by `GraphComparator.compare_claims` in
`src/pipeline/graph_comparator.py`.

## Labels

| Label | Meaning in code |
|---|---|
| SUPPORTED | Matches a trusted FACT under legacy exact match or target-frame rules |
| CONTRADICTED | Conflicts with a FACT (same relation / family, incompatible object; plus polarity/engine helpers) |
| NO_EVIDENCE | No supporting or conflicting match under active rules |

```{figure} ../diagrams/rendered/fact_claim_contradiction_example.svg
:alt: FACT retained while CLAIM labeled CONTRADICTED

WannaCry qualitative contradiction example.
```

Labels are calculated in Python and may be stored on `:CLAIM` relationships.
