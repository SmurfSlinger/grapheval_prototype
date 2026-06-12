import type { PipelineResult, VerificationLabel } from "@/lib/api";

function badgeClass(label: VerificationLabel): string {
  if (label === "CONTRADICTED") return "badge contradicted";
  return "badge nei";
}

function formatClaim(triple: {
  subject: string;
  relation: string;
  object: string;
}): string {
  return `${triple.subject} — ${triple.relation} → ${triple.object}`;
}

interface FlaggedTriplesProps {
  result: PipelineResult;
}

export default function FlaggedTriples({ result }: FlaggedTriplesProps) {
  const flagged = result.verification_results.filter(
    (vr) => vr.label !== "SUPPORTED",
  );

  if (flagged.length === 0) {
    return (
      <p className="muted-text">
        No flagged claims — all extracted claims were supported by the context.
      </p>
    );
  }

  return (
    <ul className="flagged-list">
      {flagged.map((vr, index) => (
        <li key={`${vr.triple.subject}-${vr.triple.relation}-${index}`} className="flagged-card">
          <div className="flagged-header">
            <span className={badgeClass(vr.label)}>{vr.label}</span>
            <span className="flagged-claim">{formatClaim(vr.triple)}</span>
          </div>
          <p>
            <strong>Why:</strong> {vr.reason}
          </p>
          <p>
            <strong>Evidence:</strong> {vr.evidence}
          </p>
        </li>
      ))}
    </ul>
  );
}
