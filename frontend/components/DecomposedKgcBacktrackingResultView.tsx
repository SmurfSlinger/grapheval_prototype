import type {
  BenchmarkRunScore,
  DecomposedBacktrackingResult,
  SubQuestionResult,
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

function finalStopReason(result: DecomposedBacktrackingResult): string | null {
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
    finalStopReason(result) ??
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

function stepSummaries(result: DecomposedBacktrackingResult): string[] {
  const subCount = result.sub_questions.length;
  const factCount = result.base_kgc_facts.length;
  const claimCount = result.sub_question_results.reduce(
    (total, row) =>
      total +
      (row.iteration_history?.at(-1)?.evaluated_claims?.length ??
        row.supported_count + row.contradicted_count + row.no_evidence_count),
    0,
  );
  const supported = result.metrics?.final_supported ?? 0;
  const contradicted = result.metrics?.final_contradicted ?? 0;
  const noEvidence = result.metrics?.final_no_evidence ?? 0;
  const revisions = result.metrics?.total_revisions ?? 0;

  return [
    `Split the compound question into ${subCount} sub-question${subCount === 1 ? "" : "s"}.`,
    `Extracted ${factCount} trusted FACT triple${factCount === 1 ? "" : "s"} from context.`,
    `Generated ${claimCount} answer CLAIM triple${claimCount === 1 ? "" : "s"} across sub-questions.`,
    `Compared claims against working FACTS: ${supported} supported, ${contradicted} contradicted, ${noEvidence} no evidence.`,
    revisions > 0
      ? `Applied ${revisions} revision pass${revisions === 1 ? "" : "es"} before combining the final answer.`
      : "No revision was required before combining the final answer.",
  ];
}

function claimLines(row: SubQuestionResult): string[] {
  const last = row.iteration_history?.at(-1);
  if (!last?.evaluated_claims?.length) return [];
  return last.evaluated_claims.map(
    (claim) =>
      `(${claim.triple.subject}, ${claim.triple.relation}, ${claim.triple.object}) → ${claim.label}`,
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

  const steps = stepSummaries(result);
  const anomalies = result.structured_triple_anomalies ?? [];
  const elapsed = elapsedFromResult(result, elapsedSeconds);
  const usedModel = result.trace?.model ?? null;
  const usedProvider =
    result.trace?.provider_class ??
    (result.trace?.stage_providers
      ? Object.values(result.trace.stage_providers)[0]
      : null);
  const predicted =
    benchmarkScore?.predicted_answer ?? result.combined_answer;
  const stopSummary =
    benchmarkScore?.final_stop_reason ?? stopReasonsSummary(result);

  return (
    <section className="results-stack simple-results">
      <div className="simple-final-answer">
        <h2>Final answer</h2>
        <p className="simple-final-answer-text">{result.combined_answer}</p>
        <p className="simple-meta-line">
          <span>Pipeline status: {pipelineStatus(result)}</span>
          <span>Stop reason: {stopSummary}</span>
        </p>
        <p className="simple-meta-line">
          {usedModel || usedProvider ? (
            <span>
              Model used: {usedModel ?? "n/a"}
              {usedProvider ? ` · ${usedProvider}` : ""}
            </span>
          ) : null}
          {typeof result.trace?.configured_num_ctx === "number" ? (
            <span>
              Configured context length (num_ctx):{" "}
              {result.trace.configured_num_ctx}
            </span>
          ) : null}
          {elapsed != null ? (
            <span>Elapsed runtime: {formatSeconds(elapsed)}</span>
          ) : null}
          {result.metrics ? (
            <span>{result.metrics.total_iterations} iteration(s)</span>
          ) : null}
        </p>
        {result.debug_log_path ? (
          <p className="simple-meta-line">
            <span>Debug log: {result.debug_log_path}</span>
          </p>
        ) : null}
      </div>

      {benchmarkScore ? (
        <div className="simple-steps">
          <h3>Benchmark score</h3>
          <ul className="benchmark-score-list">
            <li>
              <strong>Question:</strong> {benchmarkScore.question_id} (hop{" "}
              {benchmarkScore.hop_count})
            </li>
            <li>
              <strong>Hop depth:</strong> {benchmarkScore.hop_count}
            </li>
            <li>
              <strong>Predicted:</strong> {predicted}
            </li>
            <li>
              <strong>Expected:</strong> {benchmarkScore.expected_answer}
            </li>
            <li>
              <strong>Exact match:</strong>{" "}
              {benchmarkScore.exact_match ? "yes" : "no"}
            </li>
            <li>
              <strong>Contains expected:</strong>{" "}
              {benchmarkScore.contains_expected_answer ? "yes" : "no"}
            </li>
            <li>
              <strong>Pipeline resolved:</strong>{" "}
              {benchmarkScore.resolved_by_pipeline ? "yes" : "no"}
            </li>
            <li>
              <strong>Stop reason:</strong> {stopSummary}
            </li>
            <li>
              <strong>Failure category:</strong>{" "}
              {failureCategory(benchmarkScore, result) ?? "none"}
            </li>
          </ul>
        </div>
      ) : null}

      <div className="simple-steps">
        <h3>Step-by-step</h3>
        <ol>
          <li>
            <strong>Step 1 — Question decomposition</strong>
            <p>{steps[0]}</p>
          </li>
          <li>
            <strong>Step 2 — Trusted facts extracted</strong>
            <p>{steps[1]}</p>
          </li>
          <li>
            <strong>Step 3 — Claims generated</strong>
            <p>{steps[2]}</p>
          </li>
          <li>
            <strong>Step 4 — Claims compared</strong>
            <p>{steps[3]}</p>
          </li>
          <li>
            <strong>Step 5 — Answer revised</strong>
            <p>{steps[4]}</p>
          </li>
        </ol>
      </div>

      <details className="kgc-expand-details">
        <summary>Research details</summary>
        <div className="simple-research-details">
          <h4>Sub-questions</h4>
          <ul>
            {result.sub_question_results.map((row) => (
              <li key={row.sub_question_id}>
                <strong>
                  Q{row.sub_question_id}: {row.question}
                </strong>
                <div>Stop: {row.stop_reason}</div>
                <div>Answer: {row.final_answer}</div>
                {claimLines(row).map((line) => (
                  <div key={line} className="mono-cell">
                    {line}
                  </div>
                ))}
              </li>
            ))}
          </ul>
          <h4>Structured FACTS</h4>
          <ul>
            {result.base_kgc_facts.map((fact, index) => (
              <li key={`${fact.subject}-${fact.relation}-${index}`}>
                ({fact.subject}, {fact.relation}, {fact.object})
              </li>
            ))}
          </ul>
        </div>
      </details>

      <details className="kgc-expand-details">
        <summary>Developer debug</summary>
        <div className="simple-research-details">
          <p>
            <strong>Debug log path:</strong>{" "}
            {result.debug_log_path ?? "(disabled — set GRAPHEVAL_DEBUG_LOGS=true)"}
          </p>
          <p>
            <strong>Neo4j evaluation source:</strong>{" "}
            {result.trace?.kgc_evaluation_source ?? "n/a"}
          </p>
          {typeof result.trace?.configured_num_ctx === "number" ? (
            <p>
              <strong>Configured context length (num_ctx):</strong>{" "}
              {result.trace.configured_num_ctx}
            </p>
          ) : null}
          <p>
            <strong>Structured-triple anomalies:</strong> {anomalies.length}
          </p>
          {anomalies.length > 0 ? (
            <pre className="json-dump">{JSON.stringify(anomalies, null, 2)}</pre>
          ) : null}
          <details>
            <summary>Full Research Trace</summary>
            <DecomposedKgcFlowView result={result} />
          </details>
        </div>
      </details>

      <details className="kgc-expand-details">
        <summary>Raw JSON</summary>
        <pre className="json-dump">
          {JSON.stringify(
            benchmarkScore ? { result, benchmark: benchmarkScore } : result,
            null,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}
