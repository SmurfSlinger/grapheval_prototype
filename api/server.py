"""FastAPI server exposing the GraphEval pipeline over HTTP."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
from src.pipeline.runner import PipelineRunner
from src.storage.neo4j_store import query_claims_if_enabled

app = FastAPI(title="GraphEval Prototype API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
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
