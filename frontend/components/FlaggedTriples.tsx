import type { FeedbackItem, PipelineResult, VerificationLabel } from "@/lib/api";

function tripleKey(triple: {
  subject: string;
  relation: string;
  object: string;
}): string {
  return `${triple.subject}|${triple.relation}|${triple.object}`;
}

function badgeClass(label: VerificationLabel): string {
  if (label === "CONTRADICTED") return "badge contradicted";
  return "badge nei";
}

interface FlaggedTriplesProps {
  result: PipelineResult;
}

export default function FlaggedTriples({ result }: FlaggedTriplesProps) {
  const feedbackByTriple = new Map(
    (result.feedback ?? []).map((fb) => [tripleKey(fb.triple), fb]),
  );

  const flagged = result.verification_results.filter(
    (vr) => vr.label !== "SUPPORTED",
  );

  if (flagged.length === 0) {
    return (
      <p className="muted-text">No flagged triples — all claims were supported.</p>
    );
  }

  return (
    <ul className="flagged-list">
      {flagged.map((vr, index) => {
        const fb: FeedbackItem | undefined = feedbackByTriple.get(
          tripleKey(vr.triple),
        );
        return (
          <li key={`${tripleKey(vr.triple)}-${index}`} className="flagged-card">
            <div className="flagged-header">
              <span className={badgeClass(vr.label)}>{vr.label}</span>
              <span className="flagged-triple">
                ({vr.triple.subject}, {vr.triple.relation}, {vr.triple.object})
              </span>
            </div>
            <p>
              <strong>Evidence:</strong> {vr.evidence}
            </p>
            <p>
              <strong>Reason:</strong> {vr.reason}
            </p>
            {fb && (
              <p>
                <strong>Feedback:</strong> {fb.instruction}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
