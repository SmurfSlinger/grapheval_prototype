import type { PipelineResult } from "@/lib/api";

interface ResultsListProps {
  results: PipelineResult[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function ResultsList({
  results,
  selectedId,
  onSelect,
}: ResultsListProps) {
  if (results.length === 0) return null;

  return (
    <section className="card">
      <h2>Run-all summary ({results.length})</h2>
      <div className="results-table-wrap">
        <table className="results-table">
          <thead>
            <tr>
              <th>Example</th>
              <th>Triples</th>
              <th>Contradicted</th>
              <th>NEI</th>
              <th>Remaining C</th>
              <th>Remaining NEI</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => {
              const m = result.metrics;
              return (
                <tr
                  key={result.example_id}
                  className={
                    selectedId === result.example_id ? "selected-row" : ""
                  }
                >
                  <td>
                    <strong>{result.example_id}</strong>
                  </td>
                  <td>{m.initial_total_triples}</td>
                  <td>{m.initial_contradicted_count}</td>
                  <td>{m.initial_not_enough_info_count}</td>
                  <td>{m.graph_revised_contradicted_count ?? "—"}</td>
                  <td>{m.graph_revised_not_enough_info_count ?? "—"}</td>
                  <td>
                    <button
                      type="button"
                      className="btn-small"
                      onClick={() => onSelect(result.example_id)}
                    >
                      View
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
