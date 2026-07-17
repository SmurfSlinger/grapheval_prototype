# NHS WannaCry multi-hop benchmark

## Purpose

Provide a second, source-grounded 50-question multi-hop measurement set that
tests whether GraphEval generalizes beyond the Apollo/NASA domain into a
mission-critical healthcare and cybersecurity incident: the May 2017 WannaCry
ransomware attack and its documented impact on the NHS in England.

This benchmark is **not** a worldwide WannaCry encyclopedia. Unless a fact is
explicitly scoped otherwise in the trusted context, the factual scope is the
documented NHS England impact.

## Hop-count semantics

### Graph depth vs question-required reasoning depth

These are related but not identical:

| Concept | Meaning |
|---|---|
| **Graph depth** | Shortest directed distance in the trusted NHS graph from the benchmark `graph_root_entity` to an answer node. |
| **Question-required reasoning depth** | Shortest directed distance from `question_anchor_entities` that are **explicitly expressed in the question text** to the expected answer. |

Declared `hop_count` encodes **question-required reasoning depth**, not merely
root-to-answer topology.

Exact definition encoded in the dataset:

> `hop_count` = the minimum number of trusted directed graph edges needed to
> derive the expected answer from the question's `question_anchor_entities`,
> under allowed alias normalization, without outside knowledge.

The benchmark validates:

- graph topology (contiguous trusted path, no inflated repeats)
- question-anchor expression and detection (no silent root fallback)
- shortcut exposure (aliases, abbreviations, late-chain entities, answer locality cues)
- locality warnings (sentence-retrieval risk vs graph traversal)
- required reasoning depth (`shortest_distance_from_question_anchor == hop_count`)

Additional rules:

- Traversal is directed.
- Alias normalization: case-insensitive alias matching. A question must express
  an anchor entity; validation must not silently fall back to the graph root.
- `graph_root_entity` and `question_anchor_entities` are stored separately.
  They are often identical in this dataset (questions begin from the incident),
  but validation allows a non-root question anchor when the path and distance
  are computed from that detected anchor.
- Questions may paraphrase relations but must not use raw relation labels as
  quiz keys.
- Questions are self-contained: no unresolved discourse markers such as
  that/those/this/same/former/latter/earlier/later/previous, and no dangling
  “the listed …” references that depend on prior questions.
- A **shortcut** is any shorter directed path created by naming a non-anchor
  graph entity (including aliases/abbreviations) whose distance to the answer
  is shorter than `hop_count`, or by naming the final-edge subject / expected
  answer in questions with `hop_count > 1`.
- Semantically empty intermediate noun phrases used only to inflate path length
  are invalid.

Each question stores:

- `graph_root_entity`
- `question_anchor_entities`
- `reasoning_anchor_entities` as a backwards-compatible alias
- `anchor_detection` evidence showing which aliases were detected in the
  question text
- `hop_semantics: "minimum_required_path"`
- `shortcut_audit` with computed shortest distance, final-subject mention flag,
  late-chain shortcut flags, locality audit, and `human_review_status`

Committed audit artifacts:

- `data/test_sets/nhs_wannacry_multihop_50.audit.json`
- `docs/NHS_WANNACRY_HOP_AUDIT.md`
- `data/test_sets/nhs_wannacry_human_review.json` (external human review; empty
  until a human reviews)

Automated graph-distance / string checks cannot fully prove semantic necessity
or rule out world-knowledge answering. They are paired with generator
constraints and a pending external human-review manifest. The honest claim is:

> Every declared N-hop question requires following the intended reasoning chain
> from information explicitly present in the question itself, under the trusted
> graph and shortcut rules above.

Locality warnings and pending human review remain documented limitations.

## Why this incident

WannaCry connects:

- software vulnerability management (MS17-010 / SMBv1)
- legacy and unpatched systems
- network exposure and firewall hygiene
- national vs local NHS cyber responsibilities
- clinical service disruption and recovery
- incident response and kill-switch containment

## Authoritative sources

Primary sources (see `data/sources/nhs_wannacry/source_manifest.json`):

1. UK National Audit Office — *Investigation: WannaCry cyber attack and the NHS*
   (HC 414, 25 April 2018)
2. DHSC / NHS CIO — *Lessons learned review of the WannaCry Ransomware Cyber Attack*
   (1 February 2018)
3. CISA / US-CERT Alert TA17-132A — WannaCry technical indicators
4. Microsoft Security Bulletin MS17-010 (14 March 2017)

Full PDFs are preserved locally when retrieved but gitignored; manifests record
URLs, retrieval date, and SHA-256 hashes. Extracted text notes are committed for
reproducibility.

## Source ambiguities preserved

Do **not** collapse these NAO distinctions:

| Concept | Documented figure |
|---|---|
| Trusts affected (infected or disrupted) | at least 80 of 236 |
| Trusts infected and locked out | 34 (25 acute) |
| Trusts disrupted but not infected | 46 |
| Primary care / other NHS orgs infected | 603 (595 GP practices) |
| Identified cancelled appointments | 6,912 |
| Estimated cancelled appointments | about 19,494 |
| Majority infected devices | unpatched supported Windows 7 |
| XP share of estate on 12 May 2017 | about 5% (minority of infection issues) |

## Dataset

- Path: `data/test_sets/nhs_wannacry_multihop_50.json`
- Builder: `scripts/build_nhs_wannacry_dataset.py`
- Root: `WannaCry attack on the NHS`
- 50 questions, 5 per hop count 1–10
- Object-shaped facts with provenance
- Expected answers/paths are scoring metadata only and are not passed to inference

## Graph metrics (validated after hop-semantics redesign)

- Nodes: 88
- Directed facts: 87
- Relation types: 20 (most reused ≥2 times)
- Connected components: 1
- Root out-degree: 12
- Distinct 10-hop first edges: 5
- Shortcut audit: 0 unresolved shortcuts
- Ambiguous discourse markers remaining: 0
- Locality warnings: 3 (warnings are reported, not validation failures)
- Human review: 50 pending / not reviewed

## Validation / mock / real commands

```bash
python3 scripts/build_nhs_wannacry_dataset.py

python3 scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/nhs_wannacry_multihop_50.json \
  --validate-only

python3 scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/nhs_wannacry_multihop_50.json \
  --provider mock \
  --continue-on-error \
  --output /tmp/nhs-wannacry-mock.json \
  --summary /tmp/nhs-wannacry-mock.md

./scripts/run_nhs_wannacry_real_baseline.sh
```

Canonical real-baseline outputs:

- `results/nhs_wannacry_multihop_real_baseline.json`
- `results/nhs_wannacry_multihop_real_baseline.md`

## Verified repository results (this pass)

- Targeted backend: `.venv/bin/python -m pytest tests/test_nhs_wannacry_benchmark.py tests/test_apollo_multihop_test_set.py` → **31 passed**
- Apollo `--validate-only` → exit 0
- NHS WannaCry structural + question-anchor / shortcut / locality validation → exit 0
- NHS mock plumbing → rerun in verification pass
- Real Ollama NHS baseline → **not run** (Ollama unavailable; and hop-validity
  gate must remain green before any expensive real run)

## Known limitations

- Mock runs validate plumbing only; they are not accuracy evidence.
- Automated shortcut checks are necessary but not a full semantic proof.
- Human review is pending in `data/test_sets/nhs_wannacry_human_review.json`;
  no dataset row claims `manual_reviewed`.
- Locality warnings identify questions whose answer also appears in one
  relatively overlapping trusted-context sentence. They are audit warnings by
  default, not structural failures. Current warnings:
  `nhs_wannacry_h05_q05`, `nhs_wannacry_h06_q03`, `nhs_wannacry_h08_q02`.
- Branch-theme cues (“along the … chain”) disambiguate sibling root out-edges
  without naming late-chain entities; they are not raw relation labels, but they
  are still somewhat artificial natural-language scaffolding.
- Real Ollama baselines require local Ollama + Neo4j.
- Per-question timeouts remain in-process `SIGALRM`.
