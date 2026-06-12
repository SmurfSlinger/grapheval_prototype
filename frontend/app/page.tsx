"use client";

import { useCallback, useEffect, useState } from "react";
import ControlsPanel from "@/components/ControlsPanel";
import PipelineResultView from "@/components/PipelineResultView";
import {
  fetchExamples,
  fetchGraphClaims,
  fetchHealth,
  runAllExamples,
  runCustomExample,
  runExample,
  type ExampleSummary,
  type PipelineResult,
  type Provider,
} from "@/lib/api";

export default function HomePage() {
  const [provider, setProvider] = useState<Provider>("mock");
  const [model, setModel] = useState("gemma4:e2b");
  const [examples, setExamples] = useState<ExampleSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
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
          setSelectedId(data[0].id);
        }
      })
      .catch((err: Error) => setError(err.message));
  }, [refreshNeo4jStatus]);

  const runOptions = useCallback(
    () => ({ provider, model }),
    [provider, model],
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
    const fromAll = allResults.find((r) => r.example_id === id);
    if (fromAll) {
      setResult(fromAll);
    } else if (result?.example_id !== id) {
      setResult(null);
    }
  };

  const handleRunSelected = async () => {
    if (!selectedId) return;
    setRunning(true);
    setError(null);
    setAllResults([]);
    try {
      const output = await runExample(selectedId, runOptions());
      setResult(output);
      await refreshNeo4jStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setRunning(false);
    }
  };

  const handleRunAll = async () => {
    setRunning(true);
    setError(null);
    try {
      const outputs = await runAllExamples(runOptions());
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

  const handleRunCustom = async () => {
    setRunning(true);
    setError(null);
    setAllResults([]);
    try {
      const output = await runCustomExample({
        question: customQuestion,
        context: customContext,
        initial_answer: customAnswer,
        ...runOptions(),
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
    <main>
      <header className="page-header">
        <div>
          <h1>GraphEval Prototype</h1>
          <p className="subtitle">
            Triple-level feedback for hallucination correction
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
        provider={provider}
        model={model}
        examples={examples}
        selectedId={selectedId}
        running={running}
        onProviderChange={setProvider}
        onModelChange={setModel}
        onSelectExample={handleSelectExample}
        onRun={handleRunSelected}
        onRunAll={handleRunAll}
      />

      <details className="card details-card">
        <summary>Advanced: custom input</summary>
        <div className="details-body">
          <label>
            Question
            <textarea
              value={customQuestion}
              onChange={(e) => setCustomQuestion(e.target.value)}
              placeholder="What should the model answer?"
            />
          </label>
          <label>
            Context (trusted source)
            <textarea
              value={customContext}
              onChange={(e) => setCustomContext(e.target.value)}
              placeholder="Ground-truth context for verification"
            />
          </label>
          <label>
            Initial answer (may contain errors)
            <textarea
              value={customAnswer}
              onChange={(e) => setCustomAnswer(e.target.value)}
              placeholder="LLM answer to verify and revise"
            />
          </label>
          <div className="row">
            <button
              type="button"
              className="secondary"
              onClick={fillCustomFromSelected}
              disabled={!selectedId}
            >
              Fill from selected
            </button>
            <button
              type="button"
              onClick={handleRunCustom}
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
        </div>
      </details>

      <PipelineResultView
        result={result}
        loading={running}
        allResults={allResults}
        selectedId={selectedId}
        onSelectResult={selectResult}
        onRefreshNeo4j={refreshNeo4jStatus}
      />
    </main>
  );
}
