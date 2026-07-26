import type {
  Answer0Mode,
  BenchmarkQuestionSummary,
  BenchmarkSummary,
  DecomposedInputSource,
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
  inputSource: DecomposedInputSource;
  customRunId: string;
  clearNeo4jBeforeRun: boolean;
  benchmarks: BenchmarkSummary[];
  benchmarksLoading: boolean;
  benchmarksError: string | null;
  selectedBenchmarkId: string | null;
  hopFilter: number | "all";
  benchmarkQuestions: BenchmarkQuestionSummary[];
  selectedBenchmarkQuestionId: string | null;
  onToolModeChange: (mode: ToolMode) => void;
  onProviderChange: (provider: Provider) => void;
  onModelChange: (model: string) => void;
  onSelectExample: (id: string) => void;
  onAnswer0ModeChange: (mode: Answer0Mode) => void;
  onCustomQuestionChange: (value: string) => void;
  onCustomContextChange: (value: string) => void;
  onCustomAnswerChange: (value: string) => void;
  onInputSourceChange: (value: DecomposedInputSource) => void;
  onCustomRunIdChange: (value: string) => void;
  onClearNeo4jBeforeRunChange: (value: boolean) => void;
  onSelectedBenchmarkIdChange: (value: string) => void;
  onHopFilterChange: (value: number | "all") => void;
  onSelectedBenchmarkQuestionIdChange: (value: string) => void;
  onBenchmarkPrevious: () => void;
  onBenchmarkNext: () => void;
  onRunKgc: () => void;
  onRunDecomposedKgc: () => void;
  onRunBaseline: () => void;
  onRunAllBaseline: () => void;
  onRunCustomBaseline: () => void;
  onFillCustomFromSelected: () => void;
}

const SOURCE_OPTIONS: { id: DecomposedInputSource; label: string }[] = [
  { id: "benchmark", label: "Benchmark Question" },
  { id: "custom", label: "Custom Input" },
  { id: "built_in", label: "Built-in Example" },
];

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
    inputSource,
    customRunId,
    clearNeo4jBeforeRun,
    benchmarks,
    benchmarksLoading,
    benchmarksError,
    selectedBenchmarkId,
    hopFilter,
    benchmarkQuestions,
    selectedBenchmarkQuestionId,
    onToolModeChange,
    onProviderChange,
    onModelChange,
    onSelectExample,
    onAnswer0ModeChange,
    onCustomQuestionChange,
    onCustomContextChange,
    onCustomAnswerChange,
    onInputSourceChange,
    onCustomRunIdChange,
    onClearNeo4jBeforeRunChange,
    onSelectedBenchmarkIdChange,
    onHopFilterChange,
    onSelectedBenchmarkQuestionIdChange,
    onBenchmarkPrevious,
    onBenchmarkNext,
    onRunKgc,
    onRunDecomposedKgc,
    onRunBaseline,
    onRunAllBaseline,
    onRunCustomBaseline,
    onFillCustomFromSelected,
  } = props;

  const selectedExample = examples.find((ex) => ex.id === selectedId);
  const presetAvailable = Boolean(selectedExample?.initial_answer?.trim());
  const selectedBenchmarkQuestion = benchmarkQuestions.find(
    (row) => row.id === selectedBenchmarkQuestionId,
  );
  const selectedBenchmarkIndex = benchmarkQuestions.findIndex(
    (row) => row.id === selectedBenchmarkQuestionId,
  );

  const primaryRunDisabled =
    running ||
    (inputSource === "custom"
      ? !customQuestion.trim() || !customContext.trim()
      : inputSource === "benchmark"
        ? !selectedBenchmarkId || !selectedBenchmarkQuestionId
        : !selectedId);

  return (
    <section className="simple-controls">
      <div className="simple-controls-top">
        <div className="simple-brand-block">
          <h1 className="simple-brand">GraphEval</h1>
          <p className="simple-workflow-label">Decomposed Backtracking</p>
        </div>
      </div>

      <div className="simple-source-row" role="tablist" aria-label="Source">
        {SOURCE_OPTIONS.map((option) => (
          <button
            key={option.id}
            type="button"
            role="tab"
            aria-selected={inputSource === option.id}
            className={
              inputSource === option.id
                ? "simple-source-tab simple-source-tab-active"
                : "simple-source-tab"
            }
            onClick={() => {
              onInputSourceChange(option.id);
              if (toolMode !== "decomposed_kgc") {
                onToolModeChange("decomposed_kgc");
              }
            }}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div className="simple-run-row">
        <label>
          Provider
          <select
            value={provider}
            onChange={(e) => onProviderChange(e.target.value as Provider)}
          >
            <option value="ollama">Ollama</option>
            <option value="mock">mock</option>
          </select>
        </label>
        <label>
          Model
          <input
            type="text"
            value={model}
            onChange={(e) => onModelChange(e.target.value)}
            disabled={provider === "mock"}
            placeholder="gemma4:e4b"
          />
        </label>
        <button
          type="button"
          className="simple-run-button"
          onClick={onRunDecomposedKgc}
          disabled={primaryRunDisabled}
        >
          {running ? "Running…" : "Run"}
        </button>
      </div>

      {inputSource === "benchmark" ? (
        <div className="simple-source-body">
          {benchmarksLoading ? (
            <p className="controls-hint">Loading benchmarks…</p>
          ) : null}
          {benchmarksError ? (
            <p className="controls-warning">{benchmarksError}</p>
          ) : null}
          <div className="simple-benchmark-grid">
            <label>
              Benchmark
              <select
                value={selectedBenchmarkId ?? ""}
                onChange={(e) => onSelectedBenchmarkIdChange(e.target.value)}
                disabled={benchmarksLoading || benchmarks.length === 0}
              >
                {benchmarks.length === 0 ? (
                  <option value="">No benchmarks available</option>
                ) : null}
                {benchmarks.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Question depth
              <select
                value={hopFilter === "all" ? "all" : String(hopFilter)}
                onChange={(e) => {
                  const value = e.target.value;
                  onHopFilterChange(
                    value === "all" ? "all" : Number.parseInt(value, 10),
                  );
                }}
              >
                <option value="all">All</option>
                {Array.from({ length: 10 }, (_, index) => index + 1).map(
                  (hop) => (
                    <option key={hop} value={hop}>
                      {hop}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label className="simple-question-select">
              Question
              <select
                value={selectedBenchmarkQuestionId ?? ""}
                onChange={(e) =>
                  onSelectedBenchmarkQuestionIdChange(e.target.value)
                }
                disabled={benchmarkQuestions.length === 0}
              >
                {benchmarkQuestions.length === 0 ? (
                  <option value="">No questions for this filter</option>
                ) : null}
                {benchmarkQuestions.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.id} · hop {row.hop_count}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="controls-hint">
            Filters questions by designed graph-path length. It does not change
            the model or force a number of reasoning steps.
          </p>
          {selectedBenchmarkQuestion ? (
            <p className="simple-question-preview">
              {selectedBenchmarkQuestion.question}
            </p>
          ) : null}
          <div className="row controls-actions benchmark-nav">
            <button
              type="button"
              onClick={onBenchmarkPrevious}
              disabled={
                running ||
                selectedBenchmarkIndex < 0 ||
                selectedBenchmarkIndex === 0
              }
            >
              Previous
            </button>
            <button
              type="button"
              onClick={onBenchmarkNext}
              disabled={
                running ||
                selectedBenchmarkIndex < 0 ||
                selectedBenchmarkIndex >= benchmarkQuestions.length - 1
              }
            >
              Next
            </button>
            <button
              type="button"
              onClick={onRunDecomposedKgc}
              disabled={primaryRunDisabled}
            >
              {running ? "Running…" : "Run"}
            </button>
          </div>
        </div>
      ) : null}

      {inputSource === "custom" ? (
        <div className="simple-source-body custom-run-fields">
          <label>
            Trusted context
            <textarea
              value={customContext}
              onChange={(e) => onCustomContextChange(e.target.value)}
            />
          </label>
          <label>
            Question
            <textarea
              value={customQuestion}
              onChange={(e) => onCustomQuestionChange(e.target.value)}
            />
          </label>
          <label>
            Optional initial answer
            <textarea
              value={customAnswer}
              onChange={(e) => onCustomAnswerChange(e.target.value)}
            />
          </label>
        </div>
      ) : null}

      {inputSource === "built_in" ? (
        <div className="simple-source-body">
          <label>
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
          {selectedExample ? (
            <p className="simple-question-preview">{selectedExample.question}</p>
          ) : null}
        </div>
      ) : null}

      <details className="simple-advanced">
        <summary>Advanced settings</summary>
        <div className="simple-advanced-body">
          <label className="controls-checkbox">
            <input
              type="checkbox"
              checked={clearNeo4jBeforeRun}
              onChange={(e) => onClearNeo4jBeforeRunChange(e.target.checked)}
            />
            Clear Neo4j before run
          </label>
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
            Answer(0) source (built-in / backtracking)
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
          {provider === "ollama" ? (
            <p className="controls-hint">
              Requires <code>ollama serve</code> and{" "}
              <code>ollama pull {model}</code>
            </p>
          ) : null}
        </div>
      </details>

      <details className="simple-advanced">
        <summary>Legacy / developer modes</summary>
        <div className="simple-advanced-body">
          <p className="controls-hint">
            Primary research workflow stays on Decomposed Backtracking. These
            modes remain available for debugging only.
          </p>
          <label>
            Mode
            <select
              value={toolMode}
              onChange={(e) => onToolModeChange(e.target.value as ToolMode)}
            >
              <option value="decomposed_kgc">Decomposed Backtracking</option>
              <option value="kgc">Backtracking</option>
              <option value="baseline">Baseline</option>
              <option value="legacy">Legacy Tools</option>
            </select>
          </label>

          {toolMode === "kgc" ? (
            <div className="row controls-actions">
              <button
                type="button"
                onClick={onRunKgc}
                disabled={!selectedId || running}
              >
                {running ? "Running…" : "Run Backtracking"}
              </button>
            </div>
          ) : null}

          {toolMode === "baseline" ? (
            <div className="row controls-actions">
              <button
                type="button"
                onClick={onRunBaseline}
                disabled={!selectedId || running}
              >
                {running ? "Running…" : "Run baseline"}
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
              <button
                type="button"
                className="secondary"
                onClick={onFillCustomFromSelected}
                disabled={!selectedId}
              >
                Fill custom from selected
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
            </>
          ) : null}
        </div>
      </details>
    </section>
  );
}
