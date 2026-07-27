"""Execution-isolated Neo4j persistence for GraphEval runs.

Every entity node is scoped by ``(execution_id, name)`` and every FACT/CLAIM
relationship carries its ``execution_id``, so repeated attempts of the same
question never share or overwrite graph state. Reads are always
execution-scoped; the only whole-graph operation is the explicit development
reset (:meth:`Neo4jStore.clear_all` / :func:`reset_neo4j_dev_if_enabled`).
"""

from __future__ import annotations

import sys

from src.config import (
    NEO4J_DATABASE,
    NEO4J_ENABLED,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
)
from src.models import (
    KgcEvaluationResult,
    KgcFact,
    VerificationResult,
    WorkingKgcAddition,
)
from src.pipeline.execution_context import ExecutionScope

BAD_CLAIM_LABELS = ("CONTRADICTED", "NO_EVIDENCE", "NOT_ENOUGH_INFO")


class Neo4jStore:
    """Store per-execution Entity nodes linked by FACT/CLAIM relationships."""

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
        database: str = NEO4J_DATABASE,
    ) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    def close(self) -> None:
        self._driver.close()

    def _session(self):
        return self._driver.session(database=self._database)

    def verify_connectivity(self) -> None:
        self._driver.verify_connectivity()

    def clear_all(self) -> None:
        """Full development reset: delete every node and relationship.

        This intentionally destroys all executions. For anything scoped to a
        single pipeline attempt use :meth:`clear_execution` instead.
        """
        with self._session() as session:
            session.run("MATCH (n) DETACH DELETE n").consume()

    def clear_execution(self, execution_id: str) -> dict[str, int]:
        """Delete only the entities and relationships of one execution."""
        with self._session() as session:
            summary = session.run(
                "MATCH (n:Entity {execution_id: $execution_id}) DETACH DELETE n",
                execution_id=execution_id,
            ).consume()
        return {"nodes_deleted": summary.counters.nodes_deleted}

    _CLAIM_FIELDS = """
        s.name AS subject,
        c.relation AS relation,
        o.name AS object,
        c.label AS label,
        c.reason AS reason,
        c.evidence AS evidence,
        c.execution_id AS execution_id,
        c.example_id AS example_id,
        c.benchmark_id AS benchmark_id,
        c.question_id AS question_id,
        c.sub_question_id AS sub_question_id,
        c.answer_stage AS answer_stage,
        c.iteration AS iteration,
        c.source AS source
    """

    def get_claims(self, execution_id: str, limit: int = 200) -> list[dict[str, object]]:
        """Return CLAIM relationships belonging to one execution only."""
        query = f"""
        MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
        WHERE c.execution_id = $execution_id
        RETURN {self._CLAIM_FIELDS}
        ORDER BY c.sub_question_id, c.iteration
        LIMIT $limit
        """
        with self._session() as session:
            result = session.run(query, execution_id=execution_id, limit=limit)
            return [dict(record) for record in result]

    def get_claims_for_example(
        self, example_id: str, limit: int = 200
    ) -> list[dict[str, object]]:
        """Legacy example-scoped view (an example may span several executions)."""
        query = f"""
        MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
        WHERE c.example_id = $example_id
        RETURN {self._CLAIM_FIELDS}
        ORDER BY c.execution_id, c.sub_question_id, c.iteration
        LIMIT $limit
        """
        with self._session() as session:
            result = session.run(query, example_id=example_id, limit=limit)
            return [dict(record) for record in result]

    def get_bad_claims(
        self, execution_id: str, limit: int = 200
    ) -> list[dict[str, object]]:
        """CONTRADICTED / NO_EVIDENCE (and legacy NOT_ENOUGH_INFO) claims."""
        query = f"""
        MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
        WHERE c.execution_id = $execution_id AND c.label IN $bad_labels
        RETURN {self._CLAIM_FIELDS}
        ORDER BY c.sub_question_id, c.iteration
        LIMIT $limit
        """
        with self._session() as session:
            result = session.run(
                query,
                execution_id=execution_id,
                bad_labels=list(BAD_CLAIM_LABELS),
                limit=limit,
            )
            return [dict(record) for record in result]

    def get_execution_summary(self, execution_id: str) -> dict[str, object]:
        """Entity/FACT/CLAIM counts plus claim-label breakdown for one execution."""
        with self._session() as session:
            entity_record = session.run(
                "MATCH (e:Entity {execution_id: $execution_id}) RETURN count(e) AS c",
                execution_id=execution_id,
            ).single()
            fact_record = session.run(
                """
                MATCH ()-[r:FACT]->()
                WHERE r.execution_id = $execution_id
                RETURN count(r) AS c
                """,
                execution_id=execution_id,
            ).single()
            claim_records = session.run(
                """
                MATCH ()-[r:CLAIM]->()
                WHERE r.execution_id = $execution_id
                RETURN r.label AS label, count(r) AS c
                """,
                execution_id=execution_id,
            )
            claim_labels = {
                str(record["label"]): int(record["c"]) for record in claim_records
            }
        return {
            "execution_id": execution_id,
            "entity_count": int(entity_record["c"]) if entity_record else 0,
            "fact_count": int(fact_record["c"]) if fact_record else 0,
            "claim_count": sum(claim_labels.values()),
            "claim_labels": claim_labels,
        }

    def store_kgc_facts(self, scope: ExecutionScope, facts: list[KgcFact]) -> None:
        if not facts:
            return
        with self._session() as session:
            for created_order, fact in enumerate(facts):
                session.execute_write(
                    self._create_fact,
                    scope,
                    fact,
                    created_order,
                )

    def get_kgc_facts(self, execution_id: str) -> list[KgcFact]:
        """Reconstruct trusted FACT relationships for one execution only."""
        query = """
        MATCH (s:Entity)-[f:FACT]->(o:Entity)
        WHERE f.execution_id = $execution_id
        RETURN s.name AS subject, f.relation AS relation, o.name AS object,
               f.evidence AS evidence
        ORDER BY f.created_order, subject, relation, object
        """
        with self._session() as session:
            result = session.run(query, execution_id=execution_id)
            return [
                KgcFact(
                    subject=record["subject"],
                    relation=record["relation"],
                    object=record["object"],
                    evidence=record["evidence"] or None,
                )
                for record in result
            ]

    def get_fact_records(self, execution_id: str) -> list[dict[str, object]]:
        """Full FACT metadata for one execution (provenance round-trip checks)."""
        query = """
        MATCH (s:Entity)-[f:FACT]->(o:Entity)
        WHERE f.execution_id = $execution_id
        RETURN
            s.name AS subject,
            f.relation AS relation,
            o.name AS object,
            f.evidence AS evidence,
            f.execution_id AS execution_id,
            f.example_id AS example_id,
            f.benchmark_id AS benchmark_id,
            f.question_id AS question_id,
            f.sub_question_id AS sub_question_id,
            f.provenance AS provenance,
            f.source AS source,
            f.extraction_stage AS extraction_stage,
            f.created_order AS created_order,
            f.derivation_type AS derivation_type,
            f.derivation_explanation AS derivation_explanation
        ORDER BY f.created_order, subject, relation, object
        """
        with self._session() as session:
            result = session.run(query, execution_id=execution_id)
            return [dict(record) for record in result]

    def get_relationship_counts(self, execution_id: str) -> dict[str, int]:
        """Actual FACT and CLAIM relationship counts for one execution."""
        with self._session() as session:
            fact_record = session.run(
                """
                MATCH ()-[r:FACT]->()
                WHERE r.execution_id = $execution_id
                RETURN count(r) AS count
                """,
                execution_id=execution_id,
            ).single()
            claim_record = session.run(
                """
                MATCH ()-[r:CLAIM]->()
                WHERE r.execution_id = $execution_id
                RETURN count(r) AS count
                """,
                execution_id=execution_id,
            ).single()
        return {
            "fact_edges": int(fact_record["count"]) if fact_record else 0,
            "claim_edges": int(claim_record["count"]) if claim_record else 0,
        }

    def store_working_kgc_additions(
        self,
        scope: ExecutionScope,
        additions: list[WorkingKgcAddition],
    ) -> None:
        if not additions:
            return
        with self._session() as session:
            for created_order, addition in enumerate(additions):
                session.execute_write(
                    self._create_working_fact,
                    scope,
                    addition,
                    created_order,
                )

    def store_kgc_claims(
        self,
        scope: ExecutionScope,
        iteration: int,
        evaluations: list[KgcEvaluationResult],
        answer_stage: str | None = None,
        sub_question_id: int | None = None,
    ) -> None:
        if not evaluations:
            return
        stage = answer_stage if answer_stage else f"answer_{iteration}"
        with self._session() as session:
            for evaluation in evaluations:
                session.execute_write(
                    self._create_kgc_claim,
                    scope,
                    iteration,
                    stage,
                    sub_question_id,
                    evaluation,
                )

    def store_verified_triples(
        self,
        scope: ExecutionScope,
        answer_stage: str,
        verification_results: list[VerificationResult],
    ) -> None:
        if not verification_results:
            return

        with self._session() as session:
            for result in verification_results:
                session.execute_write(
                    self._create_claim,
                    scope,
                    answer_stage,
                    result,
                )

    @staticmethod
    def _create_fact(
        tx,
        scope: ExecutionScope,
        fact: KgcFact,
        created_order: int,
    ) -> None:
        query = """
        MERGE (s:Entity {execution_id: $execution_id, name: $subject})
        MERGE (o:Entity {execution_id: $execution_id, name: $object})
        MERGE (s)-[f:FACT {
            execution_id: $execution_id,
            relation: $relation,
            provenance: "trusted_context",
            extraction_stage: "context_triple_extraction"
        }]->(o)
        SET f.example_id = $example_id,
            f.benchmark_id = $benchmark_id,
            f.question_id = $question_id,
            f.evidence = $evidence,
            f.source = "trusted_context",
            f.created_order = $created_order
        """
        tx.run(
            query,
            subject=fact.subject,
            object=fact.object,
            relation=fact.relation,
            evidence=fact.evidence or "",
            execution_id=scope.execution_id,
            example_id=scope.example_id,
            benchmark_id=scope.benchmark_id,
            question_id=scope.question_id,
            created_order=created_order,
        )

    @staticmethod
    def _create_working_fact(
        tx,
        scope: ExecutionScope,
        addition: WorkingKgcAddition,
        created_order: int,
    ) -> None:
        fact = addition.fact
        provenance = addition.provenance.value
        query = """
        MERGE (s:Entity {execution_id: $execution_id, name: $subject})
        MERGE (o:Entity {execution_id: $execution_id, name: $object})
        MERGE (s)-[f:FACT {
            execution_id: $execution_id,
            relation: $relation,
            provenance: $provenance,
            extraction_stage: $extraction_stage
        }]->(o)
        SET f.example_id = $example_id,
            f.benchmark_id = $benchmark_id,
            f.question_id = $question_id,
            f.sub_question_id = $sub_question_id,
            f.evidence = $evidence,
            f.source = $provenance,
            f.derivation_type = $derivation_type,
            f.evidence_spans = $evidence_spans,
            f.derivation_explanation = $derivation_explanation,
            f.created_order = $created_order
        """
        tx.run(
            query,
            subject=fact.subject,
            object=fact.object,
            relation=fact.relation,
            evidence=fact.evidence or "",
            execution_id=scope.execution_id,
            example_id=scope.example_id,
            benchmark_id=scope.benchmark_id,
            question_id=scope.question_id,
            provenance=provenance,
            extraction_stage=addition.extraction_scope,
            sub_question_id=addition.sub_question_id,
            derivation_type=addition.derivation_type or "",
            evidence_spans=addition.evidence_spans,
            derivation_explanation=addition.derivation_explanation or "",
            created_order=created_order,
        )

    @staticmethod
    def _create_kgc_claim(
        tx,
        scope: ExecutionScope,
        iteration: int,
        answer_stage: str,
        sub_question_id: int | None,
        evaluation: KgcEvaluationResult,
    ) -> None:
        query = """
        MERGE (s:Entity {execution_id: $execution_id, name: $subject})
        MERGE (o:Entity {execution_id: $execution_id, name: $object})
        CREATE (s)-[:CLAIM {
            execution_id: $execution_id,
            example_id: $example_id,
            benchmark_id: $benchmark_id,
            question_id: $question_id,
            sub_question_id: $sub_question_id,
            relation: $relation,
            label: $label,
            reason: $reason,
            evidence: $evidence,
            answer_stage: $answer_stage,
            iteration: $iteration,
            source: "answer",
            conflicting_object: $conflicting_object,
            conflicting_fact: $conflicting_fact
        }]->(o)
        """
        conflicting_fact = ""
        if evaluation.conflicting_fact:
            cf = evaluation.conflicting_fact
            conflicting_fact = (
                f"{cf.subject} -- {cf.relation} --> {cf.object}"
            )
        tx.run(
            query,
            subject=evaluation.triple.subject,
            object=evaluation.triple.object,
            relation=evaluation.triple.relation,
            label=evaluation.label.value,
            reason=evaluation.reason,
            evidence=evaluation.evidence,
            execution_id=scope.execution_id,
            example_id=scope.example_id,
            benchmark_id=scope.benchmark_id,
            question_id=scope.question_id,
            sub_question_id=sub_question_id,
            answer_stage=answer_stage,
            iteration=iteration,
            conflicting_object=evaluation.conflicting_object or "",
            conflicting_fact=conflicting_fact,
        )

    @staticmethod
    def _create_claim(
        tx,
        scope: ExecutionScope,
        answer_stage: str,
        result: VerificationResult,
    ) -> None:
        query = """
        MERGE (s:Entity {execution_id: $execution_id, name: $subject})
        MERGE (o:Entity {execution_id: $execution_id, name: $object})
        CREATE (s)-[:CLAIM {
            execution_id: $execution_id,
            example_id: $example_id,
            benchmark_id: $benchmark_id,
            question_id: $question_id,
            relation: $relation,
            label: $label,
            reason: $reason,
            evidence: $evidence,
            answer_stage: $answer_stage,
            source: "answer"
        }]->(o)
        """
        tx.run(
            query,
            subject=result.triple.subject,
            object=result.triple.object,
            relation=result.triple.relation,
            label=result.label.value,
            reason=result.reason,
            evidence=result.evidence,
            execution_id=scope.execution_id,
            example_id=scope.example_id,
            benchmark_id=scope.benchmark_id,
            question_id=scope.question_id,
            answer_stage=answer_stage,
        )


def query_claims_if_enabled(
    *,
    execution_id: str | None = None,
    example_id: str | None = None,
    limit: int = 200,
    bad_only: bool = False,
) -> tuple[bool, list[dict[str, object]], str | None]:
    """Query stored claims when NEO4J_ENABLED is set; return (enabled, claims, error)."""
    if not NEO4J_ENABLED:
        return False, [], "Neo4j storage is disabled (set NEO4J_ENABLED=true)"

    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        if bad_only:
            if not execution_id:
                return True, [], "bad-claim queries require an execution_id"
            claims = store.get_bad_claims(execution_id, limit=limit)
        elif execution_id:
            claims = store.get_claims(execution_id, limit=limit)
        elif example_id:
            claims = store.get_claims_for_example(example_id, limit=limit)
        else:
            return True, [], "claim queries require an execution_id or example_id"
        return True, claims, None
    except Exception as exc:
        return True, [], f"Neo4j query failed: {exc}"
    finally:
        if store is not None:
            store.close()


def query_execution_summary_if_enabled(
    execution_id: str,
) -> tuple[bool, dict[str, object] | None, str | None]:
    """Execution-scoped entity/FACT/CLAIM summary when NEO4J_ENABLED is set."""
    if not NEO4J_ENABLED:
        return False, None, "Neo4j storage is disabled (set NEO4J_ENABLED=true)"
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        return True, store.get_execution_summary(execution_id), None
    except Exception as exc:
        return True, None, f"Neo4j query failed: {exc}"
    finally:
        if store is not None:
            store.close()


def neo4j_status(*, required_for_this_route: bool = False) -> dict[str, object]:
    """Distinguish configuration from live Bolt connectivity."""
    status: dict[str, object] = {
        "configured": bool(NEO4J_ENABLED),
        "connected": False,
        "required_for_this_route": bool(required_for_this_route),
        "uri": NEO4J_URI,
        "user": NEO4J_USER,
        "database": NEO4J_DATABASE,
        "error": None,
    }
    if not NEO4J_ENABLED:
        status["error"] = "Neo4j storage is disabled (set NEO4J_ENABLED=true)"
        return status
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.verify_connectivity()
        # Cheap authenticated round-trip beyond TCP.
        with store._session() as session:
            session.run("RETURN 1 AS ok").single()
        status["connected"] = True
    except Exception as exc:
        status["error"] = str(exc)
    finally:
        if store is not None:
            store.close()
    return status


def clear_execution_if_enabled(
    execution_id: str,
    *,
    required: bool = False,
) -> bool:
    """Delete one execution's graph state; never touches other executions."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError(
                "Neo4j execution clear was requested but NEO4J_ENABLED is false."
            )
        return False
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.clear_execution(execution_id)
        return True
    except Exception:
        if required:
            raise
        return False
    finally:
        if store is not None:
            store.close()


def reset_neo4j_dev_if_enabled(*, required: bool = False) -> bool:
    """Explicit full development reset: deletes every execution in the graph."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError(
                "Neo4j full reset was requested but NEO4J_ENABLED is false."
            )
        return False
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.clear_all()
        return True
    except Exception:
        if required:
            raise
        return False
    finally:
        if store is not None:
            store.close()


def store_kgc_facts_if_enabled(
    scope: ExecutionScope,
    facts: list[KgcFact],
    *,
    required: bool = False,
) -> bool:
    """Persist execution-scoped KGc FACT edges when NEO4J_ENABLED is set."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError("Neo4j FACT persistence requires NEO4J_ENABLED=true.")
        return False
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.store_kgc_facts(scope, facts)
        return True
    except Exception as exc:
        if required:
            raise
        print(f"Warning: Neo4j KGc fact storage failed: {exc}", file=sys.stderr)
        return False
    finally:
        if store is not None:
            store.close()


def read_kgc_facts_if_enabled(
    execution_id: str,
    *,
    required: bool = False,
) -> list[KgcFact] | None:
    """Read execution-scoped FACT edges back as the comparator's KGc input."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError("Neo4j FACT readback requires NEO4J_ENABLED=true.")
        return None
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        return store.get_kgc_facts(execution_id)
    except Exception as exc:
        if required:
            raise
        print(f"Warning: Neo4j KGc fact readback failed: {exc}", file=sys.stderr)
        return None
    finally:
        if store is not None:
            store.close()


def query_relationship_counts_if_enabled(
    execution_id: str,
    *,
    required: bool = False,
) -> dict[str, int] | None:
    """Read actual execution-scoped FACT/CLAIM counts for reporting."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError("Neo4j relationship counts require NEO4J_ENABLED=true.")
        return None
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        return store.get_relationship_counts(execution_id)
    except Exception as exc:
        if required:
            raise
        print(f"Warning: Neo4j relationship count query failed: {exc}", file=sys.stderr)
        return None
    finally:
        if store is not None:
            store.close()


def store_working_kgc_additions_if_enabled(
    scope: ExecutionScope,
    additions: list[WorkingKgcAddition],
    *,
    required: bool = False,
) -> bool:
    """Persist focused/derived trusted facts with explicit provenance."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError("Neo4j working KGc persistence requires NEO4J_ENABLED=true.")
        return False
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.store_working_kgc_additions(scope, additions)
        return True
    except Exception as exc:
        if required:
            raise
        print(f"Warning: Neo4j working KGc storage failed: {exc}", file=sys.stderr)
        return False
    finally:
        if store is not None:
            store.close()


def store_kgc_claims_if_enabled(
    scope: ExecutionScope,
    iteration: int,
    evaluations: list[KgcEvaluationResult],
    answer_stage: str | None = None,
    sub_question_id: int | None = None,
    *,
    required: bool = False,
) -> bool:
    """Persist KGc-evaluated CLAIM edges when NEO4J_ENABLED is set."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError("Neo4j CLAIM persistence requires NEO4J_ENABLED=true.")
        return False
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.store_kgc_claims(
            scope,
            iteration,
            evaluations,
            answer_stage=answer_stage,
            sub_question_id=sub_question_id,
        )
        return True
    except Exception as exc:
        if required:
            raise
        print(f"Warning: Neo4j KGc claim storage failed: {exc}", file=sys.stderr)
        return False
    finally:
        if store is not None:
            store.close()


def store_verified_triples_if_enabled(
    scope: ExecutionScope,
    answer_stage: str,
    verification_results: list[VerificationResult],
) -> None:
    """Persist triples when NEO4J_ENABLED is set; warn and continue on failure."""
    if not NEO4J_ENABLED:
        return

    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.store_verified_triples(scope, answer_stage, verification_results)
    except Exception as exc:
        print(f"Warning: Neo4j storage failed: {exc}", file=sys.stderr)
    finally:
        if store is not None:
            store.close()
