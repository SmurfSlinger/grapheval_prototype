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

function stopReasonsSummary(result: DecomposedBacktrackingResult): string {
  return aggregateStopReason(result);
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
    stopReasonsSummary(result) ??
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
  const fromResult =
    result.runtime_seconds ??
    result.elapsed_seconds ??
    null;
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
  const providerRaw = result.trace?.provider_class ?? null;
  const usedProvider = providerRaw
    ? providerRaw.toLowerCase().includes("ollama")
      ? "Ollama"
      : providerRaw
    : null;

  const predicted = benchmarkScore?.predicted_answer ?? result.combined_answer;
  const stopSummary =
    benchmarkScore?.final_stop_reason ?? stopReasonsSummary(result);

  const exactMatch = benchmarkScore?.exact_match ?? null;
  const expectedAnswer = benchmarkScore?.expected_answer ?? null;

  const pipelineResolved = benchmarkScore?.resolved_by_pipeline
    ? true
    : benchmarkScore
      ? false
      : pipelineStatus(result) === "Resolved";

  const pathComplete =
    typeof lastSub?.evidence_path_complete === "boolean"
      ? lastSub.evidence_path_complete
      : Boolean(lastSub?.evidence_path?.complete);

  const evidenceEdges = lastSub?.evidence_path?.evidence_path ?? [];
  const terminalEdge = evidenceEdges.at(-1) ?? null;

  const hops =
    typeof lastSub?.evidence_path_length === "number"
      ? lastSub.evidence_path_length
      : typeof lastSub?.evidence_path?.path_length === "number"
        ? lastSub.evidence_path?.path_length
        : evidenceEdges.length;

  const revisions = result.metrics?.total_revisions ?? 0;

  const configuredCtx =
    typeof result.trace?.configured_num_ctx === "number"
      ? result.trace.configured_num_ctx
      : null;

  const evidenceLines: string[] =
    evidenceEdges.length > 0
      ? [evidenceEdges[0].subject].concat(
          evidenceEdges.flatMap((e) => [
            `→ ${prettyEvidenceRelation(e.relation)}`,
            e.object,
          ]),
        )
      : [];

  const terminalSupportedClaim = (() => {
    if (!terminalEdge) return null;
    const lastIter = lastSub?.iteration_history?.at(-1);
    const evaluated = lastIter?.evaluated_claims ?? [];
    const match = evaluated.find((c) => {
      const triple = c.triple;
      return (
        triple.subject === terminalEdge.subject &&
        triple.relation === terminalEdge.relation &&
        triple.object === terminalEdge.object &&
        c.label.toUpperCase() === "SUPPORTED"
      );
    });
    return match
      ? `${terminalEdge.subject} — ${prettyEvidenceRelation(
          terminalEdge.relation,
        )} — ${terminalEdge.object}`
      : null;
  })();

  const subQuestionCount = result.sub_questions.length;
  const showSubQuestions = subQuestionCount > 1;
  const executionId = result.trace?.execution_id ?? null;
  const benchmarkId = benchmarkScore?.benchmark_id ?? result.trace?.benchmark_id ?? null;
  const questionId = benchmarkScore?.question_id ?? result.trace?.question_id ?? null;

  const workingAdditions = result.working_kgc_additions ?? [];
  const directAdds = workingAdditions.filter(
    (a) => !a.provenance.toLowerCase().includes("derived"),
  ).length;
  const derivedAdds = workingAdditions.filter((a) =>
    a.provenance.toLowerCase().includes("derived"),
  ).length;

  async function copyDebugPath(text: string) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // no-op: clipboard may be blocked in some browsers
    }
  }

  return (
    <section className="results-stack simple-results">
      <div className="simple-final-answer">
        <h2>Answer</h2>
        <p className="simple-final-answer-text">{predicted}</p>

        <p className="simple-meta-line">
          <span>{pipelineResolved ? "Resolved" : "Unresolved"}</span>
          {exactMatch != null ? (
            <span>Exact match: {exactMatch ? "Yes" : "No"}</span>
          ) : null}
          {hops != null ? (
            <span>
              {pathComplete ? "Complete" : "Incomplete"} {hops}-hop path
            </span>
          ) : null}
          <span>{revisions} revision(s)</span>
          {elapsed != null ? <span>Runtime: {formatSeconds(elapsed)}</span> : null}
        </p>

        {benchmarkScore && expectedAnswer && (!pipelineResolved || exactMatch === false) ? (
          <p className="simple-meta-line">
            <span>Expected: {expectedAnswer}</span>
            <span>Failure: {failureCategory(benchmarkScore, result) ?? "unknown"}</span>
          </p>
        ) : null}
      </div>

      <div className="simple-steps">
        <h3>Evidence path</h3>
        {evidenceLines.length > 0 ? (
          <ul className="kgc-evidence-list">
            {evidenceLines.map((line, idx) => (
              <li key={idx} className="kgc-evidence-item">
                {line}
              </li>
            ))}
          </ul>
        ) : (
          <p className="kgc-empty-note">No evidence path available.</p>
        )}
        <p className="kgc-evidence-text">
          {hops} hops · {pathComplete ? "Complete" : "Incomplete"}
        </p>
        {terminalSupportedClaim ? (
          <p className="kgc-evidence-text">Supported claim: {terminalSupportedClaim}</p>
        ) : null}
      </div>

      <div className="simple-steps">
        <h3>Question</h3>
        <p style={{ margin: 0 }}>{result.original_question}</p>
      </div>

      {showSubQuestions ? (
        <div className="simple-steps">
          <h3>Sub-questions</h3>
          {result.sub_question_results.map((row) => {
            const rowTerminal = row.evidence_path?.evidence_path?.at(-1) ?? null;
            return (
              <div key={row.sub_question_id} className="card" style={{ marginBottom: "0.85rem" }}>
                <p style={{ margin: 0 }}>
                  <strong>Q{row.sub_question_id}:</strong> {row.question}
                </p>
                <p style={{ margin: "0.3rem 0 0" }}>
                  Answer: {row.final_answer}
                </p>
                <p className="simple-meta-line" style={{ marginTop: "0.35rem" }}>
                  <span>Status: {row.stop_reason}</span>
                  {typeof row.evidence_path_length === "number" ? (
                    <span>Path length: {row.evidence_path_length}</span>
                  ) : null}
                  {rowTerminal ? (
                    <span>
                      {rowTerminal.subject} —{" "}
                      {prettyEvidenceRelation(rowTerminal.relation)} —{" "}
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
        <h3>Run details</h3>
        <p className="simple-meta-line" style={{ marginTop: 0 }}>
          <span>{usedModel ?? "n/a"}</span>
          <span>{usedProvider ?? "n/a"}</span>
          {configuredCtx != null ? <span>{configuredCtx.toLocaleString()} context</span> : null}
          {elapsed != null ? <span>{formatSeconds(elapsed)}</span> : null}
        </p>
        {result.debug_log_path ? (
          <p className="simple-meta-line">
            <span>Debug log</span>
            <span style={{ fontFamily: "ui-monospace, monospace" }}>{result.debug_log_path}</span>
            <button
              type="button"
              className="btn-link"
              onClick={() => copyDebugPath(result.debug_log_path ?? "")}
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
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Question ID</span>
                <span className="kgc-check-detail-value">
                  {questionId ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Benchmark</span>
                <span className="kgc-check-detail-value">
                  {benchmarkId ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Designed depth</span>
                <span className="kgc-check-detail-value">
                  {benchmarkScore?.hop_count ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Execution ID</span>
                <span className="kgc-check-detail-value">
                  {executionId ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Model</span>
                <span className="kgc-check-detail-value">
                  {usedModel ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Provider</span>
                <span className="kgc-check-detail-value">
                  {usedProvider ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Configured context</span>
                <span className="kgc-check-detail-value">
                  {configuredCtx ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Iteration count</span>
                <span className="kgc-check-detail-value">
                  {result.metrics?.total_iterations ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Revision count</span>
                <span className="kgc-check-detail-value">{revisions}</span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">FACT count</span>
                <span className="kgc-check-detail-value">
                  {result.base_kgc_facts.length}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">CLAIM count</span>
                <span className="kgc-check-detail-value">
                  {result.metrics?.total_claims_evaluated ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Direct FACT additions</span>
                <span className="kgc-check-detail-value">{directAdds}</span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Derived FACT additions</span>
                <span className="kgc-check-detail-value">{derivedAdds}</span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Structured-triple anomalies</span>
                <span className="kgc-check-detail-value">{anomalies.length}</span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Neo4j evaluation source</span>
                <span className="kgc-check-detail-value">
                  {result.trace?.kgc_evaluation_source ?? "n/a"}
                </span>
              </div>
            </div>
            <div className="kgc-check-detail-row">
              <div className="kgc-check-detail-line">
                <span className="kgc-check-detail-key">Stop reason</span>
                <span className="kgc-check-detail-value">{stopSummary}</span>
              </div>
            </div>
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
                copyDebugPath(
                  JSON.stringify(
                    benchmarkScore ? { result, benchmark: benchmarkScore } : result,
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
                benchmarkScore ? { result, benchmark: benchmarkScore } : result,
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
