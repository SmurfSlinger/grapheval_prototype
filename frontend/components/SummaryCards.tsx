import type { PipelineMetrics } from "@/lib/api";

interface SummaryCardsProps {
  metrics: PipelineMetrics;
  exampleId: string;
}

export default function SummaryCards({ metrics, exampleId }: SummaryCardsProps) {
  return (
    <div className="overview-card">
      <h2 className="overview-title">Results — {exampleId}</h2>

      <div className="overview-section">
        <p className="overview-label">Initial answer had:</p>
        <div className="summary-cards compact">
          <span className="mini-stat">
            <strong>{metrics.initial_total_triples}</strong> triples
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
          {metrics.graph_revision_needed && (
            <span className="badge revision">revision needed</span>
          )}
        </div>
      </div>

      {metrics.graph_revised_contradicted_count != null && (
        <div className="overview-section">
          <p className="overview-label">After graph-feedback revision:</p>
          <div className="summary-cards compact">
            <span className="badge contradicted">
              {metrics.graph_revised_contradicted_count} contradicted
            </span>
            <span className="badge nei">
              {metrics.graph_revised_not_enough_info_count ?? 0} not enough info
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
