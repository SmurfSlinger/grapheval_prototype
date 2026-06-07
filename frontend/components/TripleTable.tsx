import type { PipelineResult, VerificationLabel } from "@/lib/api";

function badgeClass(label: VerificationLabel | null): string {
  if (label === "SUPPORTED") return "badge supported";
  if (label === "CONTRADICTED") return "badge contradicted";
  if (label === "NOT_ENOUGH_INFO") return "badge nei";
  return "badge pending";
}

function tripleKey(triple: {
  subject: string;
  relation: string;
  object: string;
}): string {
  return `${triple.subject}|${triple.relation}|${triple.object}`;
}

interface TripleTableProps {
  result: PipelineResult;
}

export default function TripleTable({ result }: TripleTableProps) {
  const verificationByTriple = new Map(
    result.verification_results.map((vr) => [tripleKey(vr.triple), vr]),
  );

  if (result.extracted_triples.length === 0) {
    return <p className="loading">No triples extracted.</p>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table>
        <thead>
          <tr>
            <th>Subject</th>
            <th>Relation</th>
            <th>Object</th>
            <th>Source sentence</th>
            <th>Label</th>
            <th>Evidence / reason</th>
          </tr>
        </thead>
        <tbody>
          {result.extracted_triples.map((triple, index) => {
            const vr = verificationByTriple.get(tripleKey(triple));
            const label = vr?.label ?? null;
            return (
              <tr key={`${tripleKey(triple)}-${index}`}>
                <td>{triple.subject}</td>
                <td>{triple.relation}</td>
                <td>{triple.object}</td>
                <td>{triple.source_sentence ?? "—"}</td>
                <td>
                  <span className={badgeClass(label)}>
                    {label ?? "—"}
                  </span>
                </td>
                <td>
                  {vr ? (
                    <>
                      <div>
                        <strong>Evidence:</strong> {vr.evidence}
                      </div>
                      <div>
                        <strong>Reason:</strong> {vr.reason}
                      </div>
                    </>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
