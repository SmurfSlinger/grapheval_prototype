"use client";

import { useCallback, useEffect, useState } from "react";
import ControlsPanel from "@/components/ControlsPanel";
import DecomposedKgcBacktrackingResultView from "@/components/DecomposedKgcBacktrackingResultView";
import KgcBacktrackingResultView from "@/components/KgcBacktrackingResultView";
import PipelineResultView from "@/components/PipelineResultView";
import {
  fetchExamples,
  fetchGraphClaims,
  fetchHealth,
  runAllExamples,
  runCustomExample,
  runCustomDecomposedKgcBacktracking,
  runDecomposedKgcBacktracking,
  runExample,
  runKgcBacktracking,
  ApiError,
  type Answer0Mode,
  type BacktrackingResult,
  type DecomposedBacktrackingResult,
  type ExampleSummary,
  type PipelineResult,
  type Provider,
  type ToolMode,
} from "@/lib/api";

function defaultAnswer0Mode(example: ExampleSummary | undefined): Answer0Mode {
  return example?.initial_answer?.trim() ? "preset" : "generated";
}

const DEMO_EXAMPLE_ID = "saturn_v_apollo_11_001";

function defaultSelectedExampleId(examples: ExampleSummary[]): string | null {
  if (examples.length === 0) return null;
  const demo = examples.find((ex) => ex.id === DEMO_EXAMPLE_ID);
  return demo?.id ?? examples[0].id;
}

export default function HomePage() {
  const [toolMode, setToolMode] = useState<ToolMode>("kgc");
  const [provider, setProvider] = useState<Provider>("mock");
  const [model, setModel] = useState("gemma4:12b");
  const [examples, setExamples] = useState<ExampleSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [answer0Mode, setAnswer0Mode] = useState<Answer0Mode>("preset");
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [kgcResult, setKgcResult] = useState<BacktrackingResult | null>(null);
  const [decomposedResult, setDecomposedResult] =
    useState<DecomposedBacktrackingResult | null>(null);
  const [allResults, setAllResults] = useState<PipelineResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<unknown>(null);
  const [running, setRunning] = useState(false);
  const [apiStatus, setApiStatus] = useState<"ok" | "down" | "checking">(
    "checking",
  );
  const [neo4jStatus, setNeo4jStatus] = useState<
    "enabled" | "disabled" | "checking"
  >("checking");

  const [customQuestion, setCustomQuestion] = useState("");
  const [customContext, setCustomContext] = useState("");
  const [customAnswer, setCustomAnswer] = useState("");
  const [customRunEnabled, setCustomRunEnabled] = useState(false);
  const [customRunId, setCustomRunId] = useState("");
  const [clearNeo4jBeforeRun, setClearNeo4jBeforeRun] = useState(true);

  const refreshNeo4jStatus = useCallback(async () => {
    try {
      const response = await fetchGraphClaims({ limit: 1 });
      setNeo4jStatus(response.enabled ? "enabled" : "disabled");
    } catch {
      setNeo4jStatus("disabled");
    }
  }, []);

  useEffect(() => {
    fetchHealth()
      .then(() => setApiStatus("ok"))
      .catch(() => setApiStatus("down"));

    refreshNeo4jStatus();

    fetchExamples()
      .then((data) => {
        setExamples(data);
        if (data.length > 0) {
          const initialId = defaultSelectedExampleId(data);
          setSelectedId(initialId);
          const initialExample = data.find((ex) => ex.id === initialId);
          setAnswer0Mode(defaultAnswer0Mode(initialExample));
        }
      })
      .catch((err: Error) => setError(err.message));
  }, [refreshNeo4jStatus]);

  const clearError = () => {
    setError(null);
    setErrorDetails(null);
  };

  const handleApiFailure = (err: unknown, fallback: string) => {
    if (err instanceof ApiError) {
      setError(err.message);
      setErrorDetails(err.details ?? null);
      return;
    }
    setError(err instanceof Error ? err.message : fallback);
    setErrorDetails(null);
  };

  const runOptions = useCallback(
    () => ({ provider, model, answer_0_mode: answer0Mode }),
    [provider, model, answer0Mode],
  );

  const selectResult = (id: string) => {
    setSelectedId(id);
    const fromAll = allResults.find((r) => r.example_id === id);
    if (fromAll) {
      setResult(fromAll);
    }
  };

  const handleSelectExample = (id: string) => {
    setSelectedId(id);
    const example = examples.find((ex) => ex.id === id);
    setAnswer0Mode(defaultAnswer0Mode(example));
    const fromAll = allResults.find((r) => r.example_id === id);
    if (fromAll) {
      setResult(fromAll);
    } else if (result?.example_id !== id) {
      setResult(null);
    }
  };

  const handleRunBaseline = async () => {
    if (!selectedId) return;
    setRunning(true);
    setError(null);
    setAllResults([]);
    try {
      const output = await runExample(selectedId, { provider, model });
      setResult(output);
      await refreshNeo4jStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setRunning(false);
    }
  };

  const handleRunAllBaseline = async () => {
    setRunning(true);
    setError(null);
    try {
      const outputs = await runAllExamples({ provider, model });
      setAllResults(outputs);
      if (outputs.length > 0) {
        setResult(outputs[0]);
        setSelectedId(outputs[0].example_id);
      }
      await refreshNeo4jStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run all failed");
    } finally {
      setRunning(false);
    }
  };

  const handleRunKgc = async () => {
    if (!selectedId) return;
    setRunning(true);
    setError(null);
    try {
      const output = await runKgcBacktracking(selectedId, runOptions());
      setKgcResult(output);
      await refreshNeo4jStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "KGc backtracking failed");
    } finally {
      setRunning(false);
    }
  };

  const handleRunDecomposedKgc = async () => {
    if (!customRunEnabled && !selectedId) return;
    setRunning(true);
    clearError();
    setDecomposedResult(null);
    try {
      const output = customRunEnabled
        ? await runCustomDecomposedKgcBacktracking({
            run_id: customRunId.trim() || undefined,
            question: customQuestion,
            context: customContext,
            initial_answer: customAnswer.trim() || undefined,
            clear_neo4j_before_run: clearNeo4jBeforeRun,
            provider,
            model,
            max_iterations_per_sub_question: 3,
          })
        : await runDecomposedKgcBacktracking(selectedId!, {
            provider,
            model,
            max_iterations_per_sub_question: 3,
            answer_0_mode: answer0Mode,
          });
      setDecomposedResult(output);
      setSelectedId(output.example_id);
      await refreshNeo4jStatus();
    } catch (err) {
      handleApiFailure(err, "Decomposed KGc backtracking failed");
    } finally {
      setRunning(false);
    }
  };

  const handleRunCustomBaseline = async () => {
    setRunning(true);
    setError(null);
    setAllResults([]);
    try {
      const output = await runCustomExample({
        question: customQuestion,
        context: customContext,
        initial_answer: customAnswer,
        provider,
        model,
      });
      setResult(output);
      setSelectedId(output.example_id);
      await refreshNeo4jStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setRunning(false);
    }
  };

  const fillCustomFromSelected = () => {
    const ex = examples.find((e) => e.id === selectedId);
    if (!ex) return;
    setCustomQuestion(ex.question);
    setCustomContext(ex.context);
    setCustomAnswer(ex.initial_answer ?? "");
  };

  return (
    <main className={toolMode === "kgc" || toolMode === "decomposed_kgc" ? "main-wide" : undefined}>
      <header className="page-header">
        <div>
          <h1>GraphEval</h1>
          <p className="subtitle">
            {toolMode === "kgc"
              ? "Method: Backtracking"
              : toolMode === "decomposed_kgc"
                ? "Method: Decomposed Backtracking"
                : toolMode === "baseline"
                  ? "Method: Baseline"
                  : "Method: Legacy Tools"}
          </p>
        </div>
        <div className="status-row">
          <span
            className={`api-badge ${apiStatus === "ok" ? "ok" : apiStatus === "down" ? "down" : ""}`}
          >
            {apiStatus === "checking" && "API…"}
            {apiStatus === "ok" && "API connected"}
            {apiStatus === "down" && "API disconnected"}
          </span>
          <span
            className={`api-badge ${neo4jStatus === "enabled" ? "ok" : neo4jStatus === "disabled" ? "down" : ""}`}
          >
            {neo4jStatus === "checking" && "Neo4j…"}
            {neo4jStatus === "enabled" && "Neo4j connected"}
            {neo4jStatus === "disabled" && "Neo4j disabled"}
          </span>
        </div>
      </header>

      {error && (
        <div className="error">
          <div>{error}</div>
          {errorDetails != null && (
            <details className="error-details">
              <summary>Advanced error details</summary>
              <pre>{JSON.stringify(errorDetails, null, 2)}</pre>
            </details>
          )}
        </div>
      )}

      <ControlsPanel
        toolMode={toolMode}
        provider={provider}
        model={model}
        examples={examples}
        selectedId={selectedId}
        answer0Mode={answer0Mode}
        running={running}
        customQuestion={customQuestion}
        customContext={customContext}
        customAnswer={customAnswer}
        customRunEnabled={customRunEnabled}
        customRunId={customRunId}
        clearNeo4jBeforeRun={clearNeo4jBeforeRun}
        onToolModeChange={setToolMode}
        onProviderChange={setProvider}
        onModelChange={setModel}
        onSelectExample={handleSelectExample}
        onAnswer0ModeChange={setAnswer0Mode}
        onCustomQuestionChange={setCustomQuestion}
        onCustomContextChange={setCustomContext}
        onCustomAnswerChange={setCustomAnswer}
        onCustomRunEnabledChange={setCustomRunEnabled}
        onCustomRunIdChange={setCustomRunId}
        onClearNeo4jBeforeRunChange={setClearNeo4jBeforeRun}
        onRunKgc={handleRunKgc}
        onRunDecomposedKgc={handleRunDecomposedKgc}
        onRunBaseline={handleRunBaseline}
        onRunAllBaseline={handleRunAllBaseline}
        onRunCustomBaseline={handleRunCustomBaseline}
        onFillCustomFromSelected={fillCustomFromSelected}
      />

      {toolMode === "kgc" ? (
        <KgcBacktrackingResultView result={kgcResult} loading={running} />
      ) : null}

      {toolMode === "decomposed_kgc" ? (
        <DecomposedKgcBacktrackingResultView
          result={decomposedResult}
          loading={running}
        />
      ) : null}

      {toolMode === "baseline" ? (
        <section className="results-stack">
          <PipelineResultView
            result={result}
            loading={running}
            allResults={[]}
            selectedId={selectedId}
            onSelectResult={selectResult}
            onRefreshNeo4j={refreshNeo4jStatus}
          />
        </section>
      ) : null}

      {toolMode === "legacy" ? (
        <section className="results-stack">
          <PipelineResultView
            result={result}
            loading={running}
            allResults={allResults}
            selectedId={selectedId}
            onSelectResult={selectResult}
            onRefreshNeo4j={refreshNeo4jStatus}
          />
        </section>
      ) : null}
    </main>
  );
}
