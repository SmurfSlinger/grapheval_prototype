import type { ReactNode } from "react";

export function TextPreview({
  text,
  lines = 2,
  className = "",
}: {
  text: string;
  lines?: number;
  className?: string;
}) {
  const clampClass =
    lines === 0
      ? "kgc-text-preview-open"
      : lines === 5
        ? "kgc-text-preview-5"
        : lines === 3
          ? "kgc-text-preview-3"
          : lines === 1
            ? "kgc-text-preview-1"
            : "";
  return (
    <p className={`kgc-text-preview ${clampClass} ${className}`.trim()}>{text}</p>
  );
}

export function RoleLabel({ children }: { children: ReactNode }) {
  return <p className="kgc-role-label">{children}</p>;
}

export function StatChip({
  label,
  variant = "neutral",
}: {
  label: string;
  variant?: "supported" | "contradicted" | "nei" | "neutral" | "revision";
}) {
  return <span className={`kgc-stat-chip kgc-stat-${variant}`}>{label}</span>;
}

export function StatChipRow({ children }: { children: ReactNode }) {
  return <div className="kgc-stat-row">{children}</div>;
}

export function ExpandableDetails({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <details className="kgc-expand-details">
      <summary>{label}</summary>
      <div className="kgc-expand-body">{children}</div>
    </details>
  );
}

export function DetailSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="kgc-detail-section">
      <h4 className="kgc-detail-section-title">{title}</h4>
      <div className="kgc-detail-section-body">{children}</div>
    </section>
  );
}

export function StageCard({
  step,
  title,
  summary,
  note,
  resultLabel,
  result,
  detailsLabel,
  details,
  variant = "default",
}: {
  step?: number;
  title: string;
  summary: string;
  note?: string;
  resultLabel?: string;
  result: ReactNode;
  detailsLabel: string;
  details: ReactNode;
  variant?: "baseline" | "loop" | "final" | "default";
}) {
  return (
    <article className={`kgc-stage-card kgc-stage-${variant}`}>
      <header className="kgc-stage-header">
        {step != null ? <span className="kgc-stage-num">{step}</span> : null}
        <div className="kgc-stage-heading">
          <h3 className="kgc-stage-title">{title}</h3>
          {summary ? <p className="kgc-stage-summary">{summary}</p> : null}
        </div>
      </header>
      <div className="kgc-stage-result">
        {resultLabel ? <RoleLabel>{resultLabel}</RoleLabel> : null}
        {result}
      </div>
      {note ? <p className="kgc-stage-note">{note}</p> : null}
      <ExpandableDetails label={detailsLabel}>{details}</ExpandableDetails>
    </article>
  );
}

export function CompactTripleList({ triples }: { triples: string[] }) {
  if (triples.length === 0) return null;
  return (
    <ul className="kgc-compact-triple-list">
      {triples.map((line, index) => (
        <li key={index} className="mono-line">
          {line}
        </li>
      ))}
    </ul>
  );
}
