const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  details?: unknown;

  constructor(message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.details = details;
  }
}

export function formatApiErrorDetail(
  detail: unknown,
): { message: string; details?: unknown } {
  if (typeof detail === "string") {
    return { message: detail };
  }

  if (Array.isArray(detail)) {
    const message = detail
      .map((item) => {
        if (item && typeof item === "object") {
          const record = item as { loc?: unknown; msg?: unknown };
          const loc = Array.isArray(record.loc) ? record.loc.join(".") : "";
          const msg =
            typeof record.msg === "string" ? record.msg : JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join("; ");
    return { message: message || "Request validation failed", details: detail };
  }

  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    const stage =
      typeof record.stage === "string" ? record.stage : undefined;
    const baseMessage =
      (typeof record.message === "string" && record.message) ||
      (typeof record.error === "string" && record.error) ||
      (typeof record.msg === "string" && record.msg) ||
      undefined;
    if (baseMessage) {
      return {
        message: stage ? `${stage}: ${baseMessage}` : baseMessage,
        details: detail,
      };
    }
    return {
      message: JSON.stringify(detail, null, 2),
      details: detail,
    };
  }

  return { message: String(detail) };
}

export type Provider = "mock" | "ollama";

export type ToolMode = "kgc" | "decomposed_kgc" | "baseline" | "legacy";

export type DecomposedInputSource = "built_in" | "custom" | "benchmark";

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

export interface SubQuestion {
  id: number;
  question: string;
}

export interface DecomposedExperimentMetrics {
  sub_question_count: number;
  total_iterations: number;
  total_claims_extracted: number;
  total_claims_evaluated: number;
  total_supported: number;
  total_contradicted: number;
  total_no_evidence: number;
  structured_output_retries: number;
  resolved_sub_questions: number;
  stalled_sub_questions: number;
  unresolved_sub_questions: number;
  max_iterations_sub_questions: number;
  total_revisions?: number;
  corrected_claims_count?: number;
  cumulative_supported_evaluations?: number;
  cumulative_contradicted_evaluations?: number;
  cumulative_no_evidence_evaluations?: number;
  final_supported?: number;
  final_contradicted?: number;
  final_no_evidence?: number;
}

export interface TraceTriple {
  subject: string;
  relation: string;
  object: string;
  source_sentence?: string | null;
  evidence?: string | null;
}

export interface TraceEvaluatedClaim {
  triple: TraceTriple;
  label: string;
  reason?: string;
  evidence?: string;
  conflicting_object?: string | null;
  conflicting_fact?: TraceTriple | null;
  matched_kgc_fact?: TraceTriple | null;
  backtracking_action?: string | null;
}

export interface TraceFeedbackItem {
  triple: TraceTriple;
  label: string;
  instruction: string;
  reason?: string;
  evidence?: string;
  conflicting_object?: string | null;
  matched_kgc_fact?: TraceTriple | null;
  conflicting_fact?: TraceTriple | null;
  backtracking_action?: string | null;
}

export interface SubQuestionIteration {
  iteration: number;
  answer: string;
  supported_count: number;
  contradicted_count: number;
  no_evidence_count: number;
  extracted_claims?: TraceTriple[];
  aligned_claims?: TraceTriple[];
  evaluated_claims?: TraceEvaluatedClaim[];
  pre_enrichment_evaluated_claims?: TraceEvaluatedClaim[];
  backtracking_feedback?: TraceFeedbackItem[];
  question_target?: Record<string, unknown> | null;
  target_satisfied?: boolean;
  on_target_supported_count?: number;
  supported_but_irrelevant_count?: number;
  unsupported_target_count?: number;
  focused_enrichment_applied?: boolean;
  focused_facts_added?: KgcFact[];
  derived_facts_added?: KgcFact[];
  derivation_trace?: Record<string, unknown> | null;
  focused_extraction_raw?: KgcFact[];
  focused_extraction_filtered?: KgcFact[];
  answer_is_abstention?: boolean;
  evaluation_signature?: string;
  target_frame_trace?: Record<string, number> | null;
}

export interface WorkingKgcAddition {
  fact: KgcFact;
  provenance: string;
  extraction_scope?: string | null;
  sub_question_id?: number | null;
  dedupe_note?: string | null;
  derivation_type?: string | null;
  evidence_spans?: string[];
  derivation_explanation?: string | null;
}

export interface SubQuestionResult {
  sub_question_id: number;
  question: string;
  initial_answer: string;
  final_answer: string;
  stop_reason: string;
  iteration_count: number;
  iteration_history: SubQuestionIteration[];
  supported_count: number;
  contradicted_count: number;
  no_evidence_count: number;
  initial_supported?: number;
  initial_contradicted?: number;
  initial_no_evidence?: number;
  final_supported?: number;
  final_contradicted?: number;
  final_no_evidence?: number;
  revision_count?: number;
  resolved_without_revision?: boolean;
  question_target?: Record<string, unknown> | null;
  question_target_satisfied?: boolean;
  supported_but_irrelevant_count?: number;
  unsupported_target_count?: number;
  focused_facts_added_count?: number;
  proactive_focused_facts_added?: number;
  reactive_focused_facts_added?: number;
  working_kgc_count_after?: number;
  focused_extraction_raw?: KgcFact[];
  focused_extraction_filtered?: KgcFact[];
  focused_extraction_merged?: KgcFact[];
}

export interface KgcCandidateUpdate {
  fact: KgcFact;
  provenance: string;
  sub_question_id?: number | null;
  iteration?: number | null;
  promoted: boolean;
  rejection_reason?: string | null;
}

export interface DecomposedBacktrackingTrace {
  mode?: string;
  answer_0_mode?: string;
  provider_class?: string | null;
  model?: string | null;
  example_id?: string | null;
  context_extraction_format?: string | null;
  context_extraction_trace?: Record<string, unknown> | null;
  stage_providers?: Record<string, string>;
  structured_output_retries?: number;
  projection_method?: string | null;
  projection_source?: string | null;
  projection_faithfulness_passed?: boolean | null;
  compound_answer_0_source?: string | null;
  configured_num_ctx?: number | null;
  llm_call_telemetry?: Array<Record<string, unknown>>;
  neo4j_enabled?: boolean;
  neo4j_cleared_before_run?: boolean;
  neo4j_base_facts_persisted?: number;
  neo4j_working_facts_persisted?: number;
  kgc_evaluation_source?: string;
}

export interface DecomposedBacktrackingResult {
  example_id: string;
  original_question: string;
  context: string;
  sub_questions: SubQuestion[];
  sub_question_results: SubQuestionResult[];
  combined_answer: string;
  base_kgc_facts: KgcFact[];
  working_kgc_facts: KgcFact[];
  working_kgc_additions?: WorkingKgcAddition[];
  candidate_kgc_updates: KgcCandidateUpdate[];
  trace?: DecomposedBacktrackingTrace | null;
  metrics?: DecomposedExperimentMetrics | null;
  carry_forward_context?: string;
  max_iterations_per_sub_question: number;
}

export interface KgcRunOptions extends RunOptions {
  answer_0_mode?: Answer0Mode;
}

export interface DecomposedKgcRunOptions extends RunOptions {
  max_iterations_per_sub_question?: number;
  answer_0_mode?: Answer0Mode | "context_grounded_per_subquestion";
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
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // keep statusText fallback below
    }

    const detail =
      body && typeof body === "object" && "detail" in body
        ? (body as { detail: unknown }).detail
        : body;
    const { message, details } = formatApiErrorDetail(detail);
    throw new ApiError(message || response.statusText, details);
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

export async function runDecomposedKgcBacktracking(
  exampleId: string,
  options: DecomposedKgcRunOptions,
): Promise<DecomposedBacktrackingResult> {
  return apiFetch("/run-decomposed-kgc-backtracking", {
    method: "POST",
    body: JSON.stringify({
      example_id: exampleId,
      provider: options.provider,
      model: options.model,
      max_iterations_per_sub_question: options.max_iterations_per_sub_question ?? 3,
      working_kgc_auto_promote: false,
      answer_0_mode: options.answer_0_mode ?? "preset",
    }),
  });
}

export async function runCustomDecomposedKgcBacktracking(
  payload: {
    run_id?: string;
    question: string;
    context: string;
    initial_answer?: string;
    clear_neo4j_before_run: boolean;
    max_iterations_per_sub_question?: number;
  } & RunOptions,
): Promise<DecomposedBacktrackingResult> {
  return apiFetch("/run-decomposed-kgc-backtracking-custom", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      max_iterations_per_sub_question:
        payload.max_iterations_per_sub_question ?? 3,
    }),
  });
}

export interface BenchmarkSummary {
  id: string;
  title: string;
  domain: string;
  description: string;
  question_count: number;
  hop_distribution: Record<string, number>;
}

export interface BenchmarkQuestionSummary {
  id: string;
  hop_count: number;
  question: string;
}

export interface BenchmarkRunScore {
  benchmark_id: string;
  question_id: string;
  hop_count: number;
  expected_answer: string;
  exact_match: boolean;
  contains_expected_answer: boolean;
  resolved_by_pipeline: boolean;
}

export interface BenchmarkQuestionRunResponse {
  result: DecomposedBacktrackingResult;
  benchmark: BenchmarkRunScore;
}

export async function fetchBenchmarks(): Promise<BenchmarkSummary[]> {
  return apiFetch("/benchmarks");
}

export async function fetchBenchmarkQuestions(
  benchmarkId: string,
  hop?: number | "all",
): Promise<BenchmarkQuestionSummary[]> {
  const params =
    hop != null && hop !== "all" ? `?hop=${encodeURIComponent(String(hop))}` : "";
  return apiFetch(`/benchmarks/${encodeURIComponent(benchmarkId)}/questions${params}`);
}

export async function runBenchmarkQuestion(
  payload: {
    benchmark_id: string;
    question_id: string;
    clear_neo4j_before_run: boolean;
    max_iterations_per_sub_question?: number;
  } & RunOptions,
): Promise<BenchmarkQuestionRunResponse> {
  return apiFetch("/run-benchmark-question", {
    method: "POST",
    body: JSON.stringify({
      ...payload,
      max_iterations_per_sub_question:
        payload.max_iterations_per_sub_question ?? 3,
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
