import type { PipelineResult } from "@/lib/api";
import FeedbackPanel from "./FeedbackPanel";
import TripleTable from "./TripleTable";

interface PipelineResultViewProps {
  result: PipelineResult | null;
  loading: boolean;
}

export default function PipelineResultView({
  result,
  loading,
}: PipelineResultViewProps) {
  if (loading) {
    return (
      <section className="card">
        <h2>Results</h2>
        <p className="loading">Running pipeline… this may take a minute with Ollama.</p>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="card">
        <h2>Results</h2>
        <p className="loading">Run an example to see pipeline output.</p>
      </section>
    );
  }

  const counts = result.verification_results.reduce(
    (acc, vr) => {
      acc[vr.label] = (acc[vr.label] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <section className="card">
      <h2>Results — {result.example_id}</h2>

      <p>
        <strong>Triples:</strong> {result.extracted_triples.length}
        {" · "}
        <span className="badge supported">SUPPORTED {counts.SUPPORTED ?? 0}</span>
        {" "}
        <span className="badge contradicted">
          CONTRADICTED {counts.CONTRADICTED ?? 0}
        </span>
        {" "}
        <span className="badge nei">
          NOT_ENOUGH_INFO {counts.NOT_ENOUGH_INFO ?? 0}
        </span>
      </p>

      <h3>Initial answer</h3>
      <div className="answer-block">{result.initial_answer}</div>

      <h3>Extracted triples</h3>
      <TripleTable result={result} />

      <h3>Feedback</h3>
      <FeedbackPanel feedback={result.feedback} />

      <h3>Revised answer</h3>
      <div className="answer-block">
        {result.revised_answer ?? "(no revision needed)"}
      </div>
    </section>
  );
}
