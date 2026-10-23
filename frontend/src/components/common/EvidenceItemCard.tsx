/**
 * EvidenceItemCard – Phase 6
 * Renders a single evidence item with:
 *  - Provenance badge (LIVE OFFICIAL / COMMUNITY CLAIM / AI ANALYSIS / SYNTHETIC)
 *  - Assessment icon + text (supports / contradicts / neutral / contextual / unassessed)
 *  - Freshness label
 *  - "Same origin as N other reports" note
 *  - SYNTHETIC badge when is_simulated=true (null URL enforced)
 *
 * TERMINOLOGY: Never "verified true" or "fake". Uses spec labels.
 */

import React from 'react';
import { EvidenceItem, EvidenceAssessment, EvidenceType } from '../../types';
import './EvidenceItemCard.css';

// ─── Provenance Badge ─────────────────────────────────────────────────────────

type ProvenanceKind = 'LIVE OFFICIAL' | 'COMMUNITY CLAIM' | 'AI ANALYSIS' | 'SYNTHETIC';

function getProvenanceKind(item: EvidenceItem): ProvenanceKind {
  if (item.is_simulated) return 'SYNTHETIC';
  if (item.evidence_type === 'official_context') return 'LIVE OFFICIAL';
  if (item.evidence_type === 'corroborating_report' || item.evidence_type === 'user_claim') return 'COMMUNITY CLAIM';
  return 'AI ANALYSIS';
}

const PROVENANCE_STYLES: Record<ProvenanceKind, string> = {
  'LIVE OFFICIAL':   'badge--official',
  'COMMUNITY CLAIM': 'badge--community',
  'AI ANALYSIS':     'badge--ai',
  'SYNTHETIC':       'badge--synthetic',
};

// ─── Assessment ───────────────────────────────────────────────────────────────

const ASSESSMENT_META: Record<EvidenceAssessment, { icon: string; label: string; cls: string }> = {
  supports:    { icon: '✓', label: 'Supports',           cls: 'assessment--supports'    },
  contradicts: { icon: '✕', label: 'Contradicts',        cls: 'assessment--contradicts' },
  neutral:     { icon: '–', label: 'Neutral',             cls: 'assessment--neutral'     },
  contextual:  { icon: 'ℹ', label: 'Contextual',         cls: 'assessment--contextual'  },
  unassessed:  { icon: '?', label: 'Unassessed',         cls: 'assessment--unassessed'  },
};

// ─── Freshness label ─────────────────────────────────────────────────────────

function freshnessLabel(freshness: string | null | undefined): string {
  if (!freshness) return '⚪ Unknown age';
  switch (freshness) {
    case 'fresh':   return '🟢 Fresh';
    case 'recent':  return '🟡 Recent';
    case 'stale':   return '🔴 Stale';
    case 'unknown': return '⚪ Unknown age';
    default:        return `🟡 ${freshness}`;   // pass-through for raw strings like "< 3h"
  }
}

// ─── Evidence type display ───────────────────────────────────────────────────

const EVIDENCE_TYPE_LABELS: Record<EvidenceType, string> = {
  user_claim:          'Community Claim',
  corroborating_report:'Corroborating Report',
  official_context:    'Official Context',
  contradictory:       'Contradictory',
  manual_attachment:   'Coordinator Attachment',
  synthetic_test:      'Synthetic Demo',
};

// ─── Timestamp formatting ─────────────────────────────────────────────────────

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true,
    });
  } catch {
    return iso;
  }
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface Props {
  item: EvidenceItem;
  /** How many items share the same independence_group (excluding this one) */
  sameOriginCount?: number;
  onReview?: (item: EvidenceItem) => void;
  isCoordinator?: boolean;
}

// ─── Component ───────────────────────────────────────────────────────────────

export const EvidenceItemCard: React.FC<Props> = ({
  item, sameOriginCount = 0, onReview, isCoordinator
}) => {
  const provenanceKind = getProvenanceKind(item);
  const assessmentMeta = ASSESSMENT_META[item.assessment] ?? ASSESSMENT_META.unassessed;

  return (
    <article
      className={`evidence-card ${item.assessment === 'contradicts' ? 'evidence-card--conflict' : ''}`}
      aria-label={`Evidence: ${item.source_name}`}
    >
      {/* Header row */}
      <div className="evidence-card__header">
        <div className="evidence-card__badges">
          <span
            className={`provenance-badge ${PROVENANCE_STYLES[provenanceKind]}`}
            role="img"
            aria-label={`Provenance: ${provenanceKind}`}
          >
            {provenanceKind}
          </span>
          {item.is_simulated && (
            <span className="provenance-badge badge--synthetic-explicit" aria-label="Synthetic demo data">
              SYNTHETIC
            </span>
          )}
        </div>

        <div
          className={`assessment-chip ${assessmentMeta.cls}`}
          role="status"
          aria-label={`Assessment: ${assessmentMeta.label}`}
        >
          <span className="assessment-chip__icon" aria-hidden="true">{assessmentMeta.icon}</span>
          <span className="assessment-chip__label">{assessmentMeta.label}</span>
        </div>
      </div>

      {/* Source & claim */}
      <div className="evidence-card__body">
        <div className="evidence-card__source-row">
          <strong className="evidence-card__source-name">{item.source_name}</strong>
          <span className="evidence-card__type-label">
            {EVIDENCE_TYPE_LABELS[item.evidence_type] ?? item.evidence_type}
          </span>
        </div>

        {item.source_description && (
          <p className="evidence-card__source-desc">{item.source_description}</p>
        )}

        <p className="evidence-card__claim">{item.claim_summary}</p>

        {item.excerpt && (
          <blockquote className="evidence-card__excerpt">"{item.excerpt}"</blockquote>
        )}

        {/* Source URL — NEVER shown for synthetic items */}
        {!item.is_simulated && item.source_url ? (
          <a
            className="evidence-card__url"
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`External source: ${item.source_url}`}
          >
            🔗 Source link ↗
          </a>
        ) : item.is_simulated ? (
          <span className="evidence-card__url evidence-card__url--no-link" aria-label="No URL for synthetic evidence">
            No external URL (synthetic demo data)
          </span>
        ) : null}
      </div>

      {/* Meta row */}
      <div className="evidence-card__meta">
        <span className="evidence-card__freshness" aria-label={`Freshness: ${item.freshness}`}>
          {freshnessLabel(item.freshness)}
        </span>
        <span className="evidence-card__ts" aria-label={`Submitted at: ${fmtDateTime(item.created_at)}`}>
          {fmtDateTime(item.created_at)}
        </span>
        {item.source_timestamp && (
          <span className="evidence-card__ts" aria-label={`Source date: ${fmtDateTime(item.source_timestamp)}`}>
            Source: {fmtDateTime(item.source_timestamp)}
          </span>
        )}
      </div>

      {/* Same-origin note */}
      {sameOriginCount > 0 && (
        <div className="evidence-card__origin-note" role="note" aria-live="polite">
          ⛓ Same origin as {sameOriginCount} other report{sameOriginCount > 1 ? 's' : ''} — counts as 1 independent source
        </div>
      )}

      {/* Reviewer notes */}
      {item.reviewer_notes && (
        <div className="evidence-card__review-note">
          <span className="evidence-card__review-label">Coordinator note:</span>
          <span className="evidence-card__review-text">{item.reviewer_notes}</span>
          {item.reviewed_by && (
            <span className="evidence-card__reviewed-by"> — {item.reviewed_by}</span>
          )}
        </div>
      )}

      {/* Coordinator actions */}
      {isCoordinator && onReview && (
        <div className="evidence-card__actions">
          <button
            className="btn btn-sm btn-outline"
            onClick={() => onReview(item)}
            aria-label={`Review evidence item: ${item.source_name}`}
          >
            Review
          </button>
        </div>
      )}
    </article>
  );
};

export default EvidenceItemCard;
