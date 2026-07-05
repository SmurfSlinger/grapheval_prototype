import type {
  BacktrackingFeedbackItem,
  BacktrackingResult,
  KgcEvaluatedClaim,
} from "@/lib/api";

export function shortObject(value: string): string {
  return value
    .replace(/^five\s+/i, "")
    .replace(/\s+rocket$/i, " rocket")
    .trim();
}

/** Human-readable launch site (KGc may store without "at"). */
export function formatLaunchLocation(value: string): string {
  const normalized = value.trim();
  const atMatch = normalized.match(
    /^(Launch Complex 39A)\s+(?:at\s+)?(Kennedy Space Center)$/i,
  );
  if (atMatch) {
    return `${atMatch[1]} at ${atMatch[2]}`;
  }
  if (/^Launch Complex 39A$/i.test(normalized)) {
    return `${normalized} at Kennedy Space Center`;
  }
  return normalized;
}

function formatRocketLabel(value: string): string {
  const base = shortObject(value.replace(/^a\s+/i, ""));
  if (/\brocket$/i.test(base)) {
    return base;
  }
  if (/\bsaturn\s+(ib|v)\b/i.test(base)) {
    return `${base} rocket`;
  }
  return base;
}

function correctedObjectForClaim(claim: KgcEvaluatedClaim): string | null {
  return claim.conflicting_fact?.object ?? claim.conflicting_object ?? null;
}

/** One-line before/after for a contradicted or no-evidence claim. */
export function formatCorrectionLine(claim: KgcEvaluatedClaim): string | null {
  const relation = claim.triple.relation;
  const fromObject = claim.triple.object;

  if (claim.label === "CONTRADICTED") {
    const corrected = correctedObjectForClaim(claim);
    if (!corrected) {
      return null;
    }
    if (relation === "launched_by") {
      return `${formatRocketLabel(fromObject)} → ${formatRocketLabel(corrected)}`;
    }
    if (relation === "launched_from") {
      return `${fromObject} → ${formatLaunchLocation(corrected)}`;
    }
    return `${shortObject(fromObject)} → ${shortObject(corrected)}`;
  }

  if (claim.label === "NO_EVIDENCE") {
    return `${shortObject(fromObject)} (removed/deferred)`;
  }

  return null;
}

function formatFeedbackCorrectionLine(fb: BacktrackingFeedbackItem): string {
  const relation = fb.triple.relation;
  const fromObject = fb.triple.object;

  if (fb.label === "CONTRADICTED") {
    const corrected =
      fb.conflicting_fact?.object ?? fb.conflicting_object ?? null;
    if (!corrected) {
      return shortObject(fromObject);
    }
    if (relation === "launched_by") {
      return `${formatRocketLabel(fromObject)} → ${formatRocketLabel(corrected)}`;
    }
    if (relation === "launched_from") {
      return `${fromObject} → ${formatLaunchLocation(corrected)}`;
    }
    return `${shortObject(fromObject)} → ${shortObject(corrected)}`;
  }

  return `${shortObject(fromObject)} claim`;
}

export function formatFactLine(fact: {
  subject: string;
  relation: string;
  object: string;
}): string {
  return `${fact.subject} → ${fact.relation.replaceAll("_", " ")} → ${fact.object}`;
}

export function contextPreview(context: string, maxSentences = 2): string {
  const trimmed = context.trim();
  const sentences = trimmed.match(/[^.!?]+[.!?]+(\s|$)/g);
  if (!sentences || sentences.length <= maxSentences) {
    return trimmed;
  }
  return `${sentences.slice(0, maxSentences).join(" ").trim()}…`;
}

export function contextNeedsExpand(context: string, maxSentences = 2): boolean {
  const trimmed = context.trim();
  const sentences = trimmed.match(/[^.!?]+[.!?]+(\s|$)/g);
  return Boolean(sentences && sentences.length > maxSentences);
}

export function buildChangedClaims(claims: KgcEvaluatedClaim[]): string[] {
  const changed: string[] = [];

  for (const claim of claims) {
    const line = formatCorrectionLine(claim);
    if (line) {
      changed.push(line);
    }
  }

  return changed;
}

export function buildClaimCheckLines(claims: KgcEvaluatedClaim[]): {
  fixed: string[];
  kept: string[];
  removed: string[];
} {
  const fixed: string[] = [];
  const kept: string[] = [];
  const removed: string[] = [];

  for (const claim of claims) {
    const objectLabel = shortObject(claim.triple.object);
    if (claim.label === "SUPPORTED") {
      kept.push(objectLabel);
    } else if (claim.label === "CONTRADICTED") {
      const line = formatCorrectionLine(claim);
      if (line) {
        fixed.push(line);
      }
    } else if (claim.label === "NO_EVIDENCE") {
      removed.push(`${objectLabel} claim`);
    }
  }

  return { fixed, kept, removed };
}

export function buildFeedbackLines(result: BacktrackingResult): {
  keep: string[];
  fix: string[];
  remove: string[];
} {
  const keep: string[] = [];
  const fix: string[] = [];
  const remove: string[] = [];

  for (const fb of result.backtracking_feedback) {
    const objectLabel = shortObject(fb.triple.object);
    if (fb.label === "SUPPORTED") {
      keep.push(objectLabel);
    } else if (fb.label === "CONTRADICTED") {
      fix.push(formatFeedbackCorrectionLine(fb));
    } else {
      remove.push(`${objectLabel} claim`);
    }
  }

  return { keep, fix, remove };
}

export function hasDemoIssues(result: BacktrackingResult): boolean {
  return result.contradicted_count > 0 || result.no_evidence_count > 0;
}

export function factCountShort(count: number): string {
  return count === 1 ? "1 fact" : `${count} facts`;
}
