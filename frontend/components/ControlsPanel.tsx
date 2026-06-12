import type { ExampleSummary, Provider } from "@/lib/api";

interface ControlsPanelProps {
  provider: Provider;
  model: string;
  examples: ExampleSummary[];
  selectedId: string | null;
  running: boolean;
  onProviderChange: (provider: Provider) => void;
  onModelChange: (model: string) => void;
  onSelectExample: (id: string) => void;
  onRun: () => void;
  onRunAll: () => void;
}

export default function ControlsPanel({
  provider,
  model,
  examples,
  selectedId,
  running,
  onProviderChange,
  onModelChange,
  onSelectExample,
  onRun,
  onRunAll,
}: ControlsPanelProps) {
  return (
    <section className="card controls-card">
      <div className="controls-grid">
        <label>
          Provider
          <select
            value={provider}
            onChange={(e) => onProviderChange(e.target.value as Provider)}
          >
            <option value="mock">mock</option>
            <option value="ollama">ollama</option>
          </select>
        </label>
        <label>
          Model
          <input
            type="text"
            value={model}
            onChange={(e) => onModelChange(e.target.value)}
            disabled={provider === "mock"}
            placeholder="gemma4:e2b"
          />
        </label>
        <label className="controls-example">
          Example
          <select
            value={selectedId ?? ""}
            onChange={(e) => onSelectExample(e.target.value)}
            disabled={examples.length === 0}
          >
            {examples.length === 0 && <option value="">Loading…</option>}
            {examples.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.id}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="row controls-actions">
        <button type="button" onClick={onRun} disabled={!selectedId || running}>
          {running ? "Running…" : "Run"}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={onRunAll}
          disabled={running || examples.length === 0}
        >
          {running ? "Running…" : "Run all"}
        </button>
      </div>
      {provider === "ollama" && (
        <p className="controls-hint">
          Requires <code>ollama serve</code> and <code>ollama pull {model}</code>
        </p>
      )}
    </section>
  );
}
