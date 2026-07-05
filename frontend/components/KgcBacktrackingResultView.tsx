import type { BacktrackingResult } from "@/lib/api";
import KgcFlowView from "@/components/KgcFlowView";

interface KgcBacktrackingResultViewProps {
  result: BacktrackingResult | null;
  loading: boolean;
}

const KGC_INCOMPLETENESS_NOTE =
  "Note: if KGc misses a fact from the context, the system may mark a correct claim as no evidence. That is a graph extraction limitation we can study later.";

export default function KgcBacktrackingResultView({
  result,
  loading,
}: KgcBacktrackingResultViewProps) {
  if (loading) {
    return (
      <section className="card">
        <p className="loading">Running KGc backtracking…</p>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="card">
        <p className="muted-text">
          Select an example, choose an Answer(0) source, then click Run KGc
          backtracking.
        </p>
      </section>
    );
  }

  return (
    <div className="results-stack">
      <KgcFlowView result={result} />

      <details className="card details-card">
        <summary>Advanced details</summary>
        <div className="details-body">
          <p className="kgc-advanced-notice">{KGC_INCOMPLETENESS_NOTE}</p>
          {result.kgc_extraction_notice ? (
            <p className="kgc-run-notice">{result.kgc_extraction_notice}</p>
          ) : null}
          {result.answer_0_warning ? (
            <p className="kgc-run-warning">{result.answer_0_warning}</p>
          ) : null}
          <h4>KGc reference answer</h4>
          <pre className="json-block">
            {result.kgc_reference_answer ?? result.graph_grounded_answer}
          </pre>
          <h4>Run metadata</h4>
          <pre className="json-block">
            {JSON.stringify(
              {
                answer_0_mode: result.answer_0_mode,
                answer_0_warning: result.answer_0_warning,
                kgc_extraction_notice: result.kgc_extraction_notice,
                stop_reason: result.stop_reason,
                trace: result.trace,
                iteration_history: result.iteration_history,
              },
              null,
              2,
            )}
          </pre>
          <h4>Question</h4>
          <pre className="json-block">{result.question}</pre>
          <h4>Raw context</h4>
          <pre className="json-block">{result.context}</pre>
          <h4>Extracted claims (before alignment)</h4>
          <pre className="json-block">
            {JSON.stringify(result.extracted_claims, null, 2)}
          </pre>
          <h4>Aligned claims (used for eval)</h4>
          <pre className="json-block">
            {JSON.stringify(result.aligned_claims, null, 2)}
          </pre>
          <h4>Full KGc backtracking JSON</h4>
          <pre className="json-block">{JSON.stringify(result, null, 2)}</pre>
        </div>
      </details>
    </div>
  );
}
