"use client";

import { useCallback, useEffect, useState } from "react";
import ExampleSelector from "@/components/ExampleSelector";
import PipelineResultView from "@/components/PipelineResultView";
import {
  fetchExamples,
  fetchHealth,
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
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [apiStatus, setApiStatus] = useState<"ok" | "down" | "checking">(
    "checking",
  );

  const [customQuestion, setCustomQuestion] = useState("");
  const [customContext, setCustomContext] = useState("");
  const [customAnswer, setCustomAnswer] = useState("");

  useEffect(() => {
    fetchHealth()
      .then(() => setApiStatus("ok"))
      .catch(() => setApiStatus("down"));

    fetchExamples()
      .then((data) => {
        setExamples(data);
        if (data.length > 0) {
          setSelectedId(data[0].id);
        }
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const runOptions = useCallback(
    () => ({ provider, model }),
    [provider, model],
  );

  const handleRunSelected = async () => {
    if (!selectedId) return;
    setRunning(true);
    setError(null);
    try {
      const output = await runExample(selectedId, runOptions());
      setResult(output);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setRunning(false);
    }
  };

  const handleRunCustom = async () => {
    setRunning(true);
    setError(null);
    try {
      const output = await runCustomExample({
        question: customQuestion,
        context: customContext,
        initial_answer: customAnswer,
        ...runOptions(),
      });
      setResult(output);
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
      <h1>GraphEval Prototype</h1>
      <p className="subtitle">
        Triple-level hallucination detection and revision demo
      </p>

      <p>
        API:{" "}
        {apiStatus === "checking" && <span className="loading">checking…</span>}
        {apiStatus === "ok" && <span className="status-ok">connected</span>}
        {apiStatus === "down" && (
          <span className="status-down">
            unreachable — start backend with uvicorn api.server:app --reload
            --port 8000
          </span>
        )}
      </p>

      {error && <div className="error">{error}</div>}

      <section className="card">
        <h2>Provider / model</h2>
        <div className="row">
          <label>
            Provider
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value as Provider)}
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
              onChange={(e) => setModel(e.target.value)}
              disabled={provider === "mock"}
              placeholder="gemma4:e2b"
            />
          </label>
        </div>
        {provider === "ollama" && (
          <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginTop: "0.5rem" }}>
            Requires Ollama running locally (<code>ollama serve</code>) and the
            model pulled (<code>ollama pull {model}</code>).
          </p>
        )}
      </section>

      <ExampleSelector
        examples={examples}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onRun={handleRunSelected}
        running={running}
      />

      <section className="card">
        <h2>Custom input</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
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
              Fill from selected example
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
              {running ? "Running…" : "Run custom example"}
            </button>
          </div>
        </div>
      </section>

      <PipelineResultView result={result} loading={running} />
    </main>
  );
}
