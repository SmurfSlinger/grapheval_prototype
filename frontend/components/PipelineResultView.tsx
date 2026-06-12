import type { PipelineMetrics, PipelineResult, StoredClaim } from "@/lib/api";
import AdvancedDetails from "./AdvancedDetails";
import FlaggedTriples from "./FlaggedTriples";
import StoredClaimsPanel from "./StoredClaimsPanel";

interface PipelineResultViewProps {
  result: PipelineResult | null;
  loading: boolean;
  allResults: PipelineResult[];
  selectedId: string | null;
  onSelectResult: (id: string) => void;
  onRefreshNeo4j?: () => void;
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
  allResults,
  selectedId,
  onSelectResult,
  onRefreshNeo4j,
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
        <p className="loading">Select an example and click Run to see results.</p>
      </section>
    );
  }

  const graphAnswer =
    result.graph_feedback_revised_answer ?? result.revised_answer;
  const metrics = result.metrics ?? defaultMetrics(result);
  const revisedContradicted = metrics.graph_revised_contradicted_count ?? 0;
  const revisedNei = metrics.graph_revised_not_enough_info_count ?? 0;
  const revisionChecked =
    metrics.graph_revised_contradicted_count != null &&
    metrics.graph_revised_not_enough_info_count != null;

  return (
    <div className="results-stack">
      <section className="card story-section">
        <h2>Original answer</h2>
        <p className="section-lead">
          The model starts with an answer that may contain unsupported or incorrect
          claims.
        </p>
        <div className="answer-block">{result.initial_answer}</div>
        <div className="context-card">
          <p className="context-label">Trusted context</p>
          <div className="answer-block context-block">{result.context}</div>
        </div>
      </section>

      <section className="card story-section">
        <h2>What the system found</h2>
        <p className="section-lead">
          The pipeline extracts claims as triples, then checks each one against the
          trusted context.
        </p>
        <div className="claim-summary">
          <span className="mini-stat">
            <strong>{metrics.initial_total_triples}</strong> total claims
          </span>
          <span className="badge supported">
            {metrics.initial_supported_count} supported
          </span>
          <span className="badge contradicted">
            {metrics.initial_contradicted_count} contradicted
          </span>
          <span className="badge nei">
            {metrics.initial_not_enough_info_count} not enough info
          </span>
        </div>
        <h3 className="subsection-title">Flagged claims</h3>
        <FlaggedTriples result={result} />
      </section>

      <section className="card story-section">
        <h2>Revised answer</h2>
        <p className="section-lead">
          The answer is revised using feedback tied to the specific bad claims and
          their evidence.
        </p>
        <div className="answer-block revised-answer">
          {graphAnswer ?? result.initial_answer}
        </div>
        {revisionChecked ? (
          revisedContradicted === 0 && revisedNei === 0 ? (
            <p className="success-text">
              No remaining unsupported or contradicted claims found after revision.
            </p>
          ) : (
            <p className="revision-stats">
              After revision: {revisedContradicted} contradicted, {revisedNei} not
              enough info
            </p>
          )
        ) : (
          <p className="revision-stats muted-text">
            No revision was needed — all claims were supported.
          </p>
        )}
      </section>

      <section className="card story-section">
        <h2>Baseline comparison</h2>
        <p className="section-lead">
          Self-correction gets a generic prompt; graph feedback gets the specific
          bad claims and evidence.
        </p>
        <div className="comparison-grid">
          <div className="comparison-panel self-correction">
            <h3>Self-correction baseline</h3>
            <div className="answer-block compact">
              {result.self_corrected_answer ?? "(not run)"}
            </div>
          </div>
          <div className="comparison-panel graph-feedback">
            <h3>Triple-level graph feedback</h3>
            <div className="answer-block compact">
              {graphAnswer ?? "(no revision needed)"}
            </div>
          </div>
        </div>
      </section>

      <StoredClaimsPanel
        selectedExampleId={result.example_id}
        onRefresh={onRefreshNeo4j}
      />

      <AdvancedDetails
        result={result}
        allResults={allResults}
        selectedId={selectedId}
        onSelectResult={onSelectResult}
      />
    </div>
  );
}
