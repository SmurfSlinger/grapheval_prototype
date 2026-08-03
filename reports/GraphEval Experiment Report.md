# Evaluating Graph-Based Feedback and Iterative Backtracking in GraphEval

Experiment Report — GraphEval Prototype Research Project
Author: Kyler Gundersen · Date: August 2026
Software state: branch `debug/8b-hop-validation`, commit `b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`
Official experiment: `apollo_multihop_llama31_8b_20260727T203028Z` (2026-07-27)

Formatting note: the professor's `Experiment Template-verJuly272026.docx` was not
available in the analysis environment; this report follows the template's specified
section structure (Abstract; Introduction: Background, Objective; Methodology: Data
Collection, Experiment Setup, Procedure; Results; Discussion; Conclusion; References).

## Abstract

Large-language-model answers can mix supported, contradicted, and unsupported
statements, and conventional final-answer scoring hides how an answer changes during
self-correction. GraphEval is a prototype research instrument that decomposes a model
answer into subject–relation–object CLAIM triples, evaluates each claim against
trusted FACT triples extracted from context and persisted in Neo4j, labels every claim
SUPPORTED, CONTRADICTED, or NO_EVIDENCE, feeds the labels back for revision, and
validates a trusted evidence path before declaring an answer resolved. This report
describes the completed official experiment: a 50-question Apollo-domain multihop
benchmark (five questions at each designed graph-path depth 1–10) run with
`llama3.1:8b` via Ollama (temperature 0, 8192-token context, at most three iterations
per sub-question) at frozen commit `b9608d0`. All 50 questions completed with no
runtime errors or timeouts. 27/50 final answers matched the expected answer exactly
(54%), 43/50 contained it (86%), and the pipeline resolved 33/50 (66%) with a complete
trusted evidence path in 36/50. The dominant divergence was textually-correct-but-
pipeline-unresolved (15/50). All 27 questions resolved on the first pass were answered
correctly or near-correctly, while only 6 of the 23 questions that entered revision
ever resolved. Trace-level case studies show both successful feedback-driven
correction (a depth-8 question revised twice into an exactly correct, fully
path-validated answer) and a pipeline-mediated regression (a WannaCry depth-10
question whose initially correct bulletin identifier, MS17-010, was lost through
malformed decomposition, projection, and unsuccessful revision). A three-run repeatability
extension (the official run retained as Run 1 plus two exact-configuration
repetitions) found byte-identical final answers and identical scoring, resolution,
stop-reason, terminal-claim, and label outcomes on all 50 questions in all three
runs, with only wall-clock runtime varying — indicating that under this frozen
temperature-0 configuration on fixed hardware, single-run results were not
distorted by run-to-run sampling noise. The main limitations are the small
per-depth sample (five questions), a single model and domain for the quantitative
sample, possible output variation under changed environments that the fixed-
configuration repeatability sample cannot rule out, and the absence of a
controlled no-feedback baseline, which precludes causal claims about correction
efficacy.

## 1. Introduction

### 1.1 Background

An LLM answer to a multi-step factual question is typically scored only on its final
text. That practice hides several distinct behaviors: an answer can be textually
correct while resting on unverifiable reasoning; it can contain a correct entity
embedded in unsupported elaboration; and iterative self-correction can silently
remove correct information as easily as it removes errors. Understanding these
behaviors requires a representation in which individual statements can be inspected,
rejected, preserved, or replaced.

The broader motivation of this project is structured memory and correction: how an
AI system represents the information in its answers, what it preserves during
correction, what it forgets or removes, and how incorrect information persists.
The GraphEval prototype studied here is not a complete conversational-memory system;
it is an experimental instrument for observing answer decomposition, claim
evaluation, preservation, revision, and failure at the level of individual triples.

The instrument keeps two concepts strictly separate. A FACT is a
subject–relation–object triple extracted from trusted context, treated as trusted
evidence, stored as a FACT relationship in Neo4j, and usable in evidence-path
validation. A CLAIM is a triple extracted from a model answer; it is evaluated
against trusted FACTs and labeled SUPPORTED, CONTRADICTED, or NO_EVIDENCE, and it
remains a CLAIM even when supported — the pipeline never promotes a supported claim
into a FACT. A triple is Subject — Relation → Object; for example,
`Microsoft Security Bulletin MS17-010 — supplied_correction_to_vulnerability → how
SMBv1 handled crafted requests`.

The prototype follows the GraphEval idea of verifying LLM output as a knowledge
graph rather than as free text. [TODO: verify and cite the original GraphEval
publication; the repository does not record the source, and no attribution is
invented here.]

### 1.2 Objective

The experiment is descriptive. Its research questions are:

- **RQ1.** How reliably does GraphEval produce textually correct and graph-resolved
  answers across designed graph-path depths 1 through 10?
- **RQ2.** During iterative revision, how does GraphEval handle claims labeled
  SUPPORTED, CONTRADICTED, and NO_EVIDENCE?
- **RQ3.** Which observed failures originate primarily in the LLM, which originate
  in the GraphEval pipeline, and which are mixed failures involving both?
- **RQ4.** What does the trace reveal about preservation, correction, removal, or
  regression of answer information between the initial and final response?

The main objective is therefore to evaluate final textual correctness,
graph-grounded resolution, behavior across depth, claim-label feedback, preservation
and regression during revision, and observable model and pipeline failure modes.
Because the experiment contains no controlled no-feedback or text-only-feedback
baseline, no causal claim is made that graph feedback outperforms ordinary
self-correction.

## 2. Methodology

### 2.1 Data Collection

**Primary quantitative dataset.** The Apollo 50-question multihop benchmark
(`data/test_sets/apollo_multihop_50.json`) contains 50 questions over a fixed
designed knowledge graph of Apollo/NASA public history: 42 nodes, 48 edges, one
connected component, rooted at `Apollo 11`, with exactly five questions at each
designed depth 1–10 (validator-confirmed inside the result file). Designed hop depth
means root-to-answer graph-path depth in this fixed graph; it does not force a
number of visible reasoning statements, does not equal the number of LLM calls, and
is separate from question decomposition. Each question carries trusted context (the
text from which FACTs are extracted) and an expected answer and expected path used
only for post-inference scoring; a dedicated test
(`tests/test_expected_answer_leakage.py`) enforces that expected answers are never
supplied to inference.

**Qualitative case data.** One preserved execution of a WannaCry-domain depth-10
question (`nhs_wannacry_h10_q01`, benchmark `nhs_wannacry_multihop_50`, grounded in
NAO, DHSC, CISA, and Microsoft sources) is analyzed as a separate qualitative case;
it is never pooled with the Apollo sample. Representative cases were selected from
existing artifacts to cover first-pass success, successful revision, honest
rejection, conservative stalls, regression, and high-depth success and failure; no
new model outputs were generated and no unfavorable rows were rerun.

No human participants were involved.

### 2.2 Experiment Setup

All values below were verified from the result JSON, the preserved runner log/rc
files, and preserved shell history (exact command in
`research/EXPERIMENT_EVIDENCE_INVENTORY.md`).

| Item | Value |
|---|---|
| Frozen commit | `b9608d0f59b5dffd30d2f51aa50cc4be745dcc93` (branch `debug/8b-hop-validation`) |
| Model / provider | `llama3.1:8b` via Ollama (all seven LLM stages) |
| Context window | `num_ctx` 8192; max observed prompt ≈ 1670 tokens (limit never approached) |
| Sampling | temperature 0; `num_predict` 4096 |
| Iteration limit | 3 per sub-question |
| Timeout | 180 s per question |
| Graph store | Neo4j 5.26.0 (Docker), required, cleared between questions, execution-scoped; claim evaluation via Neo4j readback in all 50 rows |
| Runner | `scripts/run_multihop_benchmark.py` (`--continue-on-error`, cooldown 2 s) |
| Outputs | `results/research/apollo_multihop_llama31_8b_20260727T203028Z.{json,md}` |
| Host | local WSL2/Ubuntu workstation running Ollama; detailed hardware was not recorded in run artifacts and is not claimed |

**Component responsibilities.** The LLM performs answer generation, question
decomposition, context FACT extraction, sub-answer projection, CLAIM extraction, and
answer revision. Deterministic Python performs decomposition validation,
structured-triple validation, schema-alignment safety checks, claim comparison and
label assignment, target derivation and validation, trusted evidence-path
resolution, stop-condition logic, benchmark scoring, and trace/metric construction.
Neo4j persists FACTs and CLAIMs scoped by execution ID and supports graph queries
and traceability; it does not generate answers, never receives the expected answer,
and never promotes CLAIMs to FACTs.

**Instrument validation before the experiment.** The offline test suite passed at
the frozen commit (PR #5 reported 406 passed / 16 skipped, with focused reliability
tests 26 passed and related pipeline tests 93 passed / 1 skipped; re-verified in
this analysis pass with `430 passed, 16 skipped` — the additional 24 tests come from
an untracked behavior-suite test file added after the freeze). Live Apollo
depth-1/2/3/10 acceptance runs succeeded after the reliability correction
(`.runtime/benchmarks/apollo_depth_acceptance*`), and Neo4j execution isolation and
FACT/CLAIM separation are covered by dedicated tests.

### 2.3 Procedure

For each benchmark question the pipeline executes:

1. load the question and trusted context;
2. optionally decompose the question into sub-questions (LLM, then deterministic validation);
3. extract FACT triples from context, validate them (rejecting anomalies such as empty objects), write them to Neo4j, and read back the working graph;
4. generate the initial answer (LLM);
5. project the compound answer onto each sub-question (LLM);
6. extract CLAIM triples from each sub-answer (LLM);
7. apply safe schema alignment of claim fields to canonical graph vocabulary (deterministically bounded);
8. compare CLAIMs to FACTs;
9. assign SUPPORTED / CONTRADICTED / NO_EVIDENCE labels;
10. build structured feedback from the labels;
11. revise the answer (LLM);
12. validate the derived question target;
13. validate the trusted evidence path from the question's start entity to the terminal claim;
14. stop (RESOLVED, STALLED, or UNRESOLVED_*) or iterate up to the limit;
15. combine sub-answers into the final answer;
16. score the final answer textually against the expected answer (post-inference only);
17. save the per-question row, metrics, and (when enabled) a JSONL debug trace.

**Analysis.** Quantitative results were produced by
`scripts/analyze_final_experiment.py`, which recomputes every aggregate from the 50
raw rows and hard-fails if any value disagrees with the runner's own summary block
(all values agreed). Figures were generated from the analysis JSON by
`scripts/plot_final_experiment.py`. Qualitative analysis inspected preserved JSONL
debug traces event-by-event; the full case records are in
`research/REPRESENTATIVE_TRACE_CASES.md`.

## 3. Results

### 3.1 Overall results

All 50 questions completed; 0 errors, 0 timeouts, 0 resumed checkpoints. Total 83
sub-question iterations and 33 revisions. Runtime per question: min 37.5 s, Q1
40.9 s, median 44.9 s, Q3 52.8 s, max 72.5 s, mean 48.4 s.

| Metric (n = 50) | Count | Rate | Wilson 95% CI |
|---|---|---|---|
| Exact match | 27 | 0.54 | [0.40, 0.67] |
| Contains expected | 43 | 0.86 | [0.74, 0.93] |
| Normalized match | 43 | 0.86 | [0.74, 0.93] |
| Pipeline resolved | 33 | 0.66 | [0.52, 0.78] |
| Complete trusted evidence path | 36 | 0.72 | [0.58, 0.83] |

These five measures are distinct: exact match and contains-expected are textual
post-hoc scores; pipeline resolution is the deterministic verdict; path completeness
and target satisfaction are its two main components. They must not be conflated —
contains-expected in particular does not mean the final answer was ideal.

### 3.2 Stop reasons

| Final stop reason | Count |
|---|---|
| RESOLVED | 33 |
| STALLED | 7 |
| UNRESOLVED_TARGET_NOT_SATISFIED | 7 |
| UNRESOLVED_NO_EVIDENCE | 3 |

(Target satisfaction is observable through the UNRESOLVED_TARGET_NOT_SATISFIED stop
reason; rows do not carry a separate boolean.)

### 3.3 Joint textual correctness × pipeline resolution

| Joint outcome | Contains-expected basis | Exact-match basis |
|---|---|---|
| Textually correct and pipeline resolved | 28 | 27 |
| Textually correct but pipeline unresolved | 15 | 0 |
| Textually incorrect but pipeline resolved | 5 | 6 |
| Textually incorrect and pipeline unresolved | 2 | 17 |

The dominant divergence is textually-correct-but-unresolved (15/50): the model's
text contained the expected entity, but the pipeline could not assemble a supported,
target-satisfying, path-complete structured account of it. The reverse divergence
(resolved but textually wrong, 5/50) shows honest graph resolution landing on the
wrong semantic target (e.g. case `apollo_hop_037`, final answer "state").
The runner's `resolved_and_matched_count` of 28 uses its permissive `answer_match`
flag; the strict exact-and-resolved count is 27.

### 3.4 Results by designed depth

Five questions per depth: counts below are descriptive and do not establish
statistical depth trends.

| Depth | Exact | Contains | Resolved | Path complete | Avg iterations | Avg revisions | Mean runtime (s) |
|---|---|---|---|---|---|---|---|
| 1 | 4/5 | 5/5 | 4/5 | 4/5 | 1.2 | 0.2 | 40.7 |
| 2 | 3/5 | 5/5 | 3/5 | 4/5 | 1.6 | 0.6 | 46.9 |
| 3 | 3/5 | 3/5 | 4/5 | 4/5 | 1.4 | 0.4 | 43.4 |
| 4 | 2/5 | 4/5 | 2/5 | 4/5 | 1.8 | 0.8 | 52.0 |
| 5 | 4/5 | 4/5 | 5/5 | 5/5 | 1.4 | 0.4 | 47.7 |
| 6 | 4/5 | 5/5 | 4/5 | 4/5 | 1.4 | 0.4 | 46.8 |
| 7 | 1/5 | 4/5 | 2/5 | 2/5 | 1.8 | 0.8 | 48.1 |
| 8 | 1/5 | 4/5 | 3/5 | 3/5 | 2.2 | 1.2 | 53.9 |
| 9 | 3/5 | 4/5 | 4/5 | 4/5 | 2.0 | 1.0 | 52.0 |
| 10 | 2/5 | 5/5 | 2/5 | 2/5 | 1.8 | 0.8 | 52.6 |

Descriptively, exact match and resolution are high at depths 1–6 (except depth 4),
weaker at depths 7, 8, and 10, and contains-expected stays high at every depth
(3/5 at depth 3 is its only dip). Iterations and runtime drift upward with depth.
Depth-10 questions were resolvable: two resolved with complete nine-edge trusted
paths, including `apollo_hop_046` exactly ("Oceanography").

### 3.5 Revision behavior

| Group | Count | Exact | Contains | Resolved |
|---|---|---|---|---|
| First-pass (0 revisions) | 27 | 24 | 25 | 27 |
| Revised (≥ 1 revision) | 23 | 3 | 18 | 6 |

Resolution ends iteration, so first-pass rows are resolved by construction; the
table's information is that 24 of 27 first-pass resolutions were also exactly
correct. Of the 23 questions that entered revision, 6 eventually resolved, 17 ended
unresolved, and 5 still did not contain the expected answer. The official-run rows
do not store initial answers or per-iteration labels (`debug_log_path` is null), so
full initial-to-final transition matrices are computable only for the separately
traced qualitative cases; this is a documented instrument limitation, not an
analysis choice.

### 3.6 Final claim labels

| Label | Total claims (final iterations) | Questions containing label |
|---|---|---|
| SUPPORTED | 65 | 44 |
| CONTRADICTED | 1 | 1 |
| NO_EVIDENCE | 12 | 10 |

At the final iteration the Apollo run was dominated by SUPPORTED claims;
CONTRADICTED was rare (one claim in one question). NO_EVIDENCE, present in 10
questions, is the label most associated with non-resolution. Label transitions
across iterations are not recoverable for the official run (see 3.5); the WannaCry
trace below provides a fully observed example (initial SUPPORTED MS17-010 claims,
final 2 SUPPORTED / 4 CONTRADICTED / 1 NO_EVIDENCE).

### 3.7 Figures

- Figure 1 — `results/research/figures/fig1_outcomes_by_depth.png`: exact /
  contains / resolved counts by depth (five questions per depth; raw counts, no
  trend lines).
- Figure 2 — `fig2_joint_outcomes.png`: joint textual × pipeline outcomes.
- Figure 3 — `fig3_stop_reasons.png`: stop-reason distribution.
- Figure 4 — `fig4_revision_outcomes.png`: first-pass vs revised outcomes.

### 3.8 Representative trace cases

Full records in `research/REPRESENTATIVE_TRACE_CASES.md`; summary:

| Case | ID (depth) | Outcome | Classification |
|---|---|---|---|
| 1 | `apollo_hop_001` (1) | exact, RESOLVED, first pass | success baseline |
| 2 | `apollo_hop_046` (10) | exact, RESOLVED, 9-edge path, first pass | high-depth success |
| 3 | `apollo_hop_036` (8) | exact, RESOLVED after 2 revisions | successful feedback-driven revision (mixed) |
| 4 | `apollo_hop_005` (1) | contains, STALLED; degenerate claim `Apollo Program — includes → "The Apollo Program."` | mixed (extractor instability + literal deterministic handling) |
| 5 | `apollo_hop_007` (2) | contains, UNRESOLVED_NO_EVIDENCE despite supported complete path | primarily pipeline (conservative stop logic) |
| 6 | `apollo_hop_014` (3) | wrong answer, correctly not resolved (target not satisfied) | primarily model; pipeline behaved as designed |
| 7 | `apollo_hop_037` (8) | RESOLVED but final answer "state" (wrong) | primarily pipeline (target/combination semantics) |
| 8 | `apollo_hop_050` (10) | contains, unresolved (`missing_intermediate_edge`) | mixed |
| 9 | `nhs_wannacry_h10_q01` (10) | lost initially-correct MS17-010; UNRESOLVED/STALLED | mixed pipeline-mediated model regression |
| 10 | `apollo_hop_046` pre-fix vs post-fix | STALLED "Global Ocean" → RESOLVED "Oceanography" | instrument-development pair (pre-fix: pipeline) |

### 3.9 Repeatability and Nondeterminism

To quantify measurement stability, the identical experiment was executed two more
times on 2026-08-03 (UTC) as a bounded extension: the official run was retained
unmodified as Run 1, and Runs 2 and 3 were complete sequential repetitions using
the same frozen commit, dataset, model digest, Ollama build, Neo4j container, and
runner flags (verified by configuration cross-checks that hard-fail on any
mismatch; full protocol in `research/REPEATABILITY_PROTOCOL.md`). No question was
selectively rerun, and the three runs are treated as repeated measurements of the
same 50 questions, never as 150 independent questions.

| Metric (n=50 per run) | Run 1 (official) | Run 2 | Run 3 | Range |
|---|---|---|---|---|
| Completed / errors / timeouts | 50 / 0 / 0 | 50 / 0 / 0 | 50 / 0 / 0 | 0 |
| Exact match | 27 | 27 | 27 | 0 |
| Contains expected | 43 | 43 | 43 | 0 |
| Pipeline resolved | 33 | 33 | 33 | 0 |
| Evidence path complete | 36 | 36 | 36 | 0 |
| Iterations / revisions total | 83 / 33 | 83 / 33 | 83 / 33 | 0 |
| Final labels S/C/N | 65/1/12 | 65/1/12 | 65/1/12 | 0 |
| Runtime mean (s) | 48.42 | 46.73 | 45.79 | 2.63 |

Per-question comparison found complete stability on every compared dimension: all
50 questions produced byte-identical raw final answers and combined answers, and
identical exact-match, contains-expected, resolution, stop-reason, evidence-path,
terminal-claim, label-tuple, iteration, and revision outcomes in all three runs
(50/50 stable on each of the eight dimensions; all pairwise agreements 1.00).
Every stability category is therefore a stable_* category: 28
stable-correct-resolved, 15 stable-correct-unresolved, 5
stable-incorrect-resolved, 2 stable-incorrect-unresolved. Execution IDs and Neo4j
execution scopes were distinct in every run, confirming three genuinely
independent executions. The only varying quantity was wall-clock runtime (means
48.4 / 46.7 / 45.8 s; the largest per-question spread was 18.1 s on the first
question of each run, plausibly warm-up, though the artifacts do not isolate the
cause). Metrics with greatest variation: runtime only; all output metrics had
zero variation. Representative reproduced cases — including the depth-8
two-revision correction, the degenerate-extraction stall, and the
resolved-but-wrong "state" answer — are documented in
`research/REPEATABILITY_CASES.md`. Depth-level counts were likewise identical
across runs (each run contains only five questions per designed depth).

Implication for interpreting one-run results: under this fixed configuration the
official run's numbers are highly repeatable, and its failure modes are
systematic rather than sampling noise. Three runs on one machine cannot certify
determinism in general — outputs may still change across hardware, drivers,
Ollama versions, model builds, or concurrent load, and previously documented
variation between differently configured executions (the 2026-07-27 diagnostics)
shows outputs do change when conditions change.

## 4. Discussion

**What worked.** The instrument ran 50/50 questions with zero transport failures and
evaluated every question through Neo4j readback with execution-scoped isolation. Two
thirds of questions resolved with graph grounding, 72% produced a complete trusted
path, and designed ten-hop chains were traversable end-to-end (Cases 2 and 10
post-fix). The FACT/CLAIM separation held: nothing untrusted was promoted, and
every unresolved verdict in the examined cases was honest.

**What revision corrected and preserved.** Case 3 (`apollo_hop_036`) is the clearest
correction: two feedback-driven revisions converted an unresolved depth-8 answer
into an exactly correct, fully path-validated one. In the WannaCry trace, the two
SUPPORTED MS17-010 claims persisted across Q2 iterations — supported information was
preserved even while the surrounding answer degraded.

**Where revision regressed.** Only 6 of 23 revised questions resolved, and revised
questions ended with far lower exact-match (3/23) than first-pass questions (24/27).
The WannaCry Q1 sequence shows the mechanism at trace level: a malformed
decomposition ("What was the final fix provided by in...") retargeted the task, the
revision replaced a bulletin-bearing answer with "patching", the resulting invented
relation (`affected_by_final_fix`) drew NO_EVIDENCE, and the correct identifier
never returned. Revision in this configuration is roughly as able to remove correct
information as to add it — an observation, given nondeterminism and sample size, not
a rate estimate.

**Why textual correctness exceeded pipeline resolution.** 86% contains-expected vs
66% resolved is explained by three trace-verified mechanisms: degenerate or
over-expanded claim extraction (Cases 4, 9), residual NO_EVIDENCE claims blocking an
otherwise supported answer (Case 5), and missing intermediate edges between the
start entity and a supported terminal claim (Case 8). These are mostly instrument
(pipeline or extractor) phenomena, not wrong answers.

**Depth.** Descriptively, depth 7–10 questions iterate more, run longer, and resolve
less often than depth 1–6 questions, but the pattern is not monotonic (depth 5 was
perfect for resolution; depth 3 had the lowest contains-expected) and five questions
per depth cannot establish a trend. The strongest supported statement is that
designed depth 10 is not a hard barrier: both resolved depth-10 rows produced
complete nine-edge trusted paths.

**Model vs tool.** Applying the first-unsupported-transformation rule: clear
model-side failures include wrong or evasive answers with failed recovery (Case 6)
and reversed or over-expanded claim extraction (Cases 4, 9, 10 pre-fix trigger).
Clear pipeline-side failures include unsafe alignment overwriting a correct terminal
claim (Case 10 pre-fix), target validation accepting a generic terminal object
(Case 7), conservative stop logic discarding a supported complete path (Case 5), and
the unresolved combiner projecting a wrong terminal object (Cases 7 and 10 pre-fix).
Mixed failures — malformed LLM decomposition accepted by deterministic validation,
over-expanded claims judged literally, accurate feedback followed by regressing
revision, thin trusted graphs bridged by unsupported claims — dominate the most
instructive cases (8, 9). The WannaCry case is classified as a mixed
pipeline-mediated model regression, not as evidence that an 8B model cannot answer a
ten-hop question: the same model produced the correct bulletin inside the same
execution.

**Repeatability, nondeterminism, and measurement stability.** In principle,
answer wording, decomposition, extracted triples, alignment candidates, and
revisions can vary between runs; a repeated execution is a new sample, not a
correction. The three-run extension (§3.9) measured this directly under the
frozen configuration and found zero output variation: all 50 questions reproduced
byte-identical answers and identical pipeline outcomes in three independent
executions six days apart, with only runtime varying. Two readings follow. First,
the official run's results — including its failure modes — are systematic under
these conditions, which strengthens the trace-level failure analysis: the
degenerate extraction of Case 4 and the "state" resolution of Case 7 recur
identically rather than appearing sporadically. Second, the stability is
conditional: it was observed at temperature 0 on one machine with one model
digest and one Ollama build, and it does not extend to changed conditions (the
differently configured 2026-07-27 diagnostics produced different outputs for the
same questions, and the WannaCry qualitative case ran under its own
configuration). The problematic WannaCry execution was deliberately not rerun;
pre-fix and post-fix runs were never pooled; and the three repeatability runs
were never pooled into 150 independent questions.

**Contribution.** The evidence supports a technical contribution — a working
decomposed graph-based backtracking instrument with structured claim-level feedback,
strict FACT/CLAIM separation, execution-scoped Neo4j persistence, target and
evidence-path validation, full traceability, benchmark tooling, and the reliability
safeguards frozen at `b9608d0` (Case 10 documents the concrete alignment-drift fix).
It also supports a modest research contribution: the textual-correctness vs
graph-resolution distinction is measurable and large (86% vs 66%); correction and
regression during revision are directly observable at claim level; and graph
feedback exposed information loss (Case 9) that final-answer-only evaluation would
hide — even in a case where it failed to repair the loss. No claim of broad
generalizability is made: one model, one quantitative domain, one configuration
(measured in triplicate by §3.9).

## 5. Conclusion

A frozen build of the GraphEval prototype executed the official 50-question
Apollo multihop benchmark cleanly (50/50, zero errors), producing 54% exact-match,
86% contains-expected, and 66% pipeline-resolved outcomes with complete trusted
paths in 72% of questions. The gap between textual correctness and graph resolution,
the honest refusal to resolve unsupported answers, and trace-visible preservation,
correction, and regression during revision are the experiment's principal findings.
Ten-hop designed chains were resolvable, and the most informative failure — the
WannaCry case — demonstrates precisely the kind of information-loss visibility that
motivates graph-grounded evaluation. A three-run repeatability
extension reproduced every output of the official run exactly (only runtime
varied), so the reported numbers and failure modes are stable properties of this
configuration rather than single-run sampling noise. The evidence base remains
deliberately bounded: five questions per depth, a single model, a single
quantitative domain, no controlled self-correction baseline, and repeatability
established only for the fixed configuration on one machine.

Immediate future work, kept separate from the completed scope: a controlled
comparison of initial answers, generic self-correction, and graph-feedback
correction; repeatability trials across environments, model builds, and non-zero
temperatures (fixed-configuration repeatability is established by §3.9, but
cross-environment stability is not); additional models and domains; stronger
decomposition validation (Case 9's malformed sub-question passed validation);
improved trace summarization; and preparation of a publication or poster from
this skeleton.

## 6. References

1. GraphEval prototype repository: `grapheval_prototype`, branch
   `debug/8b-hop-validation`, commit `b9608d0f59b5dffd30d2f51aa50cc4be745dcc93`
   (implementation, benchmark tooling, and all result artifacts cited in this report).
2. [TODO — original GraphEval publication: the repository describes the system as
   "GraphEval-style" but does not record the source; attribution must be verified
   before submission.]
3. UK National Audit Office, *Investigation: WannaCry cyber attack and the NHS*,
   HC 414, 25 April 2018. (WannaCry benchmark grounding.)
4. Department of Health & Social Care / NHS CIO, *Lessons learned review of the
   WannaCry Ransomware Cyber Attack*, 1 February 2018.
5. CISA / US-CERT, Alert TA17-132A: *Indicators Associated With WannaCry
   Ransomware*, May 2017.
6. Microsoft, *Microsoft Security Bulletin MS17-010 — Critical: Security Update for
   Microsoft Windows SMB Server*, 14 March 2017.
7. Project analysis artifacts: `results/research/grapheval_final_experiment_analysis.{json,md}`;
   `research/REPRESENTATIVE_TRACE_CASES.md`; `research/EXPERIMENT_PROTOCOL.md`;
   `research/REPRODUCIBILITY_RECORD.md` (this repository, 2026-08-02).
8. Repeatability extension artifacts:
   `results/research/repeatability/apollo_repeat_run{2,3}_llama31_8b_<UTCSTAMP>.{json,md}`;
   `results/research/repeatability/grapheval_repeatability_analysis.{json,md}`;
   `research/REPEATABILITY_PROTOCOL.md`; `research/REPEATABILITY_CASES.md`
   (this repository, 2026-08-03).
