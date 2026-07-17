import type { DecomposedBacktrackingResult } from "@/lib/api";
import DecomposedKgcFlowView from "@/components/DecomposedKgcFlowView";

interface DecomposedKgcBacktrackingResultViewProps {
  result: DecomposedBacktrackingResult | null;
  loading: boolean;
}

export default function DecomposedKgcBacktrackingResultView({
  result,
  loading,
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
      <DecomposedKgcFlowView result={result} />
      <details className="kgc-expand-details">
        <summary>Full response JSON</summary>
        <pre className="json-dump">{JSON.stringify(result, null, 2)}</pre>
      </details>
    </section>
  );
}
