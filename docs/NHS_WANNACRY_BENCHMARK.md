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

Declared `hop_count` is **not** merely root-to-answer graph depth.

Exact definition encoded in the dataset:

> `hop_count` = the minimum number of trusted directed graph edges needed to
> derive the expected answer from the question's `reasoning_anchor_entities`,
> under allowed alias normalization, without outside knowledge.

Additional rules:

- Traversal is directed.
- Alias normalization: case-insensitive exact entity-string match; ordinary
  linguistic coreference to the incident root is allowed when the question
  refers to WannaCry / the NHS attack.
- Questions may paraphrase relations but must not use raw relation labels as
  quiz keys.
- A **shortcut** is any shorter directed path from an explicit question anchor
  to the answer, or naming the final-edge subject in questions with
  `hop_count > 1`.
- Semantically empty intermediate noun phrases used only to inflate path length
  are invalid.

Each question stores:

- `reasoning_anchor_entities`
- `hop_semantics: "minimum_required_path"`
- `shortcut_audit` with computed shortest distance, final-subject mention flag,
  and manual review status

Committed audit artifacts:

- `data/test_sets/nhs_wannacry_multihop_50.audit.json`
- `docs/NHS_WANNACRY_HOP_AUDIT.md`

Automated graph-distance / string checks cannot fully prove semantic necessity.
They are paired with generator constraints and manual review metadata. The
dataset should be described as supporting 1–10-hop measurement only while the
shortcut audit reports zero unresolved shortcuts.

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

## Validation / mock / real commands

```bash
python scripts/build_nhs_wannacry_dataset.py

python scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/nhs_wannacry_multihop_50.json \
  --validate-only

python scripts/run_multihop_benchmark.py \
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

- Backend: `pytest tests/` → **255 passed**
- Frontend: `npm run build` → success
- Apollo `--validate-only` → exit 0
- NHS WannaCry structural + shortcut/minimal-path validation → exit 0
- NHS mock plumbing → 50 terminal error records, 0 completions (plumbing only)
- Real Ollama NHS baseline → **not run** (Ollama unavailable; and hop-validity
  gate must remain green before any expensive real run)

## Known limitations

- Mock runs validate plumbing only; they are not accuracy evidence.
- Automated shortcut checks are necessary but not a full semantic proof.
- Real Ollama baselines require local Ollama + Neo4j.
- Per-question timeouts remain in-process `SIGALRM`.
