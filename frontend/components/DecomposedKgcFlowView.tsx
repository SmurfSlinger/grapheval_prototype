"use client";

import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import type {
  DecomposedBacktrackingResult,
  KgcFact,
  SubQuestionIteration,
  SubQuestionResult,
  TraceEvaluatedClaim,
  TraceFeedbackItem,
  TraceTriple,
} from "@/lib/api";
import { StatChip, StatChipRow } from "@/components/kgc/StageCard";

interface DecomposedKgcFlowViewProps {
  result: DecomposedBacktrackingResult;
}

function formatTriple(t: TraceTriple | KgcFact): string {
  return `${t.subject} — ${t.relation} → ${t.object}`;
}

function normalizeRelation(relation: string): string {
  return relation.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

/** Deterministic relation → readable claim label (no case-specific values). */
const RELATION_DISPLAY: Record<string, string> = {
  has_a1c: "A1C",
  a1c: "A1C",
  a1c_value: "A1C",
  hemoglobin_a1c: "A1C",
  lab_value: "Lab value",
  measured_value: "Measured value",
  has_ckd_stage: "CKD stage",
  ckd_stage: "CKD stage",
  disease_stage: "Disease stage",
  renal_stage: "Renal stage",
  stage: "Stage",
  has_stage: "Stage",
  has_egfr: "eGFR",
  egfr: "eGFR",
  egfr_value: "eGFR",
  kidney_function_measurement: "Kidney function",
  renal_measurement: "Kidney function",
  diagnosed_with: "Diagnosis",
  has_diagnosis: "Diagnosis",
  diagnosis: "Diagnosis",
  condition: "Condition",
  has_condition: "Condition",
  discontinued_medication: "Stopped medication",
  medication_discontinued: "Stopped medication",
  discontinued: "Stopped medication",
  stopped: "Stopped medication",
  stopped_medication: "Stopped medication",
  discontinued_because: "Reason for stopping",
  stopped_because: "Reason for stopping",
  intolerance_reason: "Reason for stopping",
  adverse_effect: "Adverse effect",
  discontinuation_reason: "Reason for stopping",
  active_medication: "Current medication",
  currently_taking: "Current medication",
  tolerated: "Tolerated medication",
  medication_tolerated: "Tolerated medication",
  taking: "Current medication",
  daily_dose: "Dose",
  dose: "Dose",
  prescribed_dose: "Dose",
  has_dose: "Dose",
  discussed_not_started: "Discussed but not started",
  planned_not_started: "Discussed but not started",
  considered: "Considered",
  future_option: "Future option",
  discussed: "Discussed",
  allergic_to: "Allergy",
  allergy: "Allergy",
  medication_allergy: "Allergy",
  has_allergy: "Allergy",
  causes_reaction: "Reaction",
  allergy_reaction: "Reaction",
  reaction: "Reaction",
  allergic_reaction: "Reaction",
  occurred_during: "Date",
  occurred_between: "Date range",
  crewed_by: "Crew",
  launched_from: "Launch site",
  president_at_time: "President at the time",
  collected: "Amount collected",
  spoke_with: "Spoke with",
};

function friendlyClaimText(t: TraceTriple | KgcFact): string {
  const rel = normalizeRelation(t.relation);
  const label = RELATION_DISPLAY[rel];
  if (label) return `${label}: ${t.object}`;
  const words = t.relation.replace(/_/g, " ");
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}: ${t.object}`;
}

function relationDisplayLabel(relation: string): string {
  const rel = normalizeRelation(relation);
  if (RELATION_DISPLAY[rel]) return RELATION_DISPLAY[rel];
  const words = relation.replace(/_/g, " ");
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}`;
}

function hasText(value: string | null | undefined): boolean {
  return Boolean(value && value.trim());
}

function iterationActionTitle(backendIndex: number): string {
  if (backendIndex === 0) return "Check the starting answer";
  if (backendIndex === 1) return "Check the revised answer";
  return "Check the next revision";
}

function answerSecondaryLabel(backendIndex: number): string {
  if (backendIndex === 0) return "Starting answer · Answer(0)";
  if (backendIndex === 1) return "Revised answer · Answer(1)";
  return `Revision · Answer(${backendIndex})`;
}

function labelVariant(
  label: string,
): "supported" | "contradicted" | "nei" | "neutral" {
  const upper = label.toUpperCase();
  if (upper === "SUPPORTED") return "supported";
  if (upper === "CONTRADICTED") return "contradicted";
  if (upper === "NO_EVIDENCE") return "nei";
  return "neutral";
}

function stopVariant(
  stop: string,
): "supported" | "contradicted" | "nei" | "neutral" {
  if (stop === "RESOLVED") return "supported";
  if (stop === "STALLED" || stop.startsWith("UNRESOLVED")) return "nei";
  if (stop === "MAX_ITERATIONS") return "contradicted";
  return "neutral";
}

function stopFriendly(stop: string): string {
  if (stop === "RESOLVED") return "Resolved";
  if (stop === "STALLED") return "Stalled";
  if (stop.startsWith("UNRESOLVED")) return "Unresolved";
  if (stop === "MAX_ITERATIONS") return "Max iterations";
  return stop;
}

function provenanceBadge(provenance: string, derived: boolean): {
  text: string;
  className: string;
} {
  if (derived || provenance.includes("derived")) {
    return {
      text: "Derived from trusted context",
      className: "rt-badge rt-badge-derived",
    };
  }
  if (provenance.includes("trusted_context")) {
    return {
      text: "From trusted context",
      className: "rt-badge rt-badge-direct",
    };
  }
  if (provenance.includes("existing") || provenance.includes("supported_by")) {
    return {
      text: "Already in knowledge graph",
      className: "rt-badge rt-badge-existing",
    };
  }
  return {
    text: "Focused trusted fact",
    className: "rt-badge rt-badge-focused",
  };
}

function buildCorrectionPlan(feedback: TraceFeedbackItem[] | undefined) {
  const preserve: TraceFeedbackItem[] = [];
  const correct: TraceFeedbackItem[] = [];
  const investigate: TraceFeedbackItem[] = [];
  for (const item of feedback ?? []) {
    const label = item.label.toUpperCase();
    if (label === "SUPPORTED") preserve.push(item);
    else if (label === "CONTRADICTED") correct.push(item);
    else investigate.push(item);
  }
  return { preserve, correct, investigate };
}

function FriendlyClaimLine({ t }: { t: TraceTriple | KgcFact }) {
  return (
    <div className="rt-friendly-claim">
      <p className="rt-claim-sentence">{friendlyClaimText(t)}</p>
      <details className="rt-evidence">
        <summary>Structured triple</summary>
        <code className="rt-triple">{formatTriple(t)}</code>
      </details>
    </div>
  );
}

function FactBlock({
  title,
  why,
  facts,
  derived = false,
  provenance = "trusted_context",
  derivationType,
  evidenceSpans,
}: {
  title: string;
  why?: string;
  facts: KgcFact[];
  derived?: boolean;
  provenance?: string;
  derivationType?: string | null;
  evidenceSpans?: string[];
}) {
  if (facts.length === 0) return null;
  const badge = provenanceBadge(provenance, derived);
  return (
    <div className={`rt-kgc-block ${derived ? "rt-kgc-derived" : "rt-kgc-direct"}`}>
      <div className="rt-kgc-block-header">
        <span className={badge.className}>{badge.text}</span>
        <span className="rt-panel-title">{title}</span>
      </div>
      {why ? <p className="rt-note">{why}</p> : null}
      <ul className="rt-triple-list">
        {facts.map((fact, idx) => (
          <li key={idx} className="rt-triple-item">
            <FriendlyClaimLine t={fact} />
            {hasText(fact.evidence) ? (
              <details className="rt-evidence">
                <summary>View evidence</summary>
                <p>{fact.evidence}</p>
              </details>
            ) : null}
          </li>
        ))}
      </ul>
      {derivationType ? (
        <details className="rt-evidence">
          <summary>Derivation details</summary>
          <p className="rt-note">{derivationType.replace(/_/g, " ")}</p>
        </details>
      ) : null}
      {evidenceSpans && evidenceSpans.length > 0 ? (
        <details className="rt-evidence">
          <summary>Based on</summary>
          <ul>
            {evidenceSpans.map((span, i) => (
              <li key={i}>{span}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function ClaimEvalCard({ claim }: { claim: TraceEvaluatedClaim }) {
  const variant = labelVariant(claim.label);
  const upper = claim.label.toUpperCase();
  const friendly =
    upper === "SUPPORTED"
      ? "Correct — keep this"
      : upper === "CONTRADICTED"
        ? "Incorrect — correct this"
        : "Not enough evidence yet";
  const mark = upper === "SUPPORTED" ? "✓" : upper === "CONTRADICTED" ? "✗" : "?";
  const evidence = hasText(claim.evidence) ? claim.evidence : null;
  const reason = hasText(claim.reason) ? claim.reason : null;

  return (
    <div className={`rt-claim-card rt-claim-${variant}`}>
      <div className="rt-claim-head">
        <span className="rt-claim-mark" aria-hidden>
          {mark}
        </span>
        <strong className="rt-claim-primary">{friendly}</strong>
        <span className={`rt-label-badge rt-label-${variant}`}>{claim.label}</span>
      </div>

      {upper === "CONTRADICTED" ? (
        <>
          <p className="rt-claim-sentence">
            {relationDisplayLabel(claim.triple.relation)}
          </p>
          <div className="rt-compare">
            <div>
              <span className="rt-compare-label">Claimed</span>
              <span>{claim.triple.object}</span>
            </div>
            <span className="rt-compare-arrow" aria-hidden>
              →
            </span>
            <div>
              <span className="rt-compare-label">Trusted value</span>
              <span>{claim.conflicting_object ?? "—"}</span>
            </div>
          </div>
        </>
      ) : (
        <p className="rt-claim-sentence">{friendlyClaimText(claim.triple)}</p>
      )}

      <details className="rt-evidence">
        <summary>Details</summary>
        <div className="rt-claim-details">
          <p className="rt-note">Structured triple</p>
          <code className="rt-triple">{formatTriple(claim.triple)}</code>
          {reason ? (
            <>
              <p className="rt-note">Reason</p>
              <p>{reason}</p>
            </>
          ) : null}
          {evidence ? (
            <>
              <p className="rt-note">Evidence</p>
              <p>{evidence}</p>
            </>
          ) : null}
          {claim.matched_kgc_fact ? (
            <>
              <p className="rt-note">Matched knowledge-graph fact</p>
              <code className="rt-triple">{formatTriple(claim.matched_kgc_fact)}</code>
            </>
          ) : null}
          {claim.conflicting_fact ? (
            <>
              <p className="rt-note">Conflicting knowledge-graph fact</p>
              <code className="rt-triple">{formatTriple(claim.conflicting_fact)}</code>
            </>
          ) : null}
        </div>
      </details>
    </div>
  );
}

function IterationTimeline({
  iter,
  nextAnswer,
  isLast,
  stopReason,
  proactiveFacts,
  kgcBefore,
  kgcAfter,
  finalAnswer,
}: {
  iter: SubQuestionIteration;
  nextAnswer?: string;
  isLast: boolean;
  stopReason: string;
  proactiveFacts: KgcFact[];
  kgcBefore: number;
  kgcAfter: number;
  finalAnswer: string;
}) {
  const displayN = iter.iteration + 1;
  const claims = iter.evaluated_claims ?? [];
  const plan = buildCorrectionPlan(iter.backtracking_feedback);
  const directFacts = [...(iter.focused_facts_added ?? [])];
  const derivedFacts = iter.derived_facts_added ?? [];
  const proactiveCount = iter.iteration === 0 ? proactiveFacts.length : 0;
  const addedCount = proactiveCount + directFacts.length + derivedFacts.length;
  const derivationType =
    iter.derivation_trace && typeof iter.derivation_trace.derivation_type === "string"
      ? iter.derivation_trace.derivation_type
      : null;
  const resolved = stopReason === "RESOLVED";

  return (
    <article className="rt-iteration">
      <header className="rt-iteration-header">
        <h4 className="rt-iteration-title">
          ITERATION {displayN} — {iterationActionTitle(iter.iteration)}
        </h4>
        <p className="rt-answer-secondary">{answerSecondaryLabel(iter.iteration)}</p>
      </header>

      <section className="rt-panel rt-panel-answer">
        <h5 className="rt-panel-label">CURRENT ANSWER</h5>
        <p className="rt-answer-text">{iter.answer}</p>
      </section>

      <div className="rt-stage-arrow" aria-hidden>
        ↓
      </div>

      <section className="rt-panel rt-panel-claims">
        <h5 className="rt-panel-label">WHAT THE ANSWER CLAIMS</h5>
        {(iter.aligned_claims ?? iter.extracted_claims ?? []).length > 0 ? (
          <ul className="rt-triple-list">
            {(iter.aligned_claims ?? iter.extracted_claims ?? []).map((t, i) => (
              <li key={i}>
                <FriendlyClaimLine t={t} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="rt-note">No claims were extracted from this answer.</p>
        )}
      </section>

      <div className="rt-stage-arrow" aria-hidden>
        ↓
      </div>

      <section className="rt-panel rt-panel-eval">
        <h5 className="rt-panel-label">CHECK AGAINST THE KNOWLEDGE GRAPH</h5>
        {claims.length > 0 ? (
          claims.map((c, i) => <ClaimEvalCard key={i} claim={c} />)
        ) : (
          <p className="rt-note">No claims were checked in this iteration.</p>
        )}
      </section>

      <div className="rt-stage-arrow" aria-hidden>
        ↓
      </div>

      <section className="rt-panel rt-panel-plan">
        <h5 className="rt-panel-label">WHAT NEEDS TO CHANGE?</h5>
        <div className="rt-plan-grid">
          <div>
            <h6>Keep</h6>
            {plan.preserve.length > 0 ? (
              <ul>
                {plan.preserve.map((fb, i) => (
                  <li key={i}>{friendlyClaimText(fb.triple)}</li>
                ))}
              </ul>
            ) : (
              <p className="rt-note">Nothing to keep</p>
            )}
          </div>
          <div>
            <h6>Change</h6>
            {plan.correct.length > 0 ? (
              <ul>
                {plan.correct.map((fb, i) => (
                  <li key={i}>
                    {fb.triple.object}
                    {fb.conflicting_object ? (
                      <>
                        {" "}
                        <span className="rt-compare-arrow">→</span>{" "}
                        {fb.conflicting_object}
                      </>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rt-note">Nothing to change</p>
            )}
          </div>
          <div>
            <h6>Remove or investigate</h6>
            {plan.investigate.length > 0 ? (
              <ul>
                {plan.investigate.map((fb, i) => (
                  <li key={i}>{friendlyClaimText(fb.triple)}</li>
                ))}
              </ul>
            ) : (
              <p className="rt-note">None</p>
            )}
          </div>
        </div>
      </section>

      <div className="rt-stage-arrow" aria-hidden>
        ↓
      </div>

      <section className="rt-panel rt-panel-kgc">
        <h5 className="rt-panel-label">KNOWLEDGE GRAPH UPDATE</h5>
        {addedCount === 0 ? (
          <p className="rt-note">
            No new fact was needed. The trusted value used for this check was already
            present in the working knowledge graph.
          </p>
        ) : (
          <>
            <p className="rt-kgc-count">
              Working knowledge graph: <strong>{kgcBefore}</strong> →{" "}
              <strong>{kgcAfter}</strong> facts
              <span className="rt-kgc-delta-chip">+{addedCount} this step</span>
            </p>
            {proactiveCount > 0 ? (
              <p className="rt-note">
                Includes {proactiveCount} fact
                {proactiveCount === 1 ? "" : "s"} gathered before checking the
                starting answer (shown above).
              </p>
            ) : null}
            <FactBlock
              title="Added from trusted context"
              why="This fact was extracted while checking the current question."
              facts={directFacts}
              derived={false}
              provenance="trusted_context"
            />
            <FactBlock
              title="Derived from trusted context"
              why="A question-specific fact was derived from trusted context."
              facts={derivedFacts}
              derived
              provenance="derived_from_trusted_context"
              derivationType={derivationType}
            />
          </>
        )}
        {iter.derivation_trace &&
        Array.isArray(iter.derivation_trace.accepted) &&
        (iter.derivation_trace.accepted as unknown[]).length > 0 ? (
          <details className="rt-evidence">
            <summary>Derivation details</summary>
            <ul className="rt-triple-list">
              {(
                iter.derivation_trace.accepted as Array<{
                  fact?: TraceTriple;
                  derivation_type?: string;
                  evidence_spans?: string[];
                  explanation?: string;
                }>
              ).map((item, i) => (
                <li key={i} className="rt-triple-item">
                  {item.fact ? <FriendlyClaimLine t={item.fact} /> : null}
                  {item.derivation_type ? (
                    <p className="rt-note">
                      {item.derivation_type.replace(/_/g, " ")}
                    </p>
                  ) : null}
                  {item.explanation ? (
                    <p className="rt-note">{item.explanation}</p>
                  ) : null}
                  {item.evidence_spans && item.evidence_spans.length > 0 ? (
                    <ul>
                      {item.evidence_spans.map((span, j) => (
                        <li key={j}>{span}</li>
                      ))}
                    </ul>
                  ) : null}
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </section>

      {!isLast && nextAnswer != null ? (
        <>
          <div className="rt-stage-arrow" aria-hidden>
            ↓
          </div>
          <section className="rt-panel rt-panel-revised">
            <h5 className="rt-panel-label">REVISED ANSWER</h5>
            <p className="rt-answer-text">{nextAnswer}</p>
          </section>
        </>
      ) : null}

      {isLast ? (
        <section className="rt-panel rt-panel-final">
          <h5 className="rt-panel-label">FINAL RESULT</h5>
          <p className="rt-final-status">
            {resolved ? "✓ Resolved" : `⚠ ${stopFriendly(stopReason)}`}
          </p>
          <p className="rt-note">Final answer</p>
          <p className="rt-answer-text">{finalAnswer}</p>
        </section>
      ) : null}
    </article>
  );
}

function tabStatusMark(stop: string): string {
  if (stop === "RESOLVED") return "✓";
  if (stop === "GENERATION_FAILED" || stop === "NO_CLAIMS_EXTRACTED") return "✕";
  return "⚠";
}

function tabStatusClass(stop: string): string {
  if (stop === "RESOLVED") return "rt-q-tab-resolved";
  if (stop === "GENERATION_FAILED" || stop === "NO_CLAIMS_EXTRACTED") {
    return "rt-q-tab-failed";
  }
  return "rt-q-tab-warn";
}

function SubQuestionTrace({
  sub,
  baseKgcCount,
  runningKgcStart,
}: {
  sub: SubQuestionResult;
  baseKgcCount: number;
  runningKgcStart: number;
}) {
  const proactive = sub.focused_extraction_merged ?? [];
  const resolved = sub.stop_reason === "RESOLVED";
  const withoutCorrection =
    resolved && (sub.revision_count === 0 || sub.resolved_without_revision);
  const corrections = sub.revision_count ?? 0;
  const resultLabel = withoutCorrection
    ? "✓ Resolved without correction"
    : resolved
      ? `✓ Resolved after ${corrections} revision${corrections === 1 ? "" : "s"}`
      : `⚠ ${stopFriendly(sub.stop_reason)}`;

  const kgcOffsets = useMemo(() => {
    let count = runningKgcStart;
    return sub.iteration_history.map((iter, idx) => {
      const before = count;
      const direct =
        (idx === 0 ? proactive.length : 0) + (iter.focused_facts_added?.length ?? 0);
      const derived = iter.derived_facts_added?.length ?? 0;
      count += direct + derived;
      return { before, after: count };
    });
  }, [sub.iteration_history, proactive.length, runningKgcStart]);

  return (
    <div className="rt-subq-panel">
      <header className="rt-subq-panel-header">
        <div className="rt-subq-header-top">
          <span className="rt-subq-id">Q{sub.sub_question_id}</span>
          <h3 className="rt-subq-question">{sub.question}</h3>
        </div>
        <p className="rt-note">Starting answer</p>
        <p className="rt-preview-answer">{sub.initial_answer}</p>
        <p className="rt-result-line">{resultLabel}</p>
      </header>

      <div className="rt-subq-body">
        {proactive.length > 0 ? (
          <div className="rt-panel rt-panel-kgc">
            <h5 className="rt-panel-label">
              Knowledge gathered before the first check
            </h5>
            <FactBlock
              title="From trusted context"
              why="These facts were pulled from the trusted context for this question."
              facts={proactive}
              provenance="trusted_context"
            />
          </div>
        ) : null}

        <div className="rt-timeline">
          {sub.iteration_history.map((iter, idx) => (
            <IterationTimeline
              key={iter.iteration}
              iter={iter}
              nextAnswer={sub.iteration_history[idx + 1]?.answer}
              isLast={idx === sub.iteration_history.length - 1}
              stopReason={sub.stop_reason}
              proactiveFacts={idx === 0 ? proactive : []}
              kgcBefore={kgcOffsets[idx]?.before ?? baseKgcCount}
              kgcAfter={kgcOffsets[idx]?.after ?? baseKgcCount}
              finalAnswer={sub.final_answer}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function DecomposedKgcFlowView({ result }: DecomposedKgcFlowViewProps) {
  const metrics = result.metrics;
  const [viewMode, setViewMode] = useState<"research" | "advanced">("research");
  const firstId = result.sub_question_results[0]?.sub_question_id ?? 1;
  const [activeQuestionId, setActiveQuestionId] = useState<number>(firstId);

  // Reset to first question whenever a new run result arrives.
  useEffect(() => {
    setActiveQuestionId(result.sub_question_results[0]?.sub_question_id ?? 1);
  }, [result]);

  const questionIds = result.sub_question_results.map((s) => s.sub_question_id);
  const activeSub =
    result.sub_question_results.find((s) => s.sub_question_id === activeQuestionId) ??
    result.sub_question_results[0] ??
    null;

  const selectQuestion = (id: number) => {
    setActiveQuestionId(id);
  };

  const onTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, id: number) => {
    const index = questionIds.indexOf(id);
    if (index < 0) return;
    let nextIndex = index;
    if (event.key === "ArrowRight") {
      nextIndex = (index + 1) % questionIds.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex = (index - 1 + questionIds.length) % questionIds.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = questionIds.length - 1;
    } else {
      return;
    }
    event.preventDefault();
    const nextId = questionIds[nextIndex];
    setActiveQuestionId(nextId);
    const el = document.getElementById(`rt-tab-q-${nextId}`);
    el?.focus();
  };

  const summary = useMemo(() => {
    const claimsPreserved = result.sub_question_results.reduce(
      (sum, sub) => sum + (sub.initial_supported ?? 0),
      0,
    );
    const claimsCorrected = metrics?.corrected_claims_count ?? 0;
    const revisions =
      metrics?.total_revisions ??
      result.sub_question_results.reduce(
        (sum, sub) => sum + (sub.revision_count ?? 0),
        0,
      );
    let directFacts = 0;
    let derivedFacts = 0;
    for (const sub of result.sub_question_results) {
      directFacts += sub.focused_facts_added_count ?? 0;
      for (const iter of sub.iteration_history) {
        derivedFacts += iter.derived_facts_added?.length ?? 0;
      }
    }
    const additions = result.working_kgc_additions ?? [];
    if (additions.length > 0) {
      directFacts = additions.filter(
        (a) =>
          a.provenance === "trusted_context" ||
          a.extraction_scope === "sub_question_focused",
      ).length;
      derivedFacts = additions.filter((a) =>
        a.provenance.includes("derived"),
      ).length;
    }
    return {
      questions: metrics?.sub_question_count ?? result.sub_questions.length,
      resolved: metrics?.resolved_sub_questions ?? 0,
      iterations: metrics?.total_iterations ?? 0,
      revisions,
      claimsPreserved,
      claimsCorrected,
      directFacts,
      derivedFacts,
      retries:
        metrics?.structured_output_retries ??
        result.trace?.structured_output_retries ??
        0,
    };
  }, [result, metrics]);

  const kgcStarts = useMemo(() => {
    let count = result.base_kgc_facts.length;
    const starts: Record<number, number> = {};
    for (const sub of result.sub_question_results) {
      starts[sub.sub_question_id] = count;
      count +=
        (sub.focused_extraction_merged?.length ?? 0) +
        sub.iteration_history.reduce(
          (sum, it) =>
            sum +
            (it.focused_facts_added?.length ?? 0) +
            (it.derived_facts_added?.length ?? 0),
          0,
        );
    }
    return starts;
  }, [result]);

  return (
    <div className="kgc-dashboard rt-dashboard">
      <div className="rt-mode-toggle" role="tablist" aria-label="Trace view mode">
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "research"}
          className={viewMode === "research" ? "rt-mode-active" : ""}
          onClick={() => setViewMode("research")}
        >
          Research Trace
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "advanced"}
          className={viewMode === "advanced" ? "rt-mode-active" : ""}
          onClick={() => setViewMode("advanced")}
        >
          Advanced / Raw Trace
        </button>
      </div>

      {viewMode === "research" ? (
        <>
          <section className="rt-summary-card">
            <h3 className="kgc-section-title">What happened in this run</h3>
            <p className="rt-outcome-summary">
              {summary.resolved === summary.questions
                ? `All ${summary.questions} questions resolved.`
                : `${summary.resolved} of ${summary.questions} questions resolved.`}{" "}
              The system checked {summary.iterations} answer state
              {summary.iterations === 1 ? "" : "s"}, preserved{" "}
              {summary.claimsPreserved} initially correct claim component
              {summary.claimsPreserved === 1 ? "" : "s"}, corrected{" "}
              {summary.claimsCorrected} incorrect component
              {summary.claimsCorrected === 1 ? "" : "s"}, and combined the
              resolved answers into one final response.
            </p>
            <StatChipRow>
              <StatChip label={`${summary.questions} questions`} />
              <StatChip
                label={`${summary.resolved} resolved`}
                variant="supported"
              />
              <StatChip label={`${summary.iterations} answer checks`} />
              <StatChip
                label={`${summary.revisions} revisions`}
                variant="revision"
              />
              <StatChip
                label={`${summary.claimsPreserved} correct parts preserved`}
                variant="supported"
              />
              <StatChip
                label={`${summary.claimsCorrected} incorrect parts corrected`}
                variant="contradicted"
              />
              {summary.retries > 0 ? (
                <StatChip label={`${summary.retries} output retries`} />
              ) : null}
            </StatChipRow>
            <div className="rt-kg-growth">
              <span className="rt-kg-growth-label">Knowledge graph growth</span>
              <StatChipRow>
                <StatChip
                  label={`+${summary.directFacts} direct facts`}
                  variant="revision"
                />
                <StatChip label={`+${summary.derivedFacts} derived facts`} />
              </StatChipRow>
              <p className="rt-note">
                Newly added during this run only — not all trusted facts used.
              </p>
            </div>
          </section>

          <nav className="rt-flow rt-flow-simple" aria-label="Research process">
            <span className="rt-flow-step">Compound question</span>
            <span className="rt-flow-arrow" aria-hidden>
              →
            </span>
            <span className="rt-flow-step">
              {summary.questions} atomic questions
            </span>
            <span className="rt-flow-arrow" aria-hidden>
              →
            </span>
            <span className="rt-flow-step">Check and correct each one</span>
            <span className="rt-flow-arrow" aria-hidden>
              →
            </span>
            <span className="rt-flow-step">Combine final answers</span>
          </nav>

          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">Original compound question</h3>
            <p className="kgc-input-value">{result.original_question}</p>
          </section>

          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">Run and graph storage</h3>
            <p className="kgc-input-value">
              Run ID: {result.example_id}
              {" · "}
              KGc evaluation:{" "}
              {result.trace?.kgc_evaluation_source ?? "in_memory"}
              {" · "}
              Neo4j clear:{" "}
              {result.trace?.neo4j_cleared_before_run ? "yes" : "no"}
              {" · "}
              FACTS persisted:{" "}
              {(result.trace?.neo4j_base_facts_persisted ?? 0) +
                (result.trace?.neo4j_working_facts_persisted ?? 0)}
            </p>
            {result.trace?.configured_num_ctx ? (
              <p className="rt-note">
                Model context configured to {result.trace.configured_num_ctx} tokens.
              </p>
            ) : null}
          </section>

          <section className="rt-question-tabs-card">
            <div
              className="rt-q-tablist"
              role="tablist"
              aria-label="Sub-questions"
            >
              {result.sub_question_results.map((sub) => {
                const selected = activeSub?.sub_question_id === sub.sub_question_id;
                const mark = tabStatusMark(sub.stop_reason);
                const statusText = stopFriendly(sub.stop_reason);
                return (
                  <button
                    key={sub.sub_question_id}
                    id={`rt-tab-q-${sub.sub_question_id}`}
                    type="button"
                    role="tab"
                    aria-selected={selected}
                    aria-controls={`rt-panel-q-${sub.sub_question_id}`}
                    tabIndex={selected ? 0 : -1}
                    title={sub.question}
                    aria-label={`Q${sub.sub_question_id}: ${sub.question} ${statusText}.`}
                    className={`rt-q-tab ${tabStatusClass(sub.stop_reason)} ${
                      selected ? "rt-q-tab-active" : ""
                    }`}
                    onClick={() => selectQuestion(sub.sub_question_id)}
                    onKeyDown={(event) => onTabKeyDown(event, sub.sub_question_id)}
                  >
                    Q{sub.sub_question_id} {mark}
                  </button>
                );
              })}
            </div>

            {activeSub ? (
              <div
                id={`rt-panel-q-${activeSub.sub_question_id}`}
                role="tabpanel"
                aria-labelledby={`rt-tab-q-${activeSub.sub_question_id}`}
                className="rt-q-tabpanel"
              >
                <SubQuestionTrace
                  key={activeSub.sub_question_id}
                  sub={activeSub}
                  baseKgcCount={result.base_kgc_facts.length}
                  runningKgcStart={
                    kgcStarts[activeSub.sub_question_id] ??
                    result.base_kgc_facts.length
                  }
                />
              </div>
            ) : null}
          </section>

          <section className="kgc-summary-card kgc-stage-final">
            <h3 className="kgc-section-title">Combined final answer</h3>
            <ol className="rt-combined-qa">
              {result.sub_question_results.map((sub) => (
                <li key={sub.sub_question_id} className="rt-combined-qa-item">
                  <p className="rt-combined-q">
                    {sub.sub_question_id}. {sub.question}
                  </p>
                  <p className="rt-combined-a">{sub.final_answer}</p>
                </li>
              ))}
            </ol>
          </section>
        </>
      ) : (
        <div className="rt-advanced">
          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">Provider / projection trace</h3>
            <p className="kgc-input-value">
              {result.trace?.provider_class ?? "unknown"}
              {result.trace?.model ? ` · ${result.trace.model}` : ""}
              {result.trace?.example_id ? ` · ${result.trace.example_id}` : ""}
            </p>
            <pre className="json-dump">{JSON.stringify(result.trace ?? {}, null, 2)}</pre>
          </section>

          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">Metrics</h3>
            <pre className="json-dump">{JSON.stringify(result.metrics ?? {}, null, 2)}</pre>
          </section>

          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">
              Question targets (intent, relations, primary subject)
            </h3>
            <pre className="json-dump">
              {JSON.stringify(
                result.sub_question_results.map((sub) => ({
                  id: sub.sub_question_id,
                  question: sub.question,
                  question_target: sub.question_target,
                  question_target_satisfied: sub.question_target_satisfied,
                  stop_reason: sub.stop_reason,
                })),
                null,
                2,
              )}
            </pre>
          </section>

          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">Base KGc facts</h3>
            <pre className="json-dump">
              {JSON.stringify(result.base_kgc_facts, null, 2)}
            </pre>
          </section>

          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">Working KGc facts</h3>
            <pre className="json-dump">
              {JSON.stringify(result.working_kgc_facts, null, 2)}
            </pre>
          </section>

          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">Working KGc additions</h3>
            <pre className="json-dump">
              {JSON.stringify(result.working_kgc_additions ?? [], null, 2)}
            </pre>
          </section>

          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">Candidate KGc updates</h3>
            <pre className="json-dump">
              {JSON.stringify(result.candidate_kgc_updates, null, 2)}
            </pre>
          </section>

          <section className="kgc-run-inputs-card">
            <h3 className="kgc-section-title">
              Per-sub-question raw iteration history (includes backend indexes)
            </h3>
            {result.sub_question_results.map((sub) => (
              <details key={sub.sub_question_id} className="kgc-expand-details">
                <summary>
                  Q{sub.sub_question_id} — full structured objects
                </summary>
                <pre className="json-dump">{JSON.stringify(sub, null, 2)}</pre>
              </details>
            ))}
          </section>

          {result.trace?.context_extraction_trace ? (
            <section className="kgc-run-inputs-card">
              <h3 className="kgc-section-title">Context extraction attempts</h3>
              <pre className="json-dump">
                {JSON.stringify(result.trace.context_extraction_trace, null, 2)}
              </pre>
            </section>
          ) : null}
        </div>
      )}
    </div>
  );
}
