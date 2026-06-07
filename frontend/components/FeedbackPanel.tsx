import type { FeedbackItem } from "@/lib/api";

interface FeedbackPanelProps {
  feedback: FeedbackItem[];
}

export default function FeedbackPanel({ feedback }: FeedbackPanelProps) {
  if (feedback.length === 0) {
    return (
      <p className="loading">No revision feedback — all triples were supported.</p>
    );
  }

  return (
    <ul className="feedback-list">
      {feedback.map((item, index) => (
        <li
          key={`${item.triple.subject}-${item.triple.relation}-${index}`}
          className={`feedback-item${item.status === "NOT_ENOUGH_INFO" ? " nei" : ""}`}
        >
          <div>
            <span
              className={
                item.status === "NOT_ENOUGH_INFO"
                  ? "badge nei"
                  : "badge contradicted"
              }
            >
              {item.status}
            </span>
          </div>
          <div>
            <strong>Triple:</strong> ({item.triple.subject},{" "}
            {item.triple.relation}, {item.triple.object})
          </div>
          <div>
            <strong>Instruction:</strong> {item.instruction}
          </div>
          <div>
            <strong>Evidence:</strong> {item.evidence}
          </div>
        </li>
      ))}
    </ul>
  );
}
