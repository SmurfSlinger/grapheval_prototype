# NHS WannaCry multi-hop benchmark

## Purpose

Provide a second, source-grounded 50-question multi-hop measurement set that
tests whether GraphEval generalizes beyond the Apollo/NASA domain into a
mission-critical healthcare and cybersecurity incident: the May 2017 WannaCry
ransomware attack and its documented impact on the NHS in England.

This benchmark is **not** a worldwide WannaCry encyclopedia. Unless a fact is
explicitly scoped otherwise in the trusted context, the factual scope is the
documented NHS England impact.

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

Organizations contacting the WannaCry domain after the kill-switch are **not**
automatically counted as infected.

## Dataset

- Path: `data/test_sets/nhs_wannacry_multihop_50.json`
- Root: `WannaCry attack on the NHS`
- 50 questions, 5 per hop count 1–10
- Object-shaped facts with provenance (`source_id`, page/section, paraphrase)
- Expected answers/paths are scoring metadata only and are not passed to inference

## Validation / mock / real commands

```bash
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

Resume requires these exact paths. The wrapper rejects overrides of
`--provider`, `--test-set`, `--output`, and `--summary`.

## Verified repository results (this branch)

- Backend: `pytest tests/` → **246 passed**
- Frontend: `npm run build` → success
- Apollo `--validate-only` → exit 0
- NHS WannaCry `--validate-only` → exit 0
- NHS mock plumbing → 50 terminal error records, 0 completions (plumbing only)
- Real Ollama NHS baseline → **not run** (Ollama unavailable in this environment)

## Graph metrics (validated)

- Nodes: 147
- Directed facts: 161
- Relation types: 29
- Connected components: 1
- Root out-degree: 12
- Distinct 10-hop first edges: 5

## Known limitations

- Mock runs validate plumbing only; they are not accuracy evidence.
- Real Ollama baselines require local Ollama + Neo4j and are environment-dependent.
- Per-question timeouts remain in-process `SIGALRM` (see Apollo/timeout docs).
