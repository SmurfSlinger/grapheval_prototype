"""Parse and validate structured LLM outputs (CSV triples, JSON question splits)."""

from __future__ import annotations

import csv
import io
import json
import threading
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, TypeVar

from src.models import KgcFact, SubQuestion, Triple
from src.pipeline.debug_log import log_debug_event, write_raw_model_output_artifact
from src.pipeline.structured_triple_validation import (
    StructuredTripleAnomaly,
    coerce_raw_triple_item,
)

T = TypeVar("T")

CONTEXT_FACT_HEADERS = ("subject", "relation", "object", "evidence")
CLAIM_HEADERS = ("subject", "relation", "object", "source_sentence")

RAW_PREVIEW_LIMIT = 1200

# Per-thread / per-run anomaly buffers. Never share across concurrent requests.
_anomaly_state = threading.local()


def _last_parse_buffer() -> list[StructuredTripleAnomaly]:
    buf = getattr(_anomaly_state, "last_parse", None)
    if buf is None:
        buf = []
        _anomaly_state.last_parse = buf
    return buf


def _run_anomaly_buffer() -> list[StructuredTripleAnomaly]:
    buf = getattr(_anomaly_state, "run", None)
    if buf is None:
        buf = []
        _anomaly_state.run = buf
    return buf


def begin_anomaly_collection() -> None:
    """Start a request/run-local anomaly accumulator."""
    _anomaly_state.last_parse = []
    _anomaly_state.run = []


def end_anomaly_collection() -> None:
    _anomaly_state.last_parse = []
    _anomaly_state.run = []


def get_last_parse_anomalies() -> list[StructuredTripleAnomaly]:
    return list(_last_parse_buffer())


def get_run_parse_anomalies() -> list[StructuredTripleAnomaly]:
    return list(_run_anomaly_buffer())


def clear_last_parse_anomalies() -> None:
    """Clear only the last-parse snapshot; run accumulator is preserved."""
    _anomaly_state.last_parse = []


class StructuredOutputError(ValueError):
    """LLM returned malformed structured output."""


@dataclass
class ExtractionAttempt:
    attempt: int
    format: str
    raw_preview: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StructuredExtractionTrace:
    stage: str
    format_used: str | None = None
    retry_count: int = 0
    attempts: list[ExtractionAttempt] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "format_used": self.format_used,
            "retry_count": self.retry_count,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }


class KgcExtractionError(ValueError):
    """Context KGc extraction failed after retries; run must not continue."""

    def __init__(self, message: str, *, trace: StructuredExtractionTrace) -> None:
        super().__init__(message)
        self.trace = trace

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": str(self),
            "message": str(self),
            "stage": self.trace.stage,
            "attempts": [attempt.to_dict() for attempt in self.trace.attempts],
            "trace": self.trace.to_dict(),
        }


def raw_preview(text: str, limit: int = RAW_PREVIEW_LIMIT) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}…"


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines).strip()


def _looks_like_csv(text: str, headers: tuple[str, ...]) -> bool:
    first_line = text.strip().splitlines()[0].strip().lower() if text.strip() else ""
    return first_line == ",".join(headers)


def _row_is_blank(record: dict[str, str]) -> bool:
    return not any(value.strip() for value in record.values())


def parse_csv_rows(text: str, headers: tuple[str, ...]) -> list[dict[str, str]]:
    """Parse CSV with exact header row; validate width and required fields."""
    cleaned = _strip_code_fences(text)
    if not cleaned:
        raise StructuredOutputError("Empty CSV response.")

    if not _looks_like_csv(cleaned, headers):
        raise StructuredOutputError(
            f"CSV must start with header row: {','.join(headers)}"
        )

    reader = csv.DictReader(io.StringIO(cleaned))
    if reader.fieldnames is None:
        raise StructuredOutputError("CSV has no header row.")

    normalized_fieldnames = [name.strip().lower() for name in reader.fieldnames]
    expected = [h.lower() for h in headers]
    if normalized_fieldnames != expected:
        raise StructuredOutputError(
            f"CSV headers must be exactly {','.join(headers)}; "
            f"got {','.join(reader.fieldnames)}"
        )

    # DictReader keys keep original header casing; map case-insensitively.
    key_map = {
        name.strip().lower(): name for name in reader.fieldnames if name is not None
    }

    rows: list[dict[str, str]] = []
    for line_no, row in enumerate(reader, start=2):
        record = {
            header: (row.get(key_map[header.lower()]) or "").strip()
            for header in headers
        }
        if _row_is_blank(record):
            continue
        if not all(record[headers[i]] for i in range(3)):
            preview = ", ".join(f"{key}={value!r}" for key, value in record.items())
            raise StructuredOutputError(
                f"CSV row {line_no}: subject, relation, and object are required "
                f"(row={preview})."
            )
        rows.append(record)

    if not rows:
        raise StructuredOutputError("CSV contains no data rows.")
    return rows


def _record_anomaly(anomaly: StructuredTripleAnomaly) -> None:
    _last_parse_buffer().append(anomaly)
    _run_anomaly_buffer().append(anomaly)
    log_debug_event(
        "structured_triple_anomaly",
        anomaly.reason,
        anomaly.to_dict(),
    )


def _record_validated(validated, *, kind: str) -> None:
    log_debug_event(
        "structured_triple_validated",
        f"{kind}_accepted",
        validated.to_debug_dict(),
    )


def parse_context_facts_csv(text: str) -> list[KgcFact]:
    rows = parse_csv_rows(text, CONTEXT_FACT_HEADERS)
    facts: list[KgcFact] = []
    for row in rows:
        validated, anomaly = coerce_raw_triple_item(
            row,
            kind="fact",
            source_stage="context_fact_csv",
            provenance="trusted_context",
        )
        if anomaly is not None:
            _record_anomaly(anomaly)
            raise StructuredOutputError(
                f"Invalid context fact CSV row: {anomaly.reason}"
            )
        assert validated is not None
        _record_validated(validated, kind="fact")
        facts.append(
            KgcFact(
                subject=validated.subject,
                relation=validated.relation,
                object=validated.object,
                evidence=validated.evidence or (row.get("evidence") or None),
            )
        )
    return facts


def parse_claims_csv(text: str) -> list[Triple]:
    rows = parse_csv_rows(text, CLAIM_HEADERS)
    claims: list[Triple] = []
    for row in rows:
        validated, anomaly = coerce_raw_triple_item(
            row,
            kind="claim",
            source_stage="claim_csv",
            provenance="answer_claim",
        )
        if anomaly is not None:
            _record_anomaly(anomaly)
            raise StructuredOutputError(f"Invalid claim CSV row: {anomaly.reason}")
        assert validated is not None
        _record_validated(validated, kind="claim")
        claims.append(
            Triple(
                subject=validated.subject,
                relation=validated.relation,
                object=validated.object,
                source_sentence=validated.source_sentence
                or (row.get("source_sentence") or None),
            )
        )
    return claims


def parse_context_facts_json(text: str) -> list[KgcFact]:
    data = _parse_json_object(text)
    triples = data.get("triples")
    if not isinstance(triples, list):
        raise StructuredOutputError("JSON must contain a 'triples' list.")
    facts: list[KgcFact] = []
    for item in triples:
        validated, anomaly = coerce_raw_triple_item(
            item,
            kind="fact",
            source_stage="context_fact_json",
            provenance="trusted_context",
        )
        if anomaly is not None:
            _record_anomaly(anomaly)
            # Keep the run alive when other triples remain usable.
            continue
        assert validated is not None
        _record_validated(validated, kind="fact")
        facts.append(
            KgcFact(
                subject=validated.subject,
                relation=validated.relation,
                object=validated.object,
                evidence=validated.evidence,
            )
        )
    if not facts and triples:
        raise StructuredOutputError(
            "All context-fact triples were rejected by structured validation."
        )
    return facts


def parse_claims_json(text: str) -> list[Triple]:
    data = _parse_json_object(text)
    triples = data.get("triples")
    if not isinstance(triples, list):
        raise StructuredOutputError("JSON must contain a 'triples' list.")
    claims: list[Triple] = []
    for item in triples:
        validated, anomaly = coerce_raw_triple_item(
            item,
            kind="claim",
            source_stage="claim_json",
            provenance="answer_claim",
        )
        if anomaly is not None:
            _record_anomaly(anomaly)
            continue
        assert validated is not None
        _record_validated(validated, kind="claim")
        claims.append(
            Triple(
                subject=validated.subject,
                relation=validated.relation,
                object=validated.object,
                source_sentence=validated.source_sentence,
            )
        )
    if not claims and triples:
        raise StructuredOutputError(
            "All claim triples were rejected by structured validation."
        )
    return claims


def parse_context_facts_response(text: str) -> list[KgcFact]:
    """Accept CSV or legacy JSON triples."""
    clear_last_parse_anomalies()
    raw_artifact = write_raw_model_output_artifact(
        stage="context_fact_extraction",
        raw_text=text,
        format_hint="context_facts",
    )
    log_debug_event(
        "context_fact_raw_response",
        "received",
        {
            "raw_preview": raw_preview(text),
            "raw_chars": len(text),
            "raw_artifact_path": raw_artifact,
        },
    )
    cleaned = _strip_code_fences(text)
    if _looks_like_csv(cleaned, CONTEXT_FACT_HEADERS):
        facts = parse_context_facts_csv(cleaned)
    else:
        facts = parse_context_facts_json(cleaned)
    log_debug_event(
        "context_fact_parsed",
        "parsed",
        {
            "fact_count": len(facts),
            "anomaly_count": len(_last_parse_buffer()),
            "facts": [
                {
                    "subject": fact.subject,
                    "relation": fact.relation,
                    "object": fact.object,
                }
                for fact in facts
            ],
        },
    )
    return facts


def parse_claims_response(text: str) -> list[Triple]:
    """Accept CSV or legacy JSON triples."""
    clear_last_parse_anomalies()
    raw_artifact = write_raw_model_output_artifact(
        stage="claim_extraction",
        raw_text=text,
        format_hint="claims",
    )
    log_debug_event(
        "claim_extraction_raw_response",
        "received",
        {
            "raw_preview": raw_preview(text),
            "raw_chars": len(text),
            "raw_artifact_path": raw_artifact,
        },
    )
    cleaned = _strip_code_fences(text)
    if _looks_like_csv(cleaned, CLAIM_HEADERS):
        claims = parse_claims_csv(cleaned)
    else:
        claims = parse_claims_json(cleaned)
    log_debug_event(
        "claim_parsed",
        "parsed",
        {
            "claim_count": len(claims),
            "anomaly_count": len(_last_parse_buffer()),
            "claims": [
                {
                    "subject": claim.subject,
                    "relation": claim.relation,
                    "object": claim.object,
                }
                for claim in claims
            ],
        },
    )
    return claims


def parse_question_split_response(text: str) -> list[SubQuestion]:
    data = _parse_json_object(text)
    if not isinstance(data, dict):
        raise StructuredOutputError("Question split must be a JSON object.")

    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise StructuredOutputError("'questions' must be a non-empty list.")

    parsed: list[SubQuestion] = []
    seen_ids: set[int] = set()
    for item in questions:
        if not isinstance(item, dict):
            raise StructuredOutputError("Each sub-question must be an object.")
        if "id" not in item or "question" not in item:
            raise StructuredOutputError("Each sub-question needs 'id' and 'question'.")

        sub_id = item["id"]
        if not isinstance(sub_id, int):
            raise StructuredOutputError(f"Sub-question id must be integer, got {sub_id!r}.")
        if sub_id in seen_ids:
            raise StructuredOutputError(f"Duplicate sub-question id: {sub_id}.")
        seen_ids.add(sub_id)

        question = str(item["question"]).strip()
        if not question:
            raise StructuredOutputError(f"Sub-question {sub_id} has empty question text.")

        parsed.append(SubQuestion(id=sub_id, question=question))

    parsed.sort(key=lambda sq: sq.id)
    expected_ids = list(range(1, len(parsed) + 1))
    actual_ids = [sq.id for sq in parsed]
    if actual_ids != expected_ids:
        raise StructuredOutputError(
            f"Sub-question ids must be unique sequential integers starting at 1; "
            f"got {actual_ids}."
        )
    return parsed


def parse_sub_answer_projection_response(
    text: str,
    expected_ids: list[int],
) -> list[SubQuestionInitialAnswer]:
    from src.models import SubQuestionInitialAnswer

    data = _parse_json_object(text)
    answers = data.get("answers")
    if not isinstance(answers, list) or not answers:
        raise StructuredOutputError("'answers' must be a non-empty list.")

    parsed: list[SubQuestionInitialAnswer] = []
    seen_ids: set[int] = set()
    for item in answers:
        if not isinstance(item, dict):
            raise StructuredOutputError("Each projected answer must be an object.")
        if "id" not in item or "answer" not in item:
            raise StructuredOutputError("Each projected answer needs 'id' and 'answer'.")
        sub_id = item["id"]
        if not isinstance(sub_id, int):
            raise StructuredOutputError(f"Projected answer id must be integer, got {sub_id!r}.")
        if sub_id in seen_ids:
            raise StructuredOutputError(f"Duplicate projected answer id: {sub_id}.")
        seen_ids.add(sub_id)
        answer = str(item["answer"]).strip()
        if not answer:
            raise StructuredOutputError(f"Projected answer for id {sub_id} is empty.")
        parsed.append(SubQuestionInitialAnswer(sub_question_id=sub_id, answer=answer))

    parsed.sort(key=lambda item: item.sub_question_id)
    actual_ids = [item.sub_question_id for item in parsed]
    if actual_ids != expected_ids:
        raise StructuredOutputError(
            f"Projected answer ids must match sub-questions exactly; "
            f"expected {expected_ids}, got {actual_ids}."
        )
    return parsed


def _balance_json_suffix(text: str) -> str:
    """Append missing closing brackets/braces when LLM output is truncated."""
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch == "}" and stack and stack[-1] == "}":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "]":
            stack.pop()
    return text + "".join(reversed(stack))


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = _strip_code_fences(text)
    start = cleaned.find("{")
    if start == -1:
        raise StructuredOutputError(
            f"No JSON object found. Snippet: {cleaned[:300]}"
        )
    fragment = cleaned[start:]
    candidates = [fragment]
    end = cleaned.rfind("}")
    if end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])
    candidates.append(_balance_json_suffix(fragment))

    last_exc: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_exc = exc
            continue
        if not isinstance(payload, dict):
            raise StructuredOutputError("Top-level JSON value must be an object.")
        return payload

    assert last_exc is not None
    raise StructuredOutputError(
        f"Invalid JSON: {last_exc}. Snippet: {fragment[:300]}"
    ) from last_exc


def complete_with_retry(
    complete_fn: Callable[[str], str],
    prompt: str,
    parser: Callable[[str], T],
    *,
    retry_suffix: str = (
        "\n\nReturn ONLY the required structured output with no prose before or after."
    ),
) -> tuple[T, int]:
    """Call LLM once; retry once on StructuredOutputError. Returns (result, retry_count)."""
    raw = complete_fn(prompt)
    try:
        return parser(raw), 0
    except StructuredOutputError:
        raw = complete_fn(prompt + retry_suffix)
        return parser(raw), 1


def complete_with_trace(
    complete_fn: Callable[[str], str],
    prompt: str,
    parser: Callable[[str], T],
    *,
    stage: str,
    output_format: str,
    retry_suffix: str | None = None,
    alternate_prompt: str | None = None,
) -> tuple[T, StructuredExtractionTrace]:
    """Parse with one retry; optional alternate prompt switches format on final attempt."""
    trace = StructuredExtractionTrace(stage=stage)
    suffix = retry_suffix or (
        "\n\nReturn ONLY the required structured output with no prose before or after."
    )

    raw = complete_fn(prompt)
    trace.attempts.append(
        ExtractionAttempt(
            attempt=1,
            format=output_format,
            raw_preview=raw_preview(raw),
        )
    )
    try:
        parsed = parser(raw)
        trace.format_used = output_format
        return parsed, trace
    except StructuredOutputError as first_exc:
        trace.attempts[-1].error = str(first_exc)
        trace.retry_count = 1

        retry_prompt = alternate_prompt if alternate_prompt is not None else prompt + suffix
        retry_format = "json" if alternate_prompt is not None else output_format
        raw_retry = complete_fn(retry_prompt)
        trace.attempts.append(
            ExtractionAttempt(
                attempt=2,
                format=retry_format,
                raw_preview=raw_preview(raw_retry),
            )
        )
        try:
            parsed = parser(raw_retry)
            trace.format_used = retry_format
            return parsed, trace
        except StructuredOutputError as second_exc:
            trace.attempts[-1].error = str(second_exc)
            raise KgcExtractionError(
                f"{stage} failed after {len(trace.attempts)} attempts: {second_exc}",
                trace=trace,
            ) from second_exc
