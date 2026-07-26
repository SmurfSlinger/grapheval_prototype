"""FastAPI server exposing the GraphEval pipeline over HTTP."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.benchmarks import (
    get_question,
    is_approved_benchmark,
    list_benchmarks,
    list_questions,
    score_result,
    trusted_context,
)
from src.config import DEFAULT_MODEL
from src.io_utils import load_examples, result_filename, save_result
from src.llm.ollama_provider import (
    OllamaConnectionError,
    OllamaError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from src.main import get_provider
from src.models import Example
from src.pipeline.backtracking_runner import BacktrackingRunner
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner
from src.pipeline.runner import PipelineRunner
from src.pipeline.structured_output import KgcExtractionError
from src.storage.neo4j_store import query_claims_if_enabled

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="GraphEval Prototype API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://fedora-desktop:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    example_id: str
    provider: Literal["mock", "ollama"] = "mock"
    model: str = DEFAULT_MODEL


class RunCustomRequest(BaseModel):
    question: str
    context: str
    initial_answer: str
    provider: Literal["mock", "ollama"] = "mock"
    model: str = DEFAULT_MODEL


class RunAllRequest(BaseModel):
    provider: Literal["mock", "ollama"] = "mock"
    model: str = DEFAULT_MODEL


class RunKgcBacktrackingRequest(BaseModel):
    example_id: str
    provider: Literal["mock", "ollama"] = "mock"
    model: str = DEFAULT_MODEL
    max_iterations: int = 1
    answer_0_mode: Literal["preset", "generated"] = "preset"


class RunDecomposedKgcBacktrackingRequest(BaseModel):
    example_id: str
    provider: Literal["mock", "ollama"] = "mock"
    model: str = DEFAULT_MODEL
    max_iterations_per_sub_question: int = 3
    working_kgc_auto_promote: bool = False
    answer_0_mode: Literal[
        "preset",
        "generated",
        "context_grounded_per_subquestion",
    ] = "preset"


class RunCustomDecomposedKgcBacktrackingRequest(BaseModel):
    run_id: str | None = None
    question: str
    context: str
    initial_answer: str | None = None
    provider: Literal["mock", "ollama"] = "mock"
    model: str = DEFAULT_MODEL
    max_iterations_per_sub_question: int = 3
    answer_0_mode: Literal[
        "preset_external_projected",
        "generated_external_projected",
        "context_grounded_per_subquestion",
    ] | None = None
    clear_neo4j_before_run: bool = True


class RunBenchmarkQuestionRequest(BaseModel):
    benchmark_id: str
    question_id: str
    provider: Literal["mock", "ollama"] = "mock"
    model: str = DEFAULT_MODEL
    max_iterations_per_sub_question: int = 3
    clear_neo4j_before_run: bool = True


class ExampleSummary(BaseModel):
    id: str
    question: str
    context: str
    initial_answer: str | None = None


class StoredClaim(BaseModel):
    subject: str
    relation: str
    object: str
    label: str
    reason: str
    evidence: str
    example_id: str
    answer_stage: str


class GraphClaimsResponse(BaseModel):
    enabled: bool
    claims: list[StoredClaim]
    error: str | None = None


def _make_decomposed_backtracking_runner(
    provider_name: str,
    model: str,
    *,
    max_iterations_per_sub_question: int = 3,
    working_kgc_auto_promote: bool = False,
    answer_0_mode: str = "preset",
    clear_neo4j_before_run: bool = False,
    neo4j_readback: bool = False,
    require_neo4j: bool = False,
) -> DecomposedBacktrackingRunner:
    try:
        provider = get_provider(provider_name, model=model, fallback_to_mock=False)
    except OllamaError as exc:
        raise _ollama_http_error(exc) from exc
    return DecomposedBacktrackingRunner(
        provider,
        max_iterations_per_sub_question=max_iterations_per_sub_question,
        working_kgc_auto_promote=working_kgc_auto_promote,
        answer_0_mode=answer_0_mode,
        clear_neo4j_before_run=clear_neo4j_before_run,
        neo4j_readback=neo4j_readback,
        require_neo4j=require_neo4j,
    )


def _make_backtracking_runner(
    provider_name: str,
    model: str,
    max_iterations: int = 1,
) -> BacktrackingRunner:
    try:
        provider = get_provider(provider_name, model=model, fallback_to_mock=False)
    except OllamaError as exc:
        raise _ollama_http_error(exc) from exc
    return BacktrackingRunner(provider, max_iterations=max_iterations)


def _make_runner(provider_name: str, model: str) -> PipelineRunner:
    try:
        provider = get_provider(provider_name, model=model, fallback_to_mock=False)
    except OllamaError as exc:
        raise _ollama_http_error(exc) from exc
    return PipelineRunner(provider)


def _run_example(example: Example, provider_name: str, model: str) -> dict[str, Any]:
    runner = _make_runner(provider_name, model)
    try:
        result = runner.run_example(example)
    except (OllamaError, ValueError) as exc:
        if isinstance(exc, OllamaError):
            raise _ollama_http_error(exc) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    fname = result_filename(example.id, model) if provider_name == "ollama" else None
    save_result(result, filename=fname)
    return result.to_dict()


def _ollama_http_error(exc: OllamaError) -> HTTPException:
    if isinstance(exc, OllamaConnectionError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, OllamaModelNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, OllamaTimeoutError):
        return HTTPException(status_code=504, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


def _log_kgc_extraction_failure(
    *,
    example_id: str,
    exc: KgcExtractionError,
) -> None:
    logger.error(
        "Decomposed KGc extraction failed for example=%s stage=%s error=%s",
        example_id,
        exc.trace.stage,
        exc,
    )
    for attempt in exc.trace.attempts:
        if attempt.error:
            logger.error(
                "  attempt=%s format=%s parser_error=%s",
                attempt.attempt,
                attempt.format,
                attempt.error,
            )


def _log_decomposed_runtime_failure(
    *,
    example_id: str,
    exc: Exception,
) -> None:
    logger.error(
        "Decomposed KGc run failed for example=%s error=%s",
        example_id,
        exc,
        exc_info=True,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _graph_claims_response(
    *,
    example_id: str | None = None,
    limit: int = 50,
    bad_only: bool = False,
) -> GraphClaimsResponse:
    enabled, claims, error = query_claims_if_enabled(
        example_id=example_id,
        limit=limit,
        bad_only=bad_only,
    )
    return GraphClaimsResponse(
        enabled=enabled,
        claims=[StoredClaim(**claim) for claim in claims],
        error=error,
    )


@app.get("/graph/claims", response_model=GraphClaimsResponse)
def get_graph_claims(
    limit: int = 50,
    example_id: str | None = None,
) -> GraphClaimsResponse:
    return _graph_claims_response(example_id=example_id, limit=limit)


@app.get("/graph/bad-claims", response_model=GraphClaimsResponse)
def get_graph_bad_claims(limit: int = 50) -> GraphClaimsResponse:
    return _graph_claims_response(limit=limit, bad_only=True)


@app.get("/examples", response_model=list[ExampleSummary])
def list_examples() -> list[ExampleSummary]:
    return [
        ExampleSummary(
            id=ex.id,
            question=ex.question,
            context=ex.context,
            initial_answer=ex.initial_answer,
        )
        for ex in load_examples()
    ]


@app.post("/run")
def run_example(request: RunRequest) -> dict[str, Any]:
    examples = {ex.id: ex for ex in load_examples()}
    if request.example_id not in examples:
        raise HTTPException(status_code=404, detail=f"Example not found: {request.example_id}")
    return _run_example(examples[request.example_id], request.provider, request.model)


@app.post("/run-kgc-backtracking")
def run_kgc_backtracking(request: RunKgcBacktrackingRequest) -> dict[str, Any]:
    examples = {ex.id: ex for ex in load_examples()}
    if request.example_id not in examples:
        raise HTTPException(status_code=404, detail=f"Example not found: {request.example_id}")

    runner = _make_backtracking_runner(
        request.provider,
        request.model,
        max_iterations=request.max_iterations,
    )
    try:
        result = runner.run_example(
            examples[request.example_id],
            answer_0_mode=request.answer_0_mode,
        )
    except (OllamaError, ValueError) as exc:
        if isinstance(exc, OllamaError):
            raise _ollama_http_error(exc) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result.to_dict()


@app.post("/run-decomposed-kgc-backtracking")
def run_decomposed_kgc_backtracking(
    request: RunDecomposedKgcBacktrackingRequest,
) -> dict[str, Any]:
    examples = {ex.id: ex for ex in load_examples()}
    if request.example_id not in examples:
        raise HTTPException(status_code=404, detail=f"Example not found: {request.example_id}")

    runner = _make_decomposed_backtracking_runner(
        request.provider,
        request.model,
        max_iterations_per_sub_question=request.max_iterations_per_sub_question,
        working_kgc_auto_promote=request.working_kgc_auto_promote,
        answer_0_mode=request.answer_0_mode,
    )
    try:
        result = runner.run_example(examples[request.example_id])
    except KgcExtractionError as exc:
        _log_kgc_extraction_failure(example_id=request.example_id, exc=exc)
        raise HTTPException(status_code=422, detail=exc.to_dict()) from exc
    except (OllamaError, ValueError) as exc:
        _log_decomposed_runtime_failure(example_id=request.example_id, exc=exc)
        if isinstance(exc, OllamaError):
            raise _ollama_http_error(exc) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result.to_dict()


@app.get("/benchmarks")
def get_benchmarks() -> list[dict[str, Any]]:
    return list_benchmarks()


@app.get("/benchmarks/{benchmark_id}/questions")
def get_benchmark_questions(
    benchmark_id: str,
    hop: int | None = None,
) -> list[dict[str, Any]]:
    if not is_approved_benchmark(benchmark_id):
        raise HTTPException(status_code=404, detail=f"Unknown benchmark_id: {benchmark_id}")
    if hop is not None and hop not in range(1, 11):
        raise HTTPException(status_code=400, detail="hop must be an integer from 1 to 10")
    try:
        return list_questions(benchmark_id, hop=hop)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/run-benchmark-question")
def run_benchmark_question(
    request: RunBenchmarkQuestionRequest,
) -> dict[str, Any]:
    if not is_approved_benchmark(request.benchmark_id):
        raise HTTPException(
            status_code=404,
            detail=f"Unknown benchmark_id: {request.benchmark_id}",
        )
    try:
        question = get_question(request.benchmark_id, request.question_id)
        context = trusted_context(request.benchmark_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    question_text = str(question.get("question") or "").strip()
    if not question_text:
        raise HTTPException(status_code=422, detail="Benchmark question text is empty")

    example = Example(
        id=str(question["id"]),
        question=question_text,
        context=context,
        initial_answer=None,
    )
    runner = _make_decomposed_backtracking_runner(
        request.provider,
        request.model,
        max_iterations_per_sub_question=request.max_iterations_per_sub_question,
        working_kgc_auto_promote=False,
        answer_0_mode="generated_external_projected",
        clear_neo4j_before_run=request.clear_neo4j_before_run,
        neo4j_readback=True,
        require_neo4j=True,
    )
    try:
        result = runner.run_example(example)
    except KgcExtractionError as exc:
        _log_kgc_extraction_failure(example_id=example.id, exc=exc)
        raise HTTPException(status_code=422, detail=exc.to_dict()) from exc
    except OllamaError as exc:
        _log_decomposed_runtime_failure(example_id=example.id, exc=exc)
        raise _ollama_http_error(exc) from exc
    except (RuntimeError, ValueError) as exc:
        _log_decomposed_runtime_failure(example_id=example.id, exc=exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    result_payload = result.to_dict()
    return {
        "result": result_payload,
        "benchmark": score_result(
            benchmark_id=request.benchmark_id,
            question=question,
            result=result,
        ),
        "debug_log_path": result_payload.get("debug_log_path"),
    }


@app.post("/run-decomposed-kgc-backtracking-custom")
def run_custom_decomposed_kgc_backtracking(
    request: RunCustomDecomposedKgcBacktrackingRequest,
) -> dict[str, Any]:
    question = request.question.strip()
    context = request.context.strip()
    initial_answer = (request.initial_answer or "").strip() or None
    run_id = (request.run_id or "").strip() or f"custom_{uuid.uuid4().hex[:8]}"
    if not question or not context:
        raise HTTPException(status_code=400, detail="question and context are required")
    if len(run_id) > 120:
        raise HTTPException(status_code=400, detail="run_id must be 120 characters or fewer")

    answer_0_mode = request.answer_0_mode or (
        "preset_external_projected"
        if initial_answer
        else "generated_external_projected"
    )
    example = Example(
        id=run_id,
        question=question,
        context=context,
        initial_answer=initial_answer,
    )
    runner = _make_decomposed_backtracking_runner(
        request.provider,
        request.model,
        max_iterations_per_sub_question=request.max_iterations_per_sub_question,
        working_kgc_auto_promote=False,
        answer_0_mode=answer_0_mode,
        clear_neo4j_before_run=request.clear_neo4j_before_run,
        neo4j_readback=True,
        require_neo4j=True,
    )
    try:
        return runner.run_example(example).to_dict()
    except KgcExtractionError as exc:
        _log_kgc_extraction_failure(example_id=run_id, exc=exc)
        raise HTTPException(status_code=422, detail=exc.to_dict()) from exc
    except OllamaError as exc:
        _log_decomposed_runtime_failure(example_id=run_id, exc=exc)
        raise _ollama_http_error(exc) from exc
    except (RuntimeError, ValueError) as exc:
        _log_decomposed_runtime_failure(example_id=run_id, exc=exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/run-custom")
def run_custom(request: RunCustomRequest) -> dict[str, Any]:
    example = Example(
        id=f"custom_{uuid.uuid4().hex[:8]}",
        question=request.question.strip(),
        context=request.context.strip(),
        initial_answer=request.initial_answer.strip(),
    )
    if not example.question or not example.context or not example.initial_answer:
        raise HTTPException(
            status_code=400,
            detail="question, context, and initial_answer are required",
        )
    return _run_example(example, request.provider, request.model)


@app.post("/run-all")
def run_all_examples(request: RunAllRequest) -> list[dict[str, Any]]:
    runner = _make_runner(request.provider, request.model)
    results: list[dict[str, Any]] = []

    for example in load_examples():
        try:
            result = runner.run_example(example)
        except (OllamaError, ValueError) as exc:
            if isinstance(exc, OllamaError):
                raise _ollama_http_error(exc) from exc
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        fname = (
            result_filename(example.id, request.model)
            if request.provider == "ollama"
            else None
        )
        save_result(result, filename=fname)
        results.append(result.to_dict())

    return results
