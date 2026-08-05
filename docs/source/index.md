# GraphEval Prototype Documentation

```{toctree}
:maxdepth: 2
:caption: Architecture

project_overview
research_problem
algorithm_overview
triple_and_graph_model
neo4j_persistence
execution_lifecycle
claim_evaluation
feedback_and_revision
target_and_path_validation
module_map
```

```{toctree}
:maxdepth: 2
:caption: Reference

api_reference
benchmark_and_analysis
trace_format
reproducibility
limitations
```

## What this site is

Handwritten pages explain how the research instrument works and map concepts to
modules. Autodoc pages list selected Python APIs; they do not replace the
architecture chapters.

Frozen inference commit for the official experiment:
`b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`.

## Build

From the repository root (after `pip install -r docs/requirements-docs.txt`):

```bash
sphinx-build -b html docs/source docs/build/html
```

Generated HTML under `docs/build/` is not committed.
