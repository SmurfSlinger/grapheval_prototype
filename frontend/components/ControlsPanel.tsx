import type {
  Answer0Mode,
  ExampleSummary,
  Provider,
  ToolMode,
} from "@/lib/api";

interface ControlsPanelProps {
  toolMode: ToolMode;
  provider: Provider;
  model: string;
  examples: ExampleSummary[];
  selectedId: string | null;
  answer0Mode: Answer0Mode;
  running: boolean;
  customQuestion: string;
  customContext: string;
  customAnswer: string;
  onToolModeChange: (mode: ToolMode) => void;
  onProviderChange: (provider: Provider) => void;
  onModelChange: (model: string) => void;
  onSelectExample: (id: string) => void;
  onAnswer0ModeChange: (mode: Answer0Mode) => void;
  onCustomQuestionChange: (value: string) => void;
  onCustomContextChange: (value: string) => void;
  onCustomAnswerChange: (value: string) => void;
  onRunKgc: () => void;
  onRunBaseline: () => void;
  onRunAllBaseline: () => void;
  onRunCustomBaseline: () => void;
  onFillCustomFromSelected: () => void;
}

const TOOL_MODE_LABELS: Record<ToolMode, string> = {
  kgc: "KGc backtracking demo",
  baseline: "Plain LLM baseline",
  legacy: "Legacy GraphEval tools",
};

function answer0ModeHint(mode: Answer0Mode): string {
  if (mode === "preset") {
    return "Demo mode: KGc checks a flawed external LLM answer.";
  }
  return "Research-style: generate Answer(0) from raw context, then audit with KGc.";
}

function answer0TestNote(mode: Answer0Mode): string {
  if (mode === "preset") {
    return "Flawed answer → KGc feedback → revised answer.";
  }
  return "Optional path when no preset baseline is available.";
}

function SharedRunFields({
  provider,
  model,
  examples,
  selectedId,
  running,
  onProviderChange,
  onModelChange,
  onSelectExample,
}: Pick<
  ControlsPanelProps,
  | "provider"
  | "model"
  | "examples"
  | "selectedId"
  | "running"
  | "onProviderChange"
  | "onModelChange"
  | "onSelectExample"
>) {
  return (
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
  );
}

export default function ControlsPanel(props: ControlsPanelProps) {
  const {
    toolMode,
    provider,
    model,
    examples,
    selectedId,
    answer0Mode,
    running,
    customQuestion,
    customContext,
    customAnswer,
    onToolModeChange,
    onProviderChange,
    onModelChange,
    onSelectExample,
    onAnswer0ModeChange,
    onCustomQuestionChange,
    onCustomContextChange,
    onCustomAnswerChange,
    onRunKgc,
    onRunBaseline,
    onRunAllBaseline,
    onRunCustomBaseline,
    onFillCustomFromSelected,
  } = props;

  const selectedExample = examples.find((ex) => ex.id === selectedId);
  const presetAvailable = Boolean(selectedExample?.initial_answer?.trim());

  return (
    <section className="card controls-card controls-card-primary">
      <div className="controls-tool-mode">
        <label className="controls-tool-mode-label">
          Tool mode
          <select
            value={toolMode}
            onChange={(e) => onToolModeChange(e.target.value as ToolMode)}
          >
            <option value="kgc">KGc backtracking demo</option>
            <option value="baseline">Plain LLM baseline</option>
            <option value="legacy">Legacy GraphEval tools</option>
          </select>
        </label>
        <p className="controls-mode-active">
          Active: <strong>{TOOL_MODE_LABELS[toolMode]}</strong>
        </p>
      </div>

      <SharedRunFields
        provider={provider}
        model={model}
        examples={examples}
        selectedId={selectedId}
        running={running}
        onProviderChange={onProviderChange}
        onModelChange={onModelChange}
        onSelectExample={onSelectExample}
      />

      {toolMode === "kgc" ? (
        <>
          <div className="controls-answer0-mode">
            <label className="controls-answer0-label">
              Answer(0) source
              <select
                value={answer0Mode}
                onChange={(e) =>
                  onAnswer0ModeChange(e.target.value as Answer0Mode)
                }
              >
                <option value="preset" disabled={!presetAvailable}>
                  Preset flawed baseline (demo)
                </option>
                <option value="generated">
                  Research: generate from raw context
                </option>
              </select>
            </label>
            <p className="controls-hint">{answer0ModeHint(answer0Mode)}</p>
            <p className="controls-test-note">
              <strong>What this shows:</strong> {answer0TestNote(answer0Mode)}
            </p>
            {answer0Mode === "preset" && !presetAvailable ? (
              <p className="controls-warning">
                No preset initial_answer for this example; run will generate
                Answer(0) from raw context.
              </p>
            ) : null}
          </div>

          <div className="row controls-actions">
            <button
              type="button"
              onClick={onRunKgc}
              disabled={!selectedId || running}
            >
              {running ? "Running…" : "Run KGc backtracking"}
            </button>
          </div>
        </>
      ) : null}

      {toolMode === "baseline" ? (
        <>
          <p className="controls-hint controls-mode-note">
            Secondary path: verify triples against raw context without KGc
            backtracking.
          </p>
          <div className="row controls-actions">
            <button
              type="button"
              onClick={onRunBaseline}
              disabled={!selectedId || running}
            >
              {running ? "Running…" : "Run baseline"}
            </button>
          </div>
        </>
      ) : null}

      {toolMode === "legacy" ? (
        <>
          <p className="controls-hint controls-mode-note">
            These are older prototype tools, kept for comparison/debugging.
          </p>
          <div className="row controls-actions">
            <button
              type="button"
              className="secondary"
              onClick={onRunBaseline}
              disabled={!selectedId || running}
            >
              {running ? "Running…" : "Run baseline"}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={onRunAllBaseline}
              disabled={running || examples.length === 0}
            >
              {running ? "Running…" : "Run all baseline"}
            </button>
          </div>
          <h4 className="legacy-tools-subtitle">Custom baseline input</h4>
          <label>
            Question
            <textarea
              value={customQuestion}
              onChange={(e) => onCustomQuestionChange(e.target.value)}
              placeholder="What should the model answer?"
            />
          </label>
          <label>
            Context (trusted source)
            <textarea
              value={customContext}
              onChange={(e) => onCustomContextChange(e.target.value)}
              placeholder="Ground-truth context for verification"
            />
          </label>
          <label>
            Initial answer (may contain errors)
            <textarea
              value={customAnswer}
              onChange={(e) => onCustomAnswerChange(e.target.value)}
              placeholder="LLM answer to verify and revise"
            />
          </label>
          <div className="row">
            <button
              type="button"
              className="secondary"
              onClick={onFillCustomFromSelected}
              disabled={!selectedId}
            >
              Fill from selected
            </button>
            <button
              type="button"
              className="secondary"
              onClick={onRunCustomBaseline}
              disabled={
                running ||
                !customQuestion.trim() ||
                !customContext.trim() ||
                !customAnswer.trim()
              }
            >
              {running ? "Running…" : "Run custom baseline"}
            </button>
          </div>
        </>
      ) : null}

      {provider === "ollama" && (
        <p className="controls-hint">
          Requires <code>ollama serve</code> and <code>ollama pull {model}</code>
        </p>
      )}
    </section>
  );
}
