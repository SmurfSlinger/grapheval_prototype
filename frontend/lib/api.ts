const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Provider = "mock" | "ollama";

export type VerificationLabel = "SUPPORTED" | "CONTRADICTED" | "NOT_ENOUGH_INFO";

export interface ExampleSummary {
  id: string;
  question: string;
  context: string;
  initial_answer: string | null;
}

export interface Triple {
  subject: string;
  relation: string;
  object: string;
  source_sentence?: string | null;
}

export interface VerificationResult {
  triple: Triple;
  label: VerificationLabel;
  evidence: string;
  reason: string;
}

export interface FeedbackItem {
  triple: Triple;
  status: VerificationLabel;
  instruction: string;
  evidence: string;
}

export interface PipelineResult {
  example_id: string;
  question: string;
  context: string;
  initial_answer: string;
  extracted_triples: Triple[];
  verification_results: VerificationResult[];
  feedback: FeedbackItem[];
  revised_answer: string | null;
}

export interface RunOptions {
  provider: Provider;
  model: string;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // keep statusText
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export async function fetchHealth(): Promise<{ status: string }> {
  return apiFetch("/health");
}

export async function fetchExamples(): Promise<ExampleSummary[]> {
  return apiFetch("/examples");
}

export async function runExample(
  exampleId: string,
  options: RunOptions,
): Promise<PipelineResult> {
  return apiFetch("/run", {
    method: "POST",
    body: JSON.stringify({
      example_id: exampleId,
      provider: options.provider,
      model: options.model,
    }),
  });
}

export async function runCustomExample(
  payload: {
    question: string;
    context: string;
    initial_answer: string;
  } & RunOptions,
): Promise<PipelineResult> {
  return apiFetch("/run-custom", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
