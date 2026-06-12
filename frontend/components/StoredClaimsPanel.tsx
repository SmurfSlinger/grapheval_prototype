"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import {
  fetchGraphClaims,
  type StoredClaim,
  type VerificationLabel,
} from "@/lib/api";

function badgeClass(label: string): string {
  if (label === "SUPPORTED") return "badge supported";
  if (label === "CONTRADICTED") return "badge contradicted";
  if (label === "NOT_ENOUGH_INFO") return "badge nei";
  return "badge pending";
}

function dedupeClaims(claims: StoredClaim[]): StoredClaim[] {
  const byKey = new Map<string, StoredClaim>();
  for (const claim of claims) {
    const key = `${claim.subject}|${claim.relation}|${claim.object}|${claim.answer_stage}`;
    byKey.set(key, claim);
  }
  return Array.from(byKey.values());
}

interface StoredClaimsPanelProps {
  selectedExampleId: string;
  onRefresh?: () => void;
}

export default function StoredClaimsPanel({
  selectedExampleId,
  onRefresh,
}: StoredClaimsPanelProps) {
  const [claims, setClaims] = useState<StoredClaim[]>([]);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  const loadClaims = useCallback(async () => {
    if (!selectedExampleId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetchGraphClaims({
        limit: 50,
        exampleId: selectedExampleId,
      });
      setEnabled(response.enabled);
      setClaims(dedupeClaims(response.claims));
      if (response.error) {
        setError(response.error);
      }
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load claims");
      setClaims([]);
    } finally {
      setLoading(false);
    }
  }, [selectedExampleId, onRefresh]);

  useEffect(() => {
    loadClaims();
  }, [loadClaims]);

  return (
    <section className="card story-section">
      <div className="section-header">
        <h2>Stored in Neo4j</h2>
        <button
          type="button"
          className="secondary"
          onClick={loadClaims}
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      <p className="section-lead">
        Neo4j stores each checked claim as an Entity → CLAIM → Entity relationship.
        The semantic relation, verification label, reason, evidence, example ID, and
        answer stage are stored as relationship properties.
      </p>

      {enabled === false && (
        <p className="muted-text">
          Neo4j storage is disabled. Set <code>NEO4J_ENABLED=true</code> and run an
          example to store claims.
        </p>
      )}

      {error && <div className="error inline">{error}</div>}

      {!loading && enabled && claims.length === 0 && !error && (
        <p className="loading">
          No stored claims for this example yet. Run it with Neo4j enabled.
        </p>
      )}

      {claims.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Subject</th>
                <th>Relation</th>
                <th>Object</th>
                <th>Label</th>
                <th>Stage</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => {
                const rowKey = `${claim.subject}|${claim.relation}|${claim.object}|${claim.answer_stage}`;
                const isExpanded = expandedKey === rowKey;
                return (
                  <Fragment key={rowKey}>
                    <tr>
                      <td>{claim.subject}</td>
                      <td>{claim.relation}</td>
                      <td>{claim.object}</td>
                      <td>
                        <span className={badgeClass(claim.label as VerificationLabel)}>
                          {claim.label}
                        </span>
                      </td>
                      <td>{claim.answer_stage}</td>
                      <td>
                        <button
                          type="button"
                          className="btn-link"
                          onClick={() =>
                            setExpandedKey(isExpanded ? null : rowKey)
                          }
                        >
                          {isExpanded ? "Hide" : "Details"}
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="claim-details-row">
                        <td colSpan={6}>
                          <p>
                            <strong>Why:</strong> {claim.reason}
                          </p>
                          <p>
                            <strong>Evidence:</strong> {claim.evidence}
                          </p>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
