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
  customRunEnabled: boolean;
  customRunId: string;
  clearNeo4jBeforeRun: boolean;
  onToolModeChange: (mode: ToolMode) => void;
  onProviderChange: (provider: Provider) => void;
  onModelChange: (model: string) => void;
  onSelectExample: (id: string) => void;
  onAnswer0ModeChange: (mode: Answer0Mode) => void;
  onCustomQuestionChange: (value: string) => void;
  onCustomContextChange: (value: string) => void;
  onCustomAnswerChange: (value: string) => void;
  onCustomRunEnabledChange: (value: boolean) => void;
  onCustomRunIdChange: (value: string) => void;
  onClearNeo4jBeforeRunChange: (value: boolean) => void;
  onRunKgc: () => void;
  onRunDecomposedKgc: () => void;
  onRunBaseline: () => void;
  onRunAllBaseline: () => void;
  onRunCustomBaseline: () => void;
  onFillCustomFromSelected: () => void;
}

/** Display labels only — internal ToolMode values are unchanged. */
const TOOL_MODE_LABELS: Record<ToolMode, string> = {
  baseline: "Baseline",
  kgc: "Backtracking",
  decomposed_kgc: "Decomposed Backtracking",
  legacy: "Legacy Tools",
};

const TOOL_MODE_BLURBS: Record<ToolMode, string> = {
  baseline: "Generate and verify answers against trusted context.",
  kgc: "Correct a flawed answer using the knowledge graph.",
  decomposed_kgc: "Checks and corrects compound questions one part at a time.",
  legacy: "Older comparison and custom-input tools.",
};

const TOOL_MODE_ORDER: ToolMode[] = [
  "baseline",
  "kgc",
  "decomposed_kgc",
  "legacy",
];

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
    customRunEnabled,
    customRunId,
    clearNeo4jBeforeRun,
    onToolModeChange,
    onProviderChange,
    onModelChange,
    onSelectExample,
    onAnswer0ModeChange,
    onCustomQuestionChange,
    onCustomContextChange,
    onCustomAnswerChange,
    onCustomRunEnabledChange,
    onCustomRunIdChange,
    onClearNeo4jBeforeRunChange,
    onRunKgc,
    onRunDecomposedKgc,
    onRunBaseline,
    onRunAllBaseline,
    onRunCustomBaseline,
    onFillCustomFromSelected,
  } = props;

  const selectedExample = examples.find((ex) => ex.id === selectedId);
  const presetAvailable = Boolean(selectedExample?.initial_answer?.trim());

  return (
    <section className="card controls-card controls-card-primary">
      <div className="controls-method">
        <p className="controls-method-label">Method</p>
        <div
          className="controls-method-tabs"
          role="tablist"
          aria-label="Method"
        >
          {TOOL_MODE_ORDER.map((mode) => (
            <button
              key={mode}
              type="button"
              role="tab"
              aria-selected={toolMode === mode}
              className={
                toolMode === mode
                  ? "controls-method-tab controls-method-tab-active"
                  : "controls-method-tab"
              }
              onClick={() => onToolModeChange(mode)}
            >
              {TOOL_MODE_LABELS[mode]}
            </button>
          ))}
        </div>
        <p className="controls-method-blurb">{TOOL_MODE_BLURBS[toolMode]}</p>
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
                  Preset flawed answer
                </option>
                <option value="generated">Generate from context</option>
              </select>
            </label>
            {answer0Mode === "preset" && !presetAvailable ? (
              <p className="controls-warning">
                No preset answer for this example; the run will generate one from
                context.
              </p>
            ) : null}
          </div>

          <div className="row controls-actions">
            <button
              type="button"
              onClick={onRunKgc}
              disabled={!selectedId || running}
            >
              {running ? "Running…" : "Run"}
            </button>
          </div>
        </>
      ) : null}

      {toolMode === "decomposed_kgc" ? (
        <>
          <label>
            Input source
            <select
              value={customRunEnabled ? "custom" : "built_in"}
              onChange={(e) =>
                onCustomRunEnabledChange(e.target.value === "custom")
              }
            >
              <option value="built_in">Built-in example</option>
              <option value="custom">Custom local run</option>
            </select>
          </label>

          {customRunEnabled ? (
            <div className="custom-run-fields">
              <label>
                Run label / ID (optional)
                <input
                  type="text"
                  value={customRunId}
                  onChange={(e) => onCustomRunIdChange(e.target.value)}
                  placeholder="professor-test-1"
                />
              </label>
              <label>
                Trusted context
                <textarea
                  value={customContext}
                  onChange={(e) => onCustomContextChange(e.target.value)}
                />
              </label>
              <label>
                Compound question
                <textarea
                  value={customQuestion}
                  onChange={(e) => onCustomQuestionChange(e.target.value)}
                />
              </label>
              <label>
                Flawed initial answer (optional)
                <textarea
                  value={customAnswer}
                  onChange={(e) => onCustomAnswerChange(e.target.value)}
                />
              </label>
              <label className="controls-checkbox">
                <input
                  type="checkbox"
                  checked={clearNeo4jBeforeRun}
                  onChange={(e) =>
                    onClearNeo4jBeforeRunChange(e.target.checked)
                  }
                />
                Clear Neo4j before run
              </label>
              <p className="controls-warning">
                Deletes the local Neo4j graph before writing this run.
              </p>
              <p className="controls-hint">
                With an initial answer, preset external projection is used.
                Otherwise GraphEval generates and projects Answer(0).
              </p>
            </div>
          ) : null}

          <div className="row controls-actions">
            <button
              type="button"
              onClick={onRunDecomposedKgc}
              disabled={
                running ||
                (customRunEnabled
                  ? !customQuestion.trim() || !customContext.trim()
                  : !selectedId)
              }
            >
              {running ? "Running…" : "Run"}
            </button>
          </div>
        </>
      ) : null}

      {toolMode === "baseline" ? (
        <div className="row controls-actions">
          <button
            type="button"
            onClick={onRunBaseline}
            disabled={!selectedId || running}
          >
            {running ? "Running…" : "Run"}
          </button>
        </div>
      ) : null}

      {toolMode === "legacy" ? (
        <>
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
              {running ? "Running…" : "Run all"}
            </button>
          </div>
          <h4 className="legacy-tools-subtitle">Custom input</h4>
          <label>
            Question
            <textarea
              value={customQuestion}
              onChange={(e) => onCustomQuestionChange(e.target.value)}
            />
          </label>
          <label>
            Context
            <textarea
              value={customContext}
              onChange={(e) => onCustomContextChange(e.target.value)}
            />
          </label>
          <label>
            Initial answer
            <textarea
              value={customAnswer}
              onChange={(e) => onCustomAnswerChange(e.target.value)}
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
              {running ? "Running…" : "Run custom"}
            </button>
          </div>
        </>
      ) : null}

      {provider === "ollama" ? (
        <p className="controls-hint">
          Requires <code>ollama serve</code> and <code>ollama pull {model}</code>
        </p>
      ) : null}
    </section>
  );
}
