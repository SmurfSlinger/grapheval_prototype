# NHS WannaCry multi-hop benchmark

## Purpose

Provide a second, source-grounded 50-question multi-hop measurement set that
tests whether GraphEval generalizes beyond the Apollo/NASA domain into a
mission-critical healthcare and cybersecurity incident: the May 2017 WannaCry
ransomware attack and its documented impact on the NHS in England.

This benchmark is **not** a worldwide WannaCry encyclopedia. Unless a fact is
explicitly scoped otherwise in the trusted context, the factual scope is the
documented NHS England impact.

Present this set as:

> a source-grounded root-to-answer graph-depth and path-following benchmark

Do not claim stronger semantics than the implementation supports.

## Hop-count semantics

### Honest framing

| Concept | Meaning |
|---|---|
| **Expected path length** | Length of the designed contiguous trusted directed path stored as `expected_path`. |
| **Root-to-answer graph depth** | Shortest directed distance from the benchmark `graph_root_entity` to the answer. |
| **Anchor distance** | Shortest directed distance from `question_anchor_entities` detected in the question text to the answer. |
| **Late-path exposure** | Whether the question names a late-chain entity, final-edge subject, or expected answer. |
| **Locality risk** | Whether a trusted-context sentence may allow local retrieval without full path following. |

In this dataset, questions start from the incident root, so declared `hop_count`
equals expected path length, root distance, and anchor distance under current
validation. That is **designed graph depth / path length**, not proof of
minimum cognitive reasoning depth.

Exact label encoded per question:

```json
"hop_semantics": "designed_root_to_answer_graph_depth"
```

The benchmark validates:

- graph topology (contiguous trusted path, no inflated repeats)
- question-anchor expression and detection (no silent root fallback)
- shortcut exposure (aliases, abbreviations, late-chain entities, answer locality cues)
- locality warnings (sentence-retrieval risk vs graph traversal)
- designed depth consistency (`expected_path_length`, root distance, and anchor distance match `hop_count`)

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
- `hop_semantics: "designed_root_to_answer_graph_depth"`
- `shortcut_audit` with expected path length, root distance, anchor distance,
  final-subject / late-chain flags, locality audit, `generator_checked: true`,
  and `human_review_status: "pending"`

Committed audit artifacts:

- `data/test_sets/nhs_wannacry_multihop_50.audit.json`
- `docs/NHS_WANNACRY_HOP_AUDIT.md`
- `data/test_sets/nhs_wannacry_human_review.json` (external human review; empty
  until a human reviews)

Automated graph-distance / string checks cannot fully prove semantic necessity
or rule out world-knowledge answering. They are paired with generator
constraints and a pending external human-review manifest. The honest claim is:

> Every declared N-hop question has a designed contiguous root-to-answer path of
> length N in the trusted graph, with self-contained wording and automated
> shortcut / discourse checks. Graph depth is not automatically equivalent to
> human reasoning depth.

Locality warnings and pending human review remain documented limitations.

## Why this incident

WannaCry connects:

- software vulnerability management (MS17-010 / SMBv1)
- legacy and unpatched systems
- network exposure and firewall hygiene
- national vs local NHS cyber responsibilities
- clinical service disruption and recovery
- incident response and kill-switch containment

Those themes exercise GraphEval’s FACT/CLAIM separation on a second domain
without requiring Apollo-specific knowledge.

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

## Dataset location

```text
data/test_sets/nhs_wannacry_multihop_50.json
```

- Builder: `scripts/build_nhs_wannacry_dataset.py`
- Root: `WannaCry attack on the NHS`
- 50 questions, 5 per hop count 1–10
- Object-shaped facts with provenance
- Expected answers/paths are scoring metadata only and are not passed to inference

## Graph metrics

- Nodes: 88
- Directed facts: 87
- Relation types: 20 (most reused ≥2 times)
- Connected components: 1
- Root out-degree: 12
- Distinct 10-hop first edges: 5
- Shortcut audit: 0 unresolved shortcuts
- Ambiguous discourse markers remaining: 0
- Locality warnings: 3 (warnings are reported, not validation failures)
- Human review: 50 pending with `generator_checked: true`

Regenerate from the committed builder:

```bash
python scripts/build_nhs_wannacry_dataset.py
```

Validate without an LLM:

```bash
python scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/nhs_wannacry_multihop_50.json \
  --validate-only
```

Mock plumbing (not accuracy):

```bash
python scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/nhs_wannacry_multihop_50.json \
  --provider mock \
  --continue-on-error \
  --output /tmp/nhs-wannacry-mock.json \
  --summary /tmp/nhs-wannacry-mock.md
```

Real baseline wrapper (optional; requires Ollama + Neo4j):

```bash
./scripts/run_nhs_wannacry_real_baseline.sh
```

Bounded smoke:

```bash
./scripts/run_nhs_wannacry_real_baseline.sh \
  --ids nhs_wannacry_h01_q01 \
  --timeout-per-question 600
```

Canonical real-baseline outputs:

- `results/nhs_wannacry_multihop_real_baseline.json`
- `results/nhs_wannacry_multihop_real_baseline.md`

## Integrity notes

- Trusted FACTS and answer CLAIMS remain separate.
- Scoring metadata (`expected_path`, `expected_answer`, fact IDs) must not appear
  in trusted context prose.
- No expected answers or paths are passed into inference.
- Mock failures validate runner plumbing only.
- The generator sets `generator_checked: true` and `human_review_status: "pending"`;
  no dataset row claims `manual_reviewed`.

## Known limitations

- Mock runs validate plumbing only; they are not accuracy evidence.
- Automated shortcut checks are necessary but not a full semantic proof.
- Graph depth / expected path length is not automatically equivalent to human
  reasoning depth.
- Human review is pending in `data/test_sets/nhs_wannacry_human_review.json`;
  no dataset row claims `manual_reviewed`.
- Locality warnings identify questions whose answer also appears in one
  relatively overlapping trusted-context sentence. They are audit warnings by
  default, not structural failures. Current warnings:
  `nhs_wannacry_h05_q05`, `nhs_wannacry_h07_q01`, `nhs_wannacry_h08_q02`.
- Branch-theme cues (“along the … chain”) disambiguate sibling root out-edges
  without naming late-chain entities; they are not raw relation labels, but they
  are still somewhat artificial natural-language scaffolding.
- Real Ollama baselines require local Ollama + Neo4j and remain optional
  follow-up work for professor-testable readiness.
- Per-question timeouts remain in-process `SIGALRM`.
