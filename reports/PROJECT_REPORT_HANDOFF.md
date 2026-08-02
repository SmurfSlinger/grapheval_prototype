# Project Report / Slide Deck Handoff

Purpose: map the completed research (Experiment Report + analysis artifacts) into the
professor's Research Project Report structure for the later project report, which may
be submitted as a slide deck. The original
`Research Project Report Template-verJuly102026.docx` was not available in this
environment; the 8-section structure below follows the specified template outline.
Do not build the deck from memory — every number should come from
`results/research/grapheval_final_experiment_analysis.json` and every trace claim
from `research/REPRESENTATIVE_TRACE_CASES.md`.

## 1. Introduction

- 1–2 slides. The problem: LLM answers mix supported/contradicted/unsupported
  statements; final-answer scoring hides how answers change during correction.
- One slide with the FACT vs CLAIM definitions and a single triple example
  (`Microsoft Security Bulletin MS17-010 — supplied_correction_to_vulnerability →
  how SMBv1 handled crafted requests`). Reuse Experiment Report §1.1 wording.
- State the four descriptive RQs (Experiment Report §1.2).

## 2. Background

- GraphEval-style verification of answers as knowledge graphs; keep the visible
  attribution TODO until the original GraphEval source is confirmed.
- The prototype architecture in one diagram: LLM stages vs deterministic Python
  stages vs Neo4j (source list: Experiment Report §2.2 component responsibilities).
- Designed hop depth definition (root-to-answer graph-path depth; not reasoning
  steps, not LLM calls).

## 3. Motivation

- Structured memory and correction: what a system preserves, forgets, or corrupts
  during revision; why a graph makes individual claims inspectable/rejectable.
- Do NOT present the prototype as a conversational-memory system; it is an
  instrument for observing decomposition, evaluation, preservation, revision, failure.

## 4. Methods

- Benchmark slide: Apollo 50 questions, 5 per depth 1–10, 42-node/48-edge designed
  graph (numbers from the result JSON validation block).
- Configuration slide: llama3.1:8b, Ollama, temperature 0, num_ctx 8192, 3
  iterations, 180 s timeout, Neo4j 5.26.0 execution-scoped, frozen commit `b9608d0`.
- Pipeline slide: the 17-step procedure (Experiment Report §2.3), condensed to the
  7 LLM stages + evaluate/label/feedback/validate loop.
- Scoring slide: exact vs contains vs normalized vs resolved vs path-complete —
  emphasize these are different measures (this distinction is the heart of the talk).

## 5. Results

- Headline slide: 50/50 completed, 0 errors; 27 exact (54%), 43 contains (86%),
  33 resolved (66%), 36 path-complete (72%).
- Figure slides (already generated, embed directly):
  - `results/research/figures/fig1_outcomes_by_depth.png` (state the 5-per-depth caveat on the slide)
  - `fig2_joint_outcomes.png` (28 / 15 / 5 / 2 joint categories)
  - `fig3_stop_reasons.png` (33 RESOLVED / 7 STALLED / 7 TARGET / 3 NO_EVIDENCE)
  - `fig4_revision_outcomes.png` (27 first-pass vs 23 revised; only 6 revised resolved)
- One slide on final claim labels (65 SUPPORTED / 1 CONTRADICTED / 12 NO_EVIDENCE).

## 6. Evaluation

- Trace-case slides (from `research/REPRESENTATIVE_TRACE_CASES.md`):
  - Success at depth 10: `apollo_hop_046` official run, 9-edge trusted path (Case 2).
  - Feedback-driven correction: `apollo_hop_036` (Case 3).
  - Honest rejection of a wrong answer: `apollo_hop_014` (Case 6).
  - The WannaCry regression (Case 9) — recommended as the centerpiece: 2 slides,
    one for the decomposition/initial answer (MS17-010 present, SUPPORTED), one for
    the final state (identifier lost; 2S/4C/1N; UNRESOLVED_NO_EVIDENCE + STALLED).
    Classification: "mixed pipeline-mediated model regression."
  - Instrument fix pair: `apollo_hop_046` pre-fix vs post-fix (Case 10) to explain
    why the experiment was frozen at `b9608d0`.
- Model-vs-tool classification slide (first-unsupported-transformation rule with the
  three columns model / pipeline / mixed and one example each).
- Limitations slide: 5 questions/depth, one model, one domain, nondeterminism, no
  controlled self-correction baseline (no causal claims).
- Future-work slide (clearly separated): controlled baseline comparison, repeated
  trials, more models/domains, decomposition validation, trace summarization,
  publication/poster preparation.

## 7. References

Copy from Experiment Report §6 (resolve the GraphEval attribution TODO first).

## 8. Appendices (optional)

- Per-question appendix table (from `grapheval_final_experiment_analysis.json`,
  `per_question` array).
- Reproducibility record summary (hashes, exact command) from
  `research/REPRODUCIBILITY_RECORD.md`.
- Full WannaCry trace excerpt (compact event list, not raw JSON).

## Ground rules carried over from the research pass

- Never pool pre-fix diagnostics with the official run.
- Never claim causal improvement over ordinary self-correction.
- State on every per-depth figure that each depth has five questions.
- Report tool limitations as tool limitations (e.g. Case 7's "state" answer).
