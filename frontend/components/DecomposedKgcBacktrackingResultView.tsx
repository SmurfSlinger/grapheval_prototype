"use client";

import type {
  BenchmarkRunScore,
  DecomposedBacktrackingResult,
} from "@/lib/api";
import DecomposedKgcFlowView from "@/components/DecomposedKgcFlowView";

interface DecomposedKgcBacktrackingResultViewProps {
  result: DecomposedBacktrackingResult | null;
  loading: boolean;
  benchmarkScore?: BenchmarkRunScore | null;
  elapsedSeconds?: number | null;
}

function aggregateStopReason(result: DecomposedBacktrackingResult): string {
  const stops = result.sub_question_results.map((row) => row.stop_reason);
  if (stops.length === 0) return "NO_SUB_QUESTIONS";
  const resolved = (stop: string) =>
    stop === "RESOLVED" || stop === "resolved";
  if (stops.every(resolved)) return "RESOLVED";
  if (stops.some(resolved)) return "PARTIALLY_UNRESOLVED";
  const priority = [
    "UNRESOLVED_TARGET_NOT_SATISFIED",
    "UNRESOLVED_NO_EVIDENCE",
    "STALLED",
    "NO_CLAIMS_EXTRACTED",
    "GENERATION_FAILED",
    "MAX_ITERATIONS",
  ];
  for (const candidate of priority) {
    if (stops.some((stop) => stop.toUpperCase() === candidate)) {
      return candidate;
    }
  }
  return stops[stops.length - 1] ?? "n/a";
}

function pipelineStatus(result: DecomposedBacktrackingResult): string {
  const aggregate = aggregateStopReason(result);
  if (aggregate === "RESOLVED") return "Resolved";
  if (aggregate === "NO_SUB_QUESTIONS") return "No sub-questions";
  if (aggregate === "PARTIALLY_UNRESOLVED") return "Partially unresolved";
  if (aggregate.toLowerCase().includes("unresolved") || aggregate === "STALLED") {
    return "Unresolved";
  }
  return aggregate;
}

function failureCategory(
  score: BenchmarkRunScore,
  result: DecomposedBacktrackingResult,
): string | null {
  if (score.failure_category) return score.failure_category;
  if (score.resolved_by_pipeline) return null;
  if (score.contains_expected_answer) {
    return "answer_matched_textually_but_pipeline_unresolved";
  }
  const stop = (
    score.final_stop_reason ??
    aggregateStopReason(result) ??
    ""
  ).toLowerCase();
  if (stop.includes("target_not_satisfied")) return "target_not_satisfied";
  if (stop.includes("no_evidence")) return "unresolved_no_evidence";
  if (stop.includes("no_claims")) return "no_claims_extracted";
  if (stop.includes("max_iterations")) {
    return "contradiction_or_uncertainty_remained";
  }
  return "pipeline_unresolved";
}

function elapsedFromResult(
  result: DecomposedBacktrackingResult,
  elapsedSeconds: number | null | undefined,
): number | null {
  const fromResult = result.runtime_seconds ?? result.elapsed_seconds ?? null;
  if (typeof fromResult === "number" && Number.isFinite(fromResult)) {
    return fromResult;
  }
  if (typeof elapsedSeconds === "number" && Number.isFinite(elapsedSeconds)) {
    return elapsedSeconds;
  }
  return null;
}

function formatSeconds(seconds: number): string {
  if (seconds < 10) return `${seconds.toFixed(2)}s`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const rem = seconds - mins * 60;
  return `${mins}m ${rem.toFixed(0)}s`;
}

function prettyEvidenceRelation(relation: string): string {
  const r = relation.trim().toLowerCase();
  if (r === "crewed_by" || r === "was_crewed_by") return "was crewed by";
  if (r === "born_in" || r === "was_born_in") return "was born in";
  if (r === "located_in" || r === "is_located_in") return "is located in";
  return r.replace(/_/g, " ");
}

function prettyProvider(providerRaw: string | null | undefined): string | null {
  if (!providerRaw) return null;
  const lower = providerRaw.toLowerCase();
  if (lower.includes("ollama")) return "Ollama";
  if (lower.includes("mock")) return "Mock";
  return providerRaw;
}

function pluralize(count: number, singular: string, plural = `${singular}S`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function DetailRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="kgc-check-detail-row">
      <div className="kgc-check-detail-line">
        <span className="kgc-check-detail-key">{label}</span>
        <span className="kgc-check-detail-value">{value}</span>
      </div>
    </div>
  );
}

export default function DecomposedKgcBacktrackingResultView({
  result,
  loading,
  benchmarkScore = null,
  elapsedSeconds = null,
}: DecomposedKgcBacktrackingResultViewProps) {
  if (loading) {
    return (
      <section className="results-stack">
        <p className="kgc-empty-note">Running…</p>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="results-stack">
        <p className="kgc-empty-note">
          Choose a source above and press Run.
        </p>
      </section>
    );
  }

  const lastSub = result.sub_question_results.at(-1) ?? null;
  const anomalies = result.structured_triple_anomalies ?? [];
  const elapsed = elapsedFromResult(result, elapsedSeconds);

  const usedModel = result.trace?.model ?? null;
  const usedProvider = prettyProvider(result.trace?.provider_class);

  const predicted = benchmarkScore?.predicted_answer ?? result.combined_answer;
  const stopSummary =
    benchmarkScore?.final_stop_reason ?? aggregateStopReason(result);

  const exactMatch = benchmarkScore?.exact_match ?? null;
  const expectedAnswer = benchmarkScore?.expected_answer ?? null;
  const containsExpected = benchmarkScore?.contains_expected_answer ?? null;

  const pipelineResolved = benchmarkScore?.resolved_by_pipeline
    ? true
    : benchmarkScore
      ? false
      : pipelineStatus(result) === "Resolved";

  const subQuestionCount = result.sub_questions.length;
  const showSubQuestions = subQuestionCount > 1;

  // Single-question runs use that path as the run evidence path.
  // Multi-question runs keep aggregate summary separate from per-sub paths.
  const pathSub = showSubQuestions ? null : lastSub;
  const pathComplete =
    pathSub == null
      ? null
      : typeof pathSub.evidence_path_complete === "boolean"
        ? pathSub.evidence_path_complete
        : Boolean(pathSub.evidence_path?.complete);

  const evidenceEdges = pathSub?.evidence_path?.evidence_path ?? [];
  const terminalEdge = evidenceEdges.at(-1) ?? null;

  const hops =
    pathSub == null
      ? null
      : typeof pathSub.evidence_path_length === "number"
        ? pathSub.evidence_path_length
        : typeof pathSub.evidence_path?.path_length === "number"
          ? pathSub.evidence_path.path_length
          : evidenceEdges.length;

  const revisions = result.metrics?.total_revisions ?? 0;
  const configuredCtx =
    typeof result.trace?.configured_num_ctx === "number"
      ? result.trace.configured_num_ctx
      : null;

  const factCount = result.base_kgc_facts.length;
  const finalSupported = result.metrics?.final_supported ?? 0;
  const finalContradicted = result.metrics?.final_contradicted ?? 0;
  const finalNoEvidence = result.metrics?.final_no_evidence ?? 0;
  const finalClaimCount = finalSupported + finalContradicted + finalNoEvidence;

  const evidenceLines: string[] =
    evidenceEdges.length > 0
      ? [evidenceEdges[0].subject].concat(
          evidenceEdges.flatMap((e) => [
            `→ ${prettyEvidenceRelation(e.relation)}`,
            e.object,
          ]),
        )
      : [];

  const terminalClaim = (() => {
    if (!terminalEdge) return null;
    const lastIter = pathSub?.iteration_history?.at(-1);
    const evaluated = lastIter?.evaluated_claims ?? [];
    const match = evaluated.find((c) => {
      const triple = c.triple;
      return (
        triple.subject === terminalEdge.subject &&
        triple.relation === terminalEdge.relation &&
        triple.object === terminalEdge.object
      );
    });
    return {
      text: `${terminalEdge.subject} — ${prettyEvidenceRelation(
        terminalEdge.relation,
      )} → ${terminalEdge.object}`,
      label: (match?.label ?? "n/a").toUpperCase(),
    };
  })();

  const executionId =
    result.execution_id ?? result.trace?.execution_id ?? null;
  const benchmarkId =
    benchmarkScore?.benchmark_id ?? result.trace?.benchmark_id ?? null;
  const questionId =
    benchmarkScore?.question_id ?? result.trace?.question_id ?? null;
  const designedDepth = benchmarkScore?.hop_count ?? null;

  const workingAdditions = result.working_kgc_additions ?? [];
  const directAdds = workingAdditions.filter(
    (a) => !a.provenance.toLowerCase().includes("derived"),
  ).length;
  const derivedAdds = workingAdditions.filter((a) =>
    a.provenance.toLowerCase().includes("derived"),
  ).length;

  async function copyText(text: string) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // clipboard may be blocked
    }
  }

  const inputBits = [
    usedModel,
    usedProvider,
    configuredCtx != null ? `${configuredCtx.toLocaleString()} context` : null,
    `${pluralize(factCount, "trusted FACT", "trusted FACTS")}`,
  ].filter(Boolean);

  return (
    <section className="results-stack simple-results">
      <div className="simple-steps">
        <h3>Experiment</h3>
        {(questionId || designedDepth != null) && (
          <p style={{ margin: 0 }}>
            {[
              questionId,
              designedDepth != null ? `designed depth ${designedDepth}` : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        )}
        <p style={{ margin: "0.35rem 0 0" }}>{result.original_question}</p>
        {inputBits.length > 0 ? (
          <p style={{ margin: "0.35rem 0 0", color: "var(--muted)", fontSize: "0.92rem" }}>
            {inputBits.join(" · ")}
          </p>
        ) : null}
      </div>

      <div className="simple-final-answer">
        <h2>Output</h2>
        <p className="kgc-empty-note" style={{ marginBottom: "0.25rem" }}>
          Answer
        </p>
        <p className="simple-final-answer-text">{predicted}</p>

        {benchmarkScore && expectedAnswer ? (
          <p className="simple-meta-line">
            <span>Expected for scoring: {expectedAnswer}</span>
          </p>
        ) : null}

        <p className="simple-meta-line">
          {exactMatch != null ? (
            <span>Exact match: {exactMatch ? "Yes" : "No"}</span>
          ) : null}
          <span>Pipeline: {pipelineResolved ? "Resolved" : "Unresolved"}</span>
          {elapsed != null ? <span>Runtime: {formatSeconds(elapsed)}</span> : null}
          <span>Revisions: {revisions}</span>
        </p>

        {benchmarkScore && (!pipelineResolved || exactMatch === false) ? (
          <p className="simple-meta-line">
            <span>
              Failure: {failureCategory(benchmarkScore, result) ?? "unknown"}
            </span>
            {containsExpected != null ? (
              <span>
                Contains expected: {containsExpected ? "Yes" : "No"}
              </span>
            ) : null}
            <span>Stop: {stopSummary}</span>
          </p>
        ) : null}
      </div>

      <div className="simple-steps">
        <h3>Verification{showSubQuestions ? " (aggregate)" : ""}</h3>
        <p className="kgc-evidence-text" style={{ marginTop: 0 }}>
          Trusted context → {pluralize(factCount, "FACT")}
        </p>
        <p className="kgc-evidence-text">
          Model answer → {pluralize(finalClaimCount, "CLAIM")}
        </p>
        <p className="kgc-evidence-text">
          CLAIM evaluation → {finalSupported} supported · {finalContradicted}{" "}
          contradicted · {finalNoEvidence} no evidence
        </p>
        {!showSubQuestions ? (
          pipelineResolved ? (
            <p className="kgc-evidence-text">
              Trusted evidence path → {hops ?? 0} hops ·{" "}
              {pathComplete ? "Complete" : "Incomplete"}
            </p>
          ) : (
            <>
              <p className="kgc-evidence-text">
                Claim evidence path → {hops ?? 0} hops ·{" "}
                {pathComplete
                  ? `Complete to ${
                      terminalEdge?.object
                        ?? pathSub?.evidence_path?.terminal_claim?.object
                        ?? "terminal claim"
                    }`
                  : "Incomplete"}
              </p>
              <p className="kgc-evidence-text">
                Question answer target →{" "}
                {pathSub?.question_target_satisfied
                  ? "Satisfied"
                  : "Not satisfied"}
              </p>
            </>
          )
        ) : (
          <p className="kgc-evidence-text">
            Aggregate of {subQuestionCount} sub-questions — see cards below for
            per-question paths
          </p>
        )}
        <p className="controls-hint" style={{ marginTop: "0.45rem" }}>
          FACTS come from trusted context. CLAIMS come from the model answer and
          remain CLAIMS after evaluation.
        </p>

        {!showSubQuestions && terminalClaim ? (
          <p className="kgc-evidence-text" style={{ marginTop: "0.65rem" }}>
            {terminalClaim.text}
            <br />
            {terminalClaim.label}
          </p>
        ) : null}

        {!showSubQuestions ? (
          evidenceLines.length > 0 ? (
            <ul className="kgc-evidence-list" style={{ marginTop: "0.55rem" }}>
              {evidenceLines.map((line, idx) => (
                <li key={idx} className="kgc-evidence-item">
                  {line}
                </li>
              ))}
            </ul>
          ) : (
            <p className="kgc-empty-note">No evidence path available.</p>
          )
        ) : null}
      </div>

      {showSubQuestions ? (
        <div className="simple-steps">
          <h3>Sub-questions</h3>
          {result.sub_question_results.map((row) => {
            const rowEdges = row.evidence_path?.evidence_path ?? [];
            const rowTerminal = rowEdges.at(-1) ?? null;
            const rowLen =
              typeof row.evidence_path_length === "number"
                ? row.evidence_path_length
                : row.evidence_path?.path_length ?? rowEdges.length;
            const rowComplete =
              typeof row.evidence_path_complete === "boolean"
                ? row.evidence_path_complete
                : Boolean(row.evidence_path?.complete);
            return (
              <div
                key={row.sub_question_id}
                className="card"
                style={{ marginBottom: "0.85rem" }}
              >
                <p style={{ margin: 0 }}>
                  <strong>Q{row.sub_question_id}:</strong> {row.question}
                </p>
                <p style={{ margin: "0.3rem 0 0" }}>Answer: {row.final_answer}</p>
                <p className="simple-meta-line" style={{ marginTop: "0.35rem" }}>
                  <span>Status: {row.stop_reason}</span>
                  <span>
                    Path: {rowLen} · {rowComplete ? "Complete" : "Incomplete"}
                  </span>
                  {rowTerminal ? (
                    <span>
                      {rowTerminal.subject} —{" "}
                      {prettyEvidenceRelation(rowTerminal.relation)} →{" "}
                      {rowTerminal.object}
                    </span>
                  ) : null}
                </p>
              </div>
            );
          })}
        </div>
      ) : null}

      <div className="simple-steps">
        <h3>Traceability</h3>
        <p className="simple-meta-line" style={{ marginTop: 0 }}>
          <span>{usedModel ?? "n/a"}</span>
          <span>{usedProvider ?? "n/a"}</span>
          {configuredCtx != null ? (
            <span>{configuredCtx.toLocaleString()} context</span>
          ) : null}
          {executionId ? <span>Execution: {executionId}</span> : null}
        </p>
        {result.debug_log_path ? (
          <p className="simple-meta-line">
            <span>Debug log</span>
            <span style={{ fontFamily: "ui-monospace, monospace" }}>
              {result.debug_log_path}
            </span>
            <button
              type="button"
              className="btn-link"
              onClick={() => copyText(result.debug_log_path ?? "")}
            >
              Copy
            </button>
          </p>
        ) : null}
      </div>

      <details className="kgc-expand-details">
        <summary>Technical details</summary>
        <div className="simple-research-details">
          <div className="kgc-check-detail-list">
            <DetailRow label="Question ID" value={questionId ?? "n/a"} />
            <DetailRow label="Benchmark" value={benchmarkId ?? "n/a"} />
            <DetailRow
              label="Designed depth"
              value={designedDepth ?? "n/a"}
            />
            <DetailRow label="Execution ID" value={executionId ?? "n/a"} />
            <DetailRow label="Model" value={usedModel ?? "n/a"} />
            <DetailRow label="Provider" value={usedProvider ?? "n/a"} />
            <DetailRow
              label="Configured context"
              value={configuredCtx ?? "n/a"}
            />
            <DetailRow
              label="Total iterations"
              value={result.metrics?.total_iterations ?? "n/a"}
            />
            <DetailRow label="Revision count" value={revisions} />
            <DetailRow label="Base FACT count" value={factCount} />
            <DetailRow label="Final CLAIM count" value={finalClaimCount} />
            <DetailRow label="Direct FACT additions" value={directAdds} />
            <DetailRow label="Derived FACT additions" value={derivedAdds} />
            <DetailRow label="Anomaly count" value={anomalies.length} />
            <DetailRow
              label="Neo4j evaluation source"
              value={result.trace?.kgc_evaluation_source ?? "n/a"}
            />
            <DetailRow label="Aggregate stop reason" value={stopSummary} />
            <DetailRow
              label="Contains expected"
              value={
                containsExpected == null
                  ? "n/a"
                  : containsExpected
                    ? "Yes"
                    : "No"
              }
            />
            <DetailRow
              label="Expected answer source"
              value="benchmark scoring only"
            />
          </div>
        </div>
      </details>

      <details className="kgc-expand-details">
        <summary>Raw research trace</summary>
        <div className="simple-research-details">
          <details>
            <summary>Trace UI</summary>
            <DecomposedKgcFlowView result={result} />
          </details>

          <details>
            <summary>Raw JSON</summary>
            <button
              type="button"
              className="btn-link"
              style={{ marginTop: "0.3rem" }}
              onClick={() =>
                copyText(
                  JSON.stringify(
                    benchmarkScore
                      ? { result, benchmark: benchmarkScore }
                      : result,
                    null,
                    2,
                  ),
                )
              }
            >
              Copy JSON
            </button>
            <pre
              className="json-block"
              style={{ marginTop: "0.5rem", overflowY: "auto" }}
            >
              {JSON.stringify(
                benchmarkScore
                  ? { result, benchmark: benchmarkScore }
                  : result,
                null,
                2,
              )}
            </pre>
          </details>
        </div>
      </details>
    </section>
  );
}
