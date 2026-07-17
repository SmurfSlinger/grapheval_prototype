"""Persist verified triples to Neo4j after pipeline verification."""

from __future__ import annotations

import sys

from src.config import NEO4J_ENABLED, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from src.models import (
    KgcEvaluationResult,
    KgcFact,
    VerificationResult,
    WorkingKgcAddition,
)


class Neo4jStore:
    """Store verified triples as Entity nodes linked by CLAIM relationships."""

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
    ) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def clear_all(self) -> None:
        """Delete every node and relationship in the configured local database."""
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n").consume()

    _CLAIM_FIELDS = """
        s.name AS subject,
        c.relation AS relation,
        o.name AS object,
        c.label AS label,
        c.reason AS reason,
        c.evidence AS evidence,
        c.example_id AS example_id,
        c.answer_stage AS answer_stage
    """

    def get_claims(self, limit: int = 50) -> list[dict[str, str]]:
        query = f"""
        MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
        RETURN {self._CLAIM_FIELDS}
        LIMIT $limit
        """
        with self._driver.session() as session:
            result = session.run(query, limit=limit)
            return [dict(record) for record in result]

    def get_claims_for_example(self, example_id: str, limit: int = 50) -> list[dict[str, str]]:
        query = f"""
        MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
        WHERE c.example_id = $example_id
        RETURN {self._CLAIM_FIELDS}
        LIMIT $limit
        """
        with self._driver.session() as session:
            result = session.run(query, example_id=example_id, limit=limit)
            return [dict(record) for record in result]

    def get_bad_claims(self, limit: int = 50) -> list[dict[str, str]]:
        query = f"""
        MATCH (s:Entity)-[c:CLAIM]->(o:Entity)
        WHERE c.label IN ['CONTRADICTED', 'NOT_ENOUGH_INFO']
        RETURN {self._CLAIM_FIELDS}
        LIMIT $limit
        """
        with self._driver.session() as session:
            result = session.run(query, limit=limit)
            return [dict(record) for record in result]

    def store_kgc_facts(self, example_id: str, facts: list[KgcFact]) -> None:
        if not facts:
            return
        with self._driver.session() as session:
            for created_order, fact in enumerate(facts):
                session.execute_write(
                    self._create_fact,
                    example_id,
                    fact,
                    created_order,
                )

    def get_kgc_facts(self, example_id: str) -> list[KgcFact]:
        """Reconstruct scoped trusted FACT relationships for one run."""
        query = """
        MATCH (s:Entity)-[f:FACT]->(o:Entity)
        WHERE f.example_id = $example_id
        RETURN s.name AS subject, f.relation AS relation, o.name AS object,
               f.evidence AS evidence
        ORDER BY f.created_order, subject, relation, object
        """
        with self._driver.session() as session:
            result = session.run(query, example_id=example_id)
            return [
                KgcFact(
                    subject=record["subject"],
                    relation=record["relation"],
                    object=record["object"],
                    evidence=record["evidence"] or None,
                )
                for record in result
            ]

    def get_relationship_counts(self, example_id: str) -> dict[str, int]:
        """Return actual scoped FACT and CLAIM relationship counts."""
        with self._driver.session() as session:
            fact_record = session.run(
                """
                MATCH ()-[r:FACT]->()
                WHERE r.example_id = $example_id
                RETURN count(r) AS count
                """,
                example_id=example_id,
            ).single()
            claim_record = session.run(
                """
                MATCH ()-[r:CLAIM]->()
                WHERE r.example_id = $example_id
                RETURN count(r) AS count
                """,
                example_id=example_id,
            ).single()
        return {
            "fact_edges": int(fact_record["count"]) if fact_record else 0,
            "claim_edges": int(claim_record["count"]) if claim_record else 0,
        }

    def store_working_kgc_additions(
        self,
        example_id: str,
        additions: list[WorkingKgcAddition],
    ) -> None:
        if not additions:
            return
        with self._driver.session() as session:
            for addition in additions:
                session.execute_write(
                    self._create_working_fact,
                    example_id,
                    addition,
                )

    def store_kgc_claims(
        self,
        example_id: str,
        iteration: int,
        evaluations: list[KgcEvaluationResult],
        answer_stage: str | None = None,
    ) -> None:
        if not evaluations:
            return
        stage = answer_stage if answer_stage else f"answer_{iteration}"
        with self._driver.session() as session:
            for evaluation in evaluations:
                session.execute_write(
                    self._create_kgc_claim,
                    example_id,
                    iteration,
                    stage,
                    evaluation,
                )

    def store_verified_triples(
        self,
        example_id: str,
        answer_stage: str,
        verification_results: list[VerificationResult],
    ) -> None:
        if not verification_results:
            return

        with self._driver.session() as session:
            for result in verification_results:
                session.execute_write(
                    self._create_claim,
                    example_id,
                    answer_stage,
                    result,
                )

    @staticmethod
    def _create_fact(
        tx,
        example_id: str,
        fact: KgcFact,
        created_order: int,
    ) -> None:
        query = """
        MERGE (s:Entity {name: $subject})
        MERGE (o:Entity {name: $object})
        MERGE (s)-[f:FACT {
            relation: $relation,
            example_id: $example_id,
            provenance: "trusted_context",
            extraction_stage: "context_triple_extraction"
        }]->(o)
        SET f.evidence = $evidence,
            f.source = "trusted_context",
            f.created_order = $created_order
        """
        tx.run(
            query,
            subject=fact.subject,
            object=fact.object,
            relation=fact.relation,
            evidence=fact.evidence or "",
            example_id=example_id,
            created_order=created_order,
        )

    @staticmethod
    def _create_working_fact(
        tx,
        example_id: str,
        addition: WorkingKgcAddition,
    ) -> None:
        fact = addition.fact
        provenance = addition.provenance.value
        query = """
        MERGE (s:Entity {name: $subject})
        MERGE (o:Entity {name: $object})
        MERGE (s)-[f:FACT {
            relation: $relation,
            example_id: $example_id,
            provenance: $provenance,
            extraction_stage: $extraction_stage,
            sub_question_id: $sub_question_id
        }]->(o)
        SET f.evidence = $evidence,
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
            example_id=example_id,
            provenance=provenance,
            extraction_stage=addition.extraction_scope,
            sub_question_id=addition.sub_question_id,
            derivation_type=addition.derivation_type or "",
            evidence_spans=addition.evidence_spans,
            derivation_explanation=addition.derivation_explanation or "",
            created_order=addition.sub_question_id or 0,
        )

    @staticmethod
    def _create_kgc_claim(
        tx,
        example_id: str,
        iteration: int,
        answer_stage: str,
        evaluation: KgcEvaluationResult,
    ) -> None:
        query = """
        MERGE (s:Entity {name: $subject})
        MERGE (o:Entity {name: $object})
        CREATE (s)-[:CLAIM {
            relation: $relation,
            label: $label,
            reason: $reason,
            evidence: $evidence,
            example_id: $example_id,
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
            example_id=example_id,
            answer_stage=answer_stage,
            iteration=iteration,
            conflicting_object=evaluation.conflicting_object or "",
            conflicting_fact=conflicting_fact,
        )

    @staticmethod
    def _create_claim(
        tx,
        example_id: str,
        answer_stage: str,
        result: VerificationResult,
    ) -> None:
        query = """
        MERGE (s:Entity {name: $subject})
        MERGE (o:Entity {name: $object})
        CREATE (s)-[:CLAIM {
            relation: $relation,
            label: $label,
            reason: $reason,
            evidence: $evidence,
            example_id: $example_id,
            answer_stage: $answer_stage
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
            example_id=example_id,
            answer_stage=answer_stage,
        )


def query_claims_if_enabled(
    *,
    example_id: str | None = None,
    limit: int = 50,
    bad_only: bool = False,
) -> tuple[bool, list[dict[str, str]], str | None]:
    """Query stored claims when NEO4J_ENABLED is set; return (enabled, claims, error)."""
    if not NEO4J_ENABLED:
        return False, [], "Neo4j storage is disabled (set NEO4J_ENABLED=true)"

    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        if bad_only:
            claims = store.get_bad_claims(limit=limit)
        elif example_id:
            claims = store.get_claims_for_example(example_id, limit=limit)
        else:
            claims = store.get_claims(limit=limit)
        return True, claims, None
    except Exception as exc:
        return True, [], f"Neo4j query failed: {exc}"
    finally:
        if store is not None:
            store.close()


def clear_neo4j_if_enabled(*, required: bool = False) -> bool:
    """Clear the configured graph, or fail when an explicitly requested clear cannot run."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError(
                "Neo4j clear was requested but NEO4J_ENABLED is false."
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
    example_id: str,
    facts: list[KgcFact],
    *,
    required: bool = False,
) -> bool:
    """Persist KGc FACT edges when NEO4J_ENABLED is set."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError("Neo4j FACT persistence requires NEO4J_ENABLED=true.")
        return False
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.store_kgc_facts(example_id, facts)
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
    example_id: str,
    *,
    required: bool = False,
) -> list[KgcFact] | None:
    """Read scoped FACT edges back as the comparator's working KGc input."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError("Neo4j FACT readback requires NEO4J_ENABLED=true.")
        return None
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        return store.get_kgc_facts(example_id)
    except Exception as exc:
        if required:
            raise
        print(f"Warning: Neo4j KGc fact readback failed: {exc}", file=sys.stderr)
        return None
    finally:
        if store is not None:
            store.close()


def query_relationship_counts_if_enabled(
    example_id: str,
    *,
    required: bool = False,
) -> dict[str, int] | None:
    """Read actual scoped FACT/CLAIM counts for reporting."""
    if not NEO4J_ENABLED:
        if required:
            raise RuntimeError("Neo4j relationship counts require NEO4J_ENABLED=true.")
        return None
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        return store.get_relationship_counts(example_id)
    except Exception as exc:
        if required:
            raise
        print(f"Warning: Neo4j relationship count query failed: {exc}", file=sys.stderr)
        return None
    finally:
        if store is not None:
            store.close()


def store_working_kgc_additions_if_enabled(
    example_id: str,
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
        store.store_working_kgc_additions(example_id, additions)
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
    example_id: str,
    iteration: int,
    evaluations: list[KgcEvaluationResult],
    answer_stage: str | None = None,
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
            example_id, iteration, evaluations, answer_stage=answer_stage
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
    example_id: str,
    answer_stage: str,
    verification_results: list[VerificationResult],
) -> None:
    """Persist triples when NEO4J_ENABLED is set; warn and continue on failure."""
    if not NEO4J_ENABLED:
        return

    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.store_verified_triples(example_id, answer_stage, verification_results)
    except Exception as exc:
        print(f"Warning: Neo4j storage failed: {exc}", file=sys.stderr)
    finally:
        if store is not None:
            store.close()
