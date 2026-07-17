# NHS WannaCry source bundle

This directory contains the preserved local source extracts used for the NHS WannaCry multihop benchmark.

## Committed files

- `nao_wannacry_full.extracted.txt` - extracted text from the UK National Audit Office report *Investigation: WannaCry cyber attack and the NHS* (HC 414, 25 April 2018).
- `nao_wannacry_summary.extracted.txt` - extracted NAO summary pages for quick audit of headline findings.
- `dhsc_lessons_learned.extracted.txt` - extracted text from the DHSC/NHS CIO *Lessons learned review of the WannaCry Ransomware Cyber Attack* (1 February 2018).
- `cisa_ta17_132a.extracted.txt` - extracted text from US-CERT/CISA Alert TA17-132A.
- `ms17_010.html` - preserved Microsoft Learn HTML for MS17-010.
- `hashes.sha256` - SHA-256 checksums for the locally preserved PDFs and HTML.
- `source_manifest.json` - structured source metadata used by the benchmark.
- `fact_inventory.json` - source-grounded fact inventory with provenance for each benchmark graph fact.

## Gitignored originals

The original PDF publications are intentionally not committed. This directory's `.gitignore` ignores `*.pdf` while keeping extracted text, manifest metadata, and checksums under version control. To verify a local PDF copy, compare it with the corresponding digest in `hashes.sha256`.

## Research-integrity note

The benchmark facts should be maintained only from the authoritative local sources in this directory. For NHS impact counts, prefer the NAO report and keep these distinctions separate: 34 infected locked trusts, 46 disrupted but not infected trusts, at least 80 affected trusts out of 236, 595 infected GP practices, and 603 infected primary-care and other NHS organisations.
