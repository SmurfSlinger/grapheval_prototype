# Limitations

- No controlled no-feedback or generic-self-correction baseline.
- Official Apollo sample: single model (`llama3.1:8b`), single domain, five
  questions per designed depth.
- Official rows generally lack per-question debug JSONL (`debug_log_path: null`),
  so intermediate answers/labels for multi-revision successes (e.g. hop_036) are
  not reconstructable from the aggregate file alone.
- Repeatability across three temperature-0 runs was byte-identical on compared
  outputs on fixed hardware; that does not prove general determinism under changed
  environments.
- Decomposition is optional instrumentation, not a factorial experimental arm.
- Neo4j state from official runs was not retained as screenshot artifacts; Browser
  captures require a careful reload or documentation re-run (see screenshot guide).
- README Mermaid diagrams are simplified conceptual views, not exact schemas.
