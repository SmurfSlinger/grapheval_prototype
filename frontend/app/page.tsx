"use client";

import { useCallback, useEffect, useState } from "react";
import ControlsPanel from "@/components/ControlsPanel";
import KgcBacktrackingResultView from "@/components/KgcBacktrackingResultView";
import PipelineResultView from "@/components/PipelineResultView";
import {
  fetchExamples,
  fetchGraphClaims,
  fetchHealth,
  runAllExamples,
  runCustomExample,
  runExample,
  runKgcBacktracking,
  type Answer0Mode,
  type BacktrackingResult,
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
  const [model, setModel] = useState("gemma4:e2b");
  const [examples, setExamples] = useState<ExampleSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [answer0Mode, setAnswer0Mode] = useState<Answer0Mode>("preset");
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [kgcResult, setKgcResult] = useState<BacktrackingResult | null>(null);
  const [allResults, setAllResults] = useState<PipelineResult[]>([]);
  const [error, setError] = useState<string | null>(null);
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
    <main className={toolMode === "kgc" ? "main-wide" : undefined}>
      <header className="page-header">
        <div>
          <h1>GraphEval Prototype</h1>
          <p className="subtitle">
            {toolMode === "kgc"
              ? "KGc backtracking demo"
              : toolMode === "baseline"
                ? "Baseline comparison"
                : "Legacy tools"}
          </p>
        </div>
        <div className="status-row">
          <span
            className={`api-badge ${apiStatus === "ok" ? "ok" : apiStatus === "down" ? "down" : ""}`}
          >
            {apiStatus === "checking" && "API checking…"}
            {apiStatus === "ok" && "API connected"}
            {apiStatus === "down" && "API disconnected"}
          </span>
          <span
            className={`api-badge ${neo4jStatus === "enabled" ? "ok" : neo4jStatus === "disabled" ? "down" : ""}`}
          >
            {neo4jStatus === "checking" && "Neo4j checking…"}
            {neo4jStatus === "enabled" && "Neo4j storage enabled"}
            {neo4jStatus === "disabled" && "Neo4j storage disabled"}
          </span>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

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
        onToolModeChange={setToolMode}
        onProviderChange={setProvider}
        onModelChange={setModel}
        onSelectExample={handleSelectExample}
        onAnswer0ModeChange={setAnswer0Mode}
        onCustomQuestionChange={setCustomQuestion}
        onCustomContextChange={setCustomContext}
        onCustomAnswerChange={setCustomAnswer}
        onRunKgc={handleRunKgc}
        onRunBaseline={handleRunBaseline}
        onRunAllBaseline={handleRunAllBaseline}
        onRunCustomBaseline={handleRunCustomBaseline}
        onFillCustomFromSelected={fillCustomFromSelected}
      />

      {toolMode === "kgc" ? (
        <KgcBacktrackingResultView result={kgcResult} loading={running} />
      ) : null}

      {toolMode === "baseline" ? (
        <section className="results-stack">
          <h2 className="results-section-title">Baseline comparison</h2>
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
          <h2 className="results-section-title">Legacy tools</h2>
          <p className="controls-hint controls-mode-note">
            These are older prototype tools, kept for comparison/debugging.
          </p>
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
