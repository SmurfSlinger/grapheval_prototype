import type {
  BacktrackingFeedbackItem,
  BacktrackingResult,
  KgcEvaluatedClaim,
  KgcFact,
  KgcClaimLabel,
} from "@/lib/api";
import {
  buildChangedClaims,
  buildClaimCheckLines,
  buildFeedbackLines,
  contextNeedsExpand,
  contextPreview,
  factCountShort,
  formatFactLine,
  hasDemoIssues,
} from "@/components/kgc/demoSummary";
import {
  DetailSection,
  ExpandableDetails,
  StageCard,
  StatChip,
  StatChipRow,
  TextPreview,
} from "@/components/kgc/StageCard";

function badgeClass(label: KgcClaimLabel): string {
  if (label === "SUPPORTED") return "badge supported";
  if (label === "CONTRADICTED") return "badge contradicted";
  return "badge nei";
}

function labelText(label: KgcClaimLabel): string {
  if (label === "SUPPORTED") return "Supported";
  if (label === "CONTRADICTED") return "Contradicted";
  return "No evidence";
}

function actionText(label: KgcClaimLabel): string {
  if (label === "SUPPORTED") return "Keep";
  if (label === "CONTRADICTED") return "Fix using KGc";
  return "Remove or defer";
}

function normalizeText(text: string): string {
  return text.trim().replace(/\s+/g, " ");
}

function answersMatch(a: string, b: string): boolean {
  return normalizeText(a) === normalizeText(b);
}

function GroupedList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="kgc-grouped-list">
      <p className="kgc-grouped-list-title">{title}</p>
      <ul className="kgc-story-list">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function RunInputsCard({ result }: { result: BacktrackingResult }) {
  const preview = contextPreview(result.context);
  const showExpand = contextNeedsExpand(result.context);

  return (
    <section className="kgc-run-inputs-card">
      <h3 className="kgc-section-title">Run inputs</h3>
      <div className="kgc-input-field">
        <p className="kgc-input-label">Question</p>
        <p className="kgc-input-value">{result.question}</p>
      </div>
      <div className="kgc-input-field">
        <p className="kgc-input-label">Trusted context</p>
        <p className="kgc-input-value">{preview}</p>
        {showExpand ? (
          <ExpandableDetails label="Show full context">
            <p className="kgc-input-value">{result.context}</p>
          </ExpandableDetails>
        ) : null}
      </div>
      <div className="kgc-input-field">
        <p className="kgc-input-label">Answer(0)</p>
        <p className="kgc-input-sublabel">External LLM answer being checked</p>
        <p className="kgc-input-value">{result.answer_0}</p>
      </div>
    </section>
  );
}

function CorrectionSummaryCard({ result }: { result: BacktrackingResult }) {
  const revision = result.revision_effect;
  const kept = revision?.preserved_supported_count ?? result.supported_count;
  const fixed = revision?.corrected_contradicted_count ?? result.contradicted_count;
  const removed =
    revision?.removed_or_deferred_no_evidence_count ?? result.no_evidence_count;
  const changedClaims = buildChangedClaims(result.evaluated_claims);

  const headline = hasDemoIssues(result)
    ? "KGc corrected the flawed starting answer."
    : "All checked claims were supported by KGc.";

  return (
    <section className="kgc-summary-card">
      <h3 className="kgc-section-title">{headline}</h3>
      <StatChipRow>
        <StatChip label={`${kept} kept`} variant="supported" />
        <StatChip label={`${fixed} fixed`} variant="contradicted" />
        <StatChip label={`${removed} removed/deferred`} variant="nei" />
      </StatChipRow>
      {changedClaims.length > 0 ? (
        <div className="kgc-changed-claims">
          <p className="kgc-grouped-list-title">Changed claims</p>
          <ul className="kgc-story-list">
            {changedClaims.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function KgcFactsTable({ facts }: { facts: KgcFact[] }) {
  if (facts.length === 0) {
    return <p className="kgc-empty-note">No KGc facts extracted.</p>;
  }

  return (
    <div className="kgc-table-wrap">
      <table className="kgc-table">
        <thead>
          <tr>
            <th>Subject</th>
            <th>Relation</th>
            <th>Object</th>
          </tr>
        </thead>
        <tbody>
          {facts.map((fact, index) => (
            <tr key={index}>
              <td>{fact.subject}</td>
              <td className="mono-cell">{fact.relation}</td>
              <td>{fact.object}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClaimCheckDetailRow({ claim }: { claim: KgcEvaluatedClaim }) {
  const answerClaim = claim.original_claim ?? claim.triple;
  const kgcSays =
    claim.label === "SUPPORTED" && claim.matched_kgc_fact
      ? formatFactLine(claim.matched_kgc_fact)
      : claim.label === "CONTRADICTED" && claim.conflicting_fact
        ? formatFactLine(claim.conflicting_fact)
        : "No matching KGc fact";

  return (
    <li className={`kgc-check-detail-row kgc-eval-${claim.label.toLowerCase()}`}>
      <p className="kgc-check-detail-line">
        <span className="kgc-check-detail-key">Answer(0) said</span>
        <span className="kgc-check-detail-value mono-line">
          {formatFactLine(answerClaim)}
        </span>
      </p>
      <p className="kgc-check-detail-line">
        <span className="kgc-check-detail-key">KGc says</span>
        <span className="kgc-check-detail-value">{kgcSays}</span>
      </p>
      <p className="kgc-check-detail-line">
        <span className="kgc-check-detail-key">Result</span>
        <span className="kgc-check-detail-value">
          <span className={badgeClass(claim.label)}>{labelText(claim.label)}</span>
        </span>
      </p>
      <p className="kgc-check-detail-line">
        <span className="kgc-check-detail-key">Why</span>
        <span className="kgc-check-detail-value">{claim.reason}</span>
      </p>
      <p className="kgc-check-detail-line">
        <span className="kgc-check-detail-key">Action</span>
        <span className="kgc-check-detail-value">
          {claim.backtracking_action ?? actionText(claim.label)}
        </span>
      </p>
    </li>
  );
}

function FeedbackDetailRow({ fb }: { fb: BacktrackingFeedbackItem }) {
  return (
    <li className="kgc-feedback-detail-row">
      <p className="kgc-check-detail-line">
        <span className="kgc-check-detail-key">Claim</span>
        <span className="kgc-check-detail-value mono-line">
          {formatFactLine(fb.triple)}
        </span>
      </p>
      <p className="kgc-check-detail-line">
        <span className="kgc-check-detail-key">Instruction</span>
        <span className="kgc-check-detail-value">{fb.instruction}</span>
      </p>
      {fb.conflicting_fact ? (
        <p className="kgc-check-detail-line">
          <span className="kgc-check-detail-key">KGc conflict</span>
          <span className="kgc-check-detail-value">
            {formatFactLine(fb.conflicting_fact)}
          </span>
        </p>
      ) : null}
    </li>
  );
}

interface KgcFlowViewProps {
  result: BacktrackingResult;
}

export default function KgcFlowView({ result }: KgcFlowViewProps) {
  const revision = result.revision_effect;
  const answer1 = result.answer_1 ?? result.answer_n_plus_1;
  const answerUnchanged = answersMatch(result.answer_0, answer1);

  const claimCheck = buildClaimCheckLines(result.evaluated_claims);
  const feedbackLines = buildFeedbackLines(result);
  const factLines = result.kgc_facts.map(formatFactLine);
  const factsHaveEvidence = result.kgc_facts.some((f) => f.evidence?.trim());

  return (
    <div className="kgc-dashboard">
      <RunInputsCard result={result} />
      <CorrectionSummaryCard result={result} />

      {result.answer_0_warning ? (
        <p className="kgc-run-warning">{result.answer_0_warning}</p>
      ) : null}

      <div className="kgc-grid-stages">
        <StageCard
          title="KGc facts"
          summary=""
          result={
            <>
              <p className="kgc-result-highlight">
                {factCountShort(result.kgc_facts.length)}
              </p>
              <ul className="kgc-story-list">
                {factLines.map((line, index) => (
                  <li key={index} className="mono-line">
                    {line}
                  </li>
                ))}
              </ul>
            </>
          }
          detailsLabel="All facts and evidence"
          details={
            <>
              <DetailSection title="Full fact table">
                <KgcFactsTable facts={result.kgc_facts} />
              </DetailSection>
              {factsHaveEvidence ? (
                <DetailSection title="Evidence from context">
                  <ul className="kgc-evidence-list">
                    {result.kgc_facts
                      .filter((f) => f.evidence?.trim())
                      .map((fact, index) => (
                        <li key={index} className="kgc-evidence-item">
                          <span className="mono-line">{formatFactLine(fact)}</span>
                          <span className="kgc-evidence-text">
                            Evidence: {fact.evidence}
                          </span>
                        </li>
                      ))}
                  </ul>
                </DetailSection>
              ) : null}
            </>
          }
        />

        <StageCard
          title="Claim check"
          summary=""
          result={
            <>
              <StatChipRow>
                <StatChip
                  label={`${result.supported_count} Supported`}
                  variant="supported"
                />
                <StatChip
                  label={`${result.contradicted_count} Contradicted`}
                  variant="contradicted"
                />
                <StatChip
                  label={`${result.no_evidence_count} No evidence`}
                  variant="nei"
                />
              </StatChipRow>
              <GroupedList title="Fixed" items={claimCheck.fixed} />
              <GroupedList title="Kept" items={claimCheck.kept} />
              <GroupedList title="Removed/deferred" items={claimCheck.removed} />
            </>
          }
          detailsLabel="Full claim checks"
          details={
            <ul className="kgc-check-detail-list">
              {result.evaluated_claims.map((claim, index) => (
                <ClaimCheckDetailRow key={index} claim={claim} />
              ))}
            </ul>
          }
        />

        <StageCard
          title="Feedback"
          summary=""
          result={
            <>
              <GroupedList title="Keep" items={feedbackLines.keep} />
              <GroupedList title="Fix" items={feedbackLines.fix} />
              <GroupedList title="Remove/defer" items={feedbackLines.remove} />
            </>
          }
          detailsLabel="Full feedback instructions"
          details={
            <ul className="kgc-check-detail-list">
              {result.backtracking_feedback.map((fb, index) => (
                <FeedbackDetailRow key={index} fb={fb} />
              ))}
            </ul>
          }
        />

        <StageCard
          title="Answer(1)"
          summary=""
          note={answerUnchanged ? undefined : "Changed after feedback."}
          variant="final"
          result={
            <>
              <TextPreview text={answer1} lines={0} className="kgc-text-preview-final" />
              {revision ? (
                <StatChipRow>
                  <StatChip
                    label={`Kept ${revision.preserved_supported_count}`}
                    variant="supported"
                  />
                  <StatChip
                    label={`Fixed ${revision.corrected_contradicted_count}`}
                    variant="contradicted"
                  />
                  <StatChip
                    label={`Removed/deferred ${revision.removed_or_deferred_no_evidence_count}`}
                    variant="nei"
                  />
                </StatChipRow>
              ) : null}
            </>
          }
          detailsLabel="Before / after"
          details={
            <div className="kgc-before-after kgc-before-after-block">
              <p>
                <span className="kgc-before-after-label">Before</span>
                {result.answer_0}
              </p>
              <p>
                <span className="kgc-before-after-label">After</span>
                {answer1}
              </p>
            </div>
          }
        />
      </div>
    </div>
  );
}
