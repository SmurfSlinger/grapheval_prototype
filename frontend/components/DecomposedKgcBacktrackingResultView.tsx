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
}

function pipelineStatus(result: DecomposedBacktrackingResult): string {
  const stops = result.sub_question_results.map((row) => row.stop_reason);
  if (stops.length === 0) return "No sub-questions";
  if (stops.every((stop) => stop === "resolved")) return "Resolved";
  if (stops.some((stop) => stop.includes("unresolved") || stop === "stalled")) {
    return "Partially unresolved";
  }
  return stops.join(", ");
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

  return (
    <section className="results-stack simple-results">
      <div className="simple-final-answer">
        <h2>Final answer</h2>
        <p className="simple-final-answer-text">{result.combined_answer}</p>
        <p className="simple-meta-line">
          <span>Pipeline status: {pipelineStatus(result)}</span>
          <span>
            Runtime:{" "}
            {typeof result.trace?.configured_num_ctx === "number"
              ? `num_ctx=${result.trace.configured_num_ctx}`
              : "n/a"}
            {result.metrics
              ? ` · ${result.metrics.total_iterations} iteration(s)`
              : ""}
          </span>
        </p>
      </div>

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
          {benchmarkScore ? (
            <ul className="benchmark-score-list">
              <li>
                <strong>Question:</strong> {benchmarkScore.question_id} (hop{" "}
                {benchmarkScore.hop_count})
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
                <strong>Resolved by pipeline:</strong>{" "}
                {benchmarkScore.resolved_by_pipeline ? "yes" : "no"}
              </li>
            </ul>
          ) : null}
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
