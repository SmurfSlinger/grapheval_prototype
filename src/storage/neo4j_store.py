"""Persist verified triples to Neo4j after pipeline verification."""

from __future__ import annotations

import sys

from src.config import NEO4J_ENABLED, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER
from src.models import KgcEvaluationResult, KgcFact, VerificationResult


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
            for fact in facts:
                session.execute_write(self._create_fact, example_id, fact)

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
    def _create_fact(tx, example_id: str, fact: KgcFact) -> None:
        query = """
        MERGE (s:Entity {name: $subject})
        MERGE (o:Entity {name: $object})
        CREATE (s)-[:FACT {
            relation: $relation,
            evidence: $evidence,
            example_id: $example_id,
            source: "context"
        }]->(o)
        """
        tx.run(
            query,
            subject=fact.subject,
            object=fact.object,
            relation=fact.relation,
            evidence=fact.evidence or "",
            example_id=example_id,
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


def store_kgc_facts_if_enabled(example_id: str, facts: list[KgcFact]) -> None:
    """Persist KGc FACT edges when NEO4J_ENABLED is set."""
    if not NEO4J_ENABLED:
        return
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.store_kgc_facts(example_id, facts)
    except Exception as exc:
        print(f"Warning: Neo4j KGc fact storage failed: {exc}", file=sys.stderr)
    finally:
        if store is not None:
            store.close()


def store_kgc_claims_if_enabled(
    example_id: str,
    iteration: int,
    evaluations: list[KgcEvaluationResult],
    answer_stage: str | None = None,
) -> None:
    """Persist KGc-evaluated CLAIM edges when NEO4J_ENABLED is set."""
    if not NEO4J_ENABLED:
        return
    store: Neo4jStore | None = None
    try:
        store = Neo4jStore()
        store.store_kgc_claims(
            example_id, iteration, evaluations, answer_stage=answer_stage
        )
    except Exception as exc:
        print(f"Warning: Neo4j KGc claim storage failed: {exc}", file=sys.stderr)
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
