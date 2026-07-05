const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Provider = "mock" | "ollama";

export type ToolMode = "kgc" | "baseline" | "legacy";

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

export interface PipelineMetrics {
  initial_total_triples: number;
  initial_supported_count: number;
  initial_contradicted_count: number;
  initial_not_enough_info_count: number;
  graph_revision_needed: boolean;
  graph_revised_total_triples?: number | null;
  graph_revised_supported_count?: number | null;
  graph_revised_contradicted_count?: number | null;
  graph_revised_not_enough_info_count?: number | null;
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
  self_corrected_answer: string | null;
  graph_feedback_revised_answer: string | null;
  graph_revised_triples: Triple[];
  graph_revised_verification_results: VerificationResult[];
  metrics: PipelineMetrics;
}

export type KgcClaimLabel = "SUPPORTED" | "CONTRADICTED" | "NO_EVIDENCE";

export interface KgcFact {
  subject: string;
  relation: string;
  object: string;
  evidence?: string | null;
}

export interface BacktrackingTrace {
  answer_0_source: string;
  answer_0_mode: "preset" | "generated";
  kgc_source: string;
  answer_n_source: string;
  claim_extraction_source: string;
  revision_source: string;
  answer_0_warning?: string | null;
  kgc_reference_answer_source?: string | null;
}

export type Answer0Mode = "preset" | "generated";

export interface RevisionEffect {
  preserved_supported_count: number;
  corrected_contradicted_count: number;
  removed_or_deferred_no_evidence_count: number;
}

export interface KgcEvaluatedClaim {
  triple: Triple;
  aligned_claim?: Triple;
  original_claim?: Triple | null;
  schema_aligned?: boolean;
  source_sentence?: string | null;
  label: KgcClaimLabel;
  reason: string;
  evidence: string;
  matched_kgc_fact?: KgcFact | null;
  conflicting_object?: string | null;
  conflicting_fact?: KgcFact | null;
  backtracking_action?: string | null;
}

export interface BacktrackingFeedbackItem {
  triple: Triple;
  label: KgcClaimLabel;
  instruction: string;
  reason: string;
  evidence: string;
  conflicting_object?: string | null;
  matched_kgc_fact?: KgcFact | null;
  conflicting_fact?: KgcFact | null;
  backtracking_action?: string | null;
}

export interface BacktrackingResult {
  example_id: string;
  question: string;
  context: string;
  answer_0: string;
  kgc_facts: KgcFact[];
  serialized_kgc: string;
  kgc_reference_answer?: string;
  graph_grounded_answer: string;
  answer_n: string;
  evaluated_answer?: string;
  evaluated_answer_iteration?: number;
  iteration: number;
  extracted_claims: Triple[];
  aligned_claims: Triple[];
  evaluated_claims: KgcEvaluatedClaim[];
  backtracking_feedback: BacktrackingFeedbackItem[];
  answer_1?: string;
  answer_n_plus_1: string;
  final_answer?: string;
  supported_count: number;
  contradicted_count: number;
  no_evidence_count: number;
  max_iterations: number;
  trace?: BacktrackingTrace | null;
  revision_effect?: RevisionEffect | null;
  answer_0_mode?: Answer0Mode;
  answer_0_warning?: string | null;
  kgc_extraction_notice?: string | null;
  stop_reason?: string | null;
  iteration_history?: Array<{
    iteration: number;
    evaluated_answer: string;
    answer_stage: string;
    supported_count: number;
    contradicted_count: number;
    no_evidence_count: number;
  }>;
}

export interface KgcRunOptions extends RunOptions {
  answer_0_mode?: Answer0Mode;
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

export async function runAllExamples(
  options: RunOptions,
): Promise<PipelineResult[]> {
  return apiFetch("/run-all", {
    method: "POST",
    body: JSON.stringify({
      provider: options.provider,
      model: options.model,
    }),
  });
}

export interface StoredClaim {
  subject: string;
  relation: string;
  object: string;
  label: VerificationLabel;
  reason: string;
  evidence: string;
  example_id: string;
  answer_stage: string;
}

export interface GraphClaimsResponse {
  enabled: boolean;
  claims: StoredClaim[];
  error: string | null;
}

export async function fetchGraphClaims(options?: {
  limit?: number;
  exampleId?: string;
}): Promise<GraphClaimsResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(options?.limit ?? 50));
  if (options?.exampleId) {
    params.set("example_id", options.exampleId);
  }
  return apiFetch(`/graph/claims?${params.toString()}`);
}

export async function runKgcBacktracking(
  exampleId: string,
  options: KgcRunOptions,
): Promise<BacktrackingResult> {
  return apiFetch("/run-kgc-backtracking", {
    method: "POST",
    body: JSON.stringify({
      example_id: exampleId,
      provider: options.provider,
      model: options.model,
      max_iterations: 1,
      answer_0_mode: options.answer_0_mode ?? "preset",
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
