import type { PipelineMetrics, PipelineResult } from "@/lib/api";
import FeedbackPanel from "./FeedbackPanel";
import FlaggedTriples from "./FlaggedTriples";
import SummaryCards from "./SummaryCards";
import TripleTable from "./TripleTable";

interface PipelineResultViewProps {
  result: PipelineResult | null;
  loading: boolean;
}

function defaultMetrics(result: PipelineResult): PipelineMetrics {
  return {
    initial_total_triples: result.extracted_triples.length,
    initial_supported_count: 0,
    initial_contradicted_count: 0,
    initial_not_enough_info_count: 0,
    graph_revision_needed: (result.feedback?.length ?? 0) > 0,
  };
}

export default function PipelineResultView({
  result,
  loading,
}: PipelineResultViewProps) {
  if (loading) {
    return (
      <section className="card">
        <p className="loading">
          Running pipeline… this may take a minute with Ollama.
        </p>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="card muted-card">
        <p className="loading">Run an example to see results.</p>
      </section>
    );
  }

  const graphAnswer =
    result.graph_feedback_revised_answer ?? result.revised_answer;
  const metrics = result.metrics ?? defaultMetrics(result);
  const graphRevisedTriples = result.graph_revised_triples ?? [];
  const graphRevisedVerification =
    result.graph_revised_verification_results ?? [];

  return (
    <div className="results-stack">
      <SummaryCards metrics={metrics} exampleId={result.example_id} />

      <section className="card">
        <h3 className="section-title">Correction comparison</h3>
        <div className="comparison-grid">
          <div className="comparison-panel self-correction">
            <h4>Self-correction baseline</h4>
            <p className="comparison-hint">Generic check against context</p>
            <div className="answer-block compact">
              {result.self_corrected_answer ?? "(not run)"}
            </div>
          </div>
          <div className="comparison-panel graph-feedback">
            <h4>Triple-level graph feedback</h4>
            <p className="comparison-hint">
              Revision using specific bad triples
            </p>
            <div className="answer-block compact">
              {graphAnswer ?? "(no revision needed)"}
            </div>
          </div>
        </div>
      </section>

      <section className="card">
        <h3 className="section-title">Flagged triples</h3>
        <FlaggedTriples result={result} />
      </section>

      <details className="card details-card">
        <summary>Show full details</summary>
        <div className="details-body">
          <h4>Question</h4>
          <div className="answer-block compact">{result.question}</div>

          <h4>Trusted context</h4>
          <div className="answer-block compact context-block">
            {result.context}
          </div>

          <h4>Initial answer</h4>
          <div className="answer-block compact">{result.initial_answer}</div>

          <h4>All extracted triples</h4>
          <TripleTable
            triples={result.extracted_triples}
            verificationResults={result.verification_results}
          />

          <h4>Graph-feedback items</h4>
          <FeedbackPanel feedback={result.feedback} />

          {graphRevisedTriples.length > 0 && (
            <>
              <h4>Triples after graph-feedback revision</h4>
              <TripleTable
                triples={graphRevisedTriples}
                verificationResults={graphRevisedVerification}
              />
            </>
          )}
        </div>
      </details>
    </div>
  );
}
