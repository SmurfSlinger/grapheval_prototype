import type {
  BenchmarkRunScore,
  DecomposedBacktrackingResult,
} from "@/lib/api";
import DecomposedKgcFlowView from "@/components/DecomposedKgcFlowView";

interface DecomposedKgcBacktrackingResultViewProps {
  result: DecomposedBacktrackingResult | null;
  loading: boolean;
  benchmarkScore?: BenchmarkRunScore | null;
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
        <p className="kgc-empty-note">Select an example and run.</p>
      </section>
    );
  }

  return (
    <section className="results-stack">
      {benchmarkScore ? (
        <div className="card benchmark-score-card">
          <h3>Benchmark score (post-inference)</h3>
          <p className="controls-hint">
            Textual matching is separate from pipeline resolution. Expected
            answers were not supplied to inference.
          </p>
          <ul className="benchmark-score-list">
            <li>
              <strong>Question:</strong> {benchmarkScore.question_id} (hop{" "}
              {benchmarkScore.hop_count})
            </li>
            <li>
              <strong>Expected answer:</strong> {benchmarkScore.expected_answer}
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
        </div>
      ) : null}
      <DecomposedKgcFlowView result={result} />
      <details className="kgc-expand-details">
        <summary>Full response JSON</summary>
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
