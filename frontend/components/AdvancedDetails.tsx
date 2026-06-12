"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import type { PipelineResult, StoredClaim } from "@/lib/api";
import { fetchGraphClaims } from "@/lib/api";
import FeedbackPanel from "./FeedbackPanel";
import ResultsList from "./ResultsList";
import TripleTable from "./TripleTable";

interface AdvancedDetailsProps {
  result: PipelineResult;
  allResults: PipelineResult[];
  selectedId: string | null;
  onSelectResult: (id: string) => void;
}

function dedupeClaims(claims: StoredClaim[]): StoredClaim[] {
  const byKey = new Map<string, StoredClaim>();
  for (const claim of claims) {
    const key = `${claim.subject}|${claim.relation}|${claim.object}|${claim.answer_stage}`;
    byKey.set(key, claim);
  }
  return Array.from(byKey.values());
}

export default function AdvancedDetails({
  result,
  allResults,
  selectedId,
  onSelectResult,
}: AdvancedDetailsProps) {
  const [showJson, setShowJson] = useState(false);
  const [neo4jClaims, setNeo4jClaims] = useState<StoredClaim[]>([]);
  const graphRevisedTriples = result.graph_revised_triples ?? [];
  const graphRevisedVerification = result.graph_revised_verification_results ?? [];

  const loadNeo4jClaims = useCallback(async () => {
    try {
      const response = await fetchGraphClaims({
        limit: 50,
        exampleId: result.example_id,
      });
      setNeo4jClaims(dedupeClaims(response.claims));
    } catch {
      setNeo4jClaims([]);
    }
  }, [result.example_id]);

  useEffect(() => {
    loadNeo4jClaims();
  }, [loadNeo4jClaims]);

  return (
    <details className="card details-card">
      <summary>Advanced details</summary>
      <div className="details-body">
        {allResults.length > 1 && (
          <>
            <h4>Run-all summary</h4>
            <ResultsList
              results={allResults}
              selectedId={selectedId}
              onSelect={onSelectResult}
            />
          </>
        )}

        <h4>All extracted triples</h4>
        <TripleTable
          triples={result.extracted_triples}
          verificationResults={result.verification_results}
        />

        <h4>Graph-feedback items</h4>
        <FeedbackPanel feedback={result.feedback} />

        {graphRevisedTriples.length > 0 && (
          <>
            <h4>Triples after graph-feedback revision</h4>
            <TripleTable
              triples={graphRevisedTriples}
              verificationResults={graphRevisedVerification}
            />
          </>
        )}

        {neo4jClaims.length > 0 && (
          <>
            <h4>Raw Neo4j claims (with reason and evidence)</h4>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>Relation</th>
                    <th>Object</th>
                    <th>Label</th>
                    <th>Stage</th>
                    <th>Reason</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {neo4jClaims.map((claim, index) => (
                    <tr key={`${claim.answer_stage}-${index}`}>
                      <td>{claim.subject}</td>
                      <td>{claim.relation}</td>
                      <td>{claim.object}</td>
                      <td>{claim.label}</td>
                      <td>{claim.answer_stage}</td>
                      <td>{claim.reason}</td>
                      <td>{claim.evidence}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        <h4>Full pipeline JSON</h4>
        <button
          type="button"
          className="secondary"
          onClick={() => setShowJson((value) => !value)}
        >
          {showJson ? "Hide JSON" : "Show JSON"}
        </button>
        {showJson && (
          <pre className="json-block">{JSON.stringify(result, null, 2)}</pre>
        )}
      </div>
    </details>
  );
}
