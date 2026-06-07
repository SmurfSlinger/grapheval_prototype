import type { ExampleSummary } from "@/lib/api";

interface ExampleSelectorProps {
  examples: ExampleSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onRun: () => void;
  running: boolean;
}

export default function ExampleSelector({
  examples,
  selectedId,
  onSelect,
  onRun,
  running,
}: ExampleSelectorProps) {
  return (
    <section className="card">
      <h2>Example selector</h2>
      {examples.length === 0 ? (
        <p className="loading">Loading examples…</p>
      ) : (
        <ul className="example-list">
          {examples.map((example) => (
            <li
              key={example.id}
              className={`example-item${selectedId === example.id ? " selected" : ""}`}
              onClick={() => onSelect(example.id)}
            >
              <strong>{example.id}</strong>
              <span>{example.question}</span>
            </li>
          ))}
        </ul>
      )}
      <div style={{ marginTop: "0.75rem" }}>
        <button
          type="button"
          onClick={onRun}
          disabled={!selectedId || running}
        >
          {running ? "Running…" : "Run selected example"}
        </button>
      </div>
    </section>
  );
}
