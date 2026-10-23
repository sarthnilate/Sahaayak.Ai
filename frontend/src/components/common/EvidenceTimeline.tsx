/**
 * EvidenceTimeline – Phase 6
 *
 * Full evidence panel for an incident:
 *  - Header: overall verification status, independent source count, suggested vs current status
 *  - Verification availability notice (honest: "Independent verification is unavailable…")
 *  - Chronological evidence list via EvidenceItemCard
 *  - "Conflicts" panel (items assessed as 'contradicts')
 *  - "Missing evidence" panel (computed gaps from backend)
 *  - Accessible manual add-evidence form (coordinator only)
 *  - Coordinator review dialog with required note
 *  - Status override dialog (coordinator only)
 *
 * TERMINOLOGY: Never "verified true" or "fake". Spec-compliant labels.
 * Model confidence never displayed as a probability.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { EvidenceItem, EvidenceStatus, IncidentEvidenceListResponse, MissingEvidenceGap } from '../../types';
import { addEvidence, getIncidentEvidence, overrideIncidentEvidenceStatus, reviewEvidence } from '../../services/api';
import { EvidenceItemCard } from './EvidenceItemCard';
import './EvidenceTimeline.css';

// ─── Evidence status display meta ─────────────────────────────────────────────

const STATUS_META: Record<EvidenceStatus, { label: string; cls: string; icon: string }> = {
  unassessed:             { label: 'Unassessed',                    cls: 'evstatus--unassessed',   icon: '○' },
  unverified:             { label: 'Unverified',                    cls: 'evstatus--unverified',   icon: '⊘' },
  partially_corroborated: { label: 'Partially Corroborated',        cls: 'evstatus--partial',      icon: '◑' },
  conflicting_evidence:   { label: 'Conflicting Evidence',          cls: 'evstatus--conflicting',  icon: '⚡' },
  corroborated:           { label: 'Corroborated by Available Evidence', cls: 'evstatus--corroborated', icon: '✓' },
  closed_after_review:    { label: 'Closed After Review',           cls: 'evstatus--closed',       icon: '✔' },
};

const ALLOWED_NEXT_STATUSES: Record<EvidenceStatus, EvidenceStatus[]> = {
  unassessed:             ['unverified'],
  unverified:             ['partially_corroborated', 'conflicting_evidence'],
  partially_corroborated: ['conflicting_evidence', 'corroborated', 'closed_after_review'],
  conflicting_evidence:   ['partially_corroborated', 'corroborated', 'unverified', 'closed_after_review'],
  corroborated:           ['conflicting_evidence', 'partially_corroborated', 'closed_after_review'],
  closed_after_review:    ['partially_corroborated', 'unverified', 'conflicting_evidence'],
};

// ─── Props ────────────────────────────────────────────────────────────────────

interface Props {
  incidentId: string;
  isCoordinator?: boolean;
}

// ─── Review dialog ────────────────────────────────────────────────────────────

interface ReviewDialogState {
  open: boolean;
  item: EvidenceItem | null;
  notes: string;
  assessment: string;
  loading: boolean;
  error: string | null;
}

const INITIAL_REVIEW: ReviewDialogState = {
  open: false, item: null, notes: '', assessment: '', loading: false, error: null
};

// ─── Add evidence form ────────────────────────────────────────────────────────

interface AddFormState {
  source_name: string;
  claim_summary: string;
  source_url: string;
  source_description: string;
  evidence_type: string;
  assessment: string;
  excerpt: string;
  loading: boolean;
  error: string | null;
}

const INITIAL_FORM: AddFormState = {
  source_name: '', claim_summary: '', source_url: '', source_description: '',
  evidence_type: 'user_claim', assessment: 'unassessed', excerpt: '',
  loading: false, error: null,
};

// ─── Status override dialog ───────────────────────────────────────────────────

interface StatusDialogState {
  open: boolean;
  targetStatus: EvidenceStatus | '';
  notes: string;
  loading: boolean;
  error: string | null;
}

const INITIAL_STATUS_DIALOG: StatusDialogState = {
  open: false, targetStatus: '', notes: '', loading: false, error: null
};

// ─── Component ───────────────────────────────────────────────────────────────

export const EvidenceTimeline: React.FC<Props> = ({ incidentId, isCoordinator = false }) => {
  const [data, setData] = useState<IncidentEvidenceListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [reviewDialog, setReviewDialog] = useState<ReviewDialogState>(INITIAL_REVIEW);
  const [statusDialog, setStatusDialog] = useState<StatusDialogState>(INITIAL_STATUS_DIALOG);
  const [addForm, setAddForm] = useState<AddFormState>(INITIAL_FORM);

  // Load evidence
  const loadEvidence = useCallback(async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const res = await getIncidentEvidence(incidentId);
      setData(res);
    } catch (err: any) {
      setLoadError(err.message ?? 'Failed to load evidence');
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => { loadEvidence(); }, [loadEvidence]);

  // Compute same-origin groups
  const originGroupCounts = useMemo(() => {
    if (!data) return {};
    const counts: Record<string, number> = {};
    for (const item of data.items) {
      const key = item.independence_group ?? item.id;
      counts[key] = (counts[key] ?? 0) + 1;
    }
    return counts;
  }, [data]);

  // ── Review dialog handlers ─────────────────────────────────────────────────

  const openReviewDialog = (item: EvidenceItem) => {
    setReviewDialog({ ...INITIAL_REVIEW, open: true, item, assessment: item.assessment });
  };

  const handleReviewSubmit = async () => {
    if (!reviewDialog.item || !reviewDialog.notes.trim()) return;
    setReviewDialog(d => ({ ...d, loading: true, error: null }));
    try {
      await reviewEvidence(reviewDialog.item.id, {
        reviewer_notes: reviewDialog.notes.trim(),
        assessment: reviewDialog.assessment || undefined,
      });
      setReviewDialog(INITIAL_REVIEW);
      await loadEvidence();
    } catch (err: any) {
      setReviewDialog(d => ({ ...d, loading: false, error: err.message ?? 'Review failed' }));
    }
  };

  // ── Add evidence handlers ──────────────────────────────────────────────────

  const handleAddEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addForm.source_name.trim() || !addForm.claim_summary.trim()) return;
    setAddForm(f => ({ ...f, loading: true, error: null }));
    try {
      await addEvidence(incidentId, {
        source_name: addForm.source_name.trim(),
        claim_summary: addForm.claim_summary.trim(),
        source_url: addForm.source_url.trim() || null,
        source_description: addForm.source_description.trim() || null,
        evidence_type: addForm.evidence_type,
        assessment: addForm.assessment,
        excerpt: addForm.excerpt.trim() || null,
      });
      setAddForm(INITIAL_FORM);
      setShowAddForm(false);
      await loadEvidence();
    } catch (err: any) {
      setAddForm(f => ({ ...f, loading: false, error: err.message ?? 'Could not attach evidence' }));
    }
  };

  // ── Status override handlers ───────────────────────────────────────────────

  const handleStatusOverride = async () => {
    if (!statusDialog.targetStatus || !statusDialog.notes.trim()) return;
    setStatusDialog(d => ({ ...d, loading: true, error: null }));
    try {
      const res = await overrideIncidentEvidenceStatus(incidentId, {
        status: statusDialog.targetStatus,
        reviewer_notes: statusDialog.notes.trim(),
      });
      setData(res);
      setStatusDialog(INITIAL_STATUS_DIALOG);
    } catch (err: any) {
      setStatusDialog(d => ({ ...d, loading: false, error: err.message ?? 'Status override failed' }));
    }
  };

  // ─── Render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="ev-timeline ev-timeline--loading" role="status" aria-live="polite">
        <div className="ev-spinner" aria-hidden="true" />
        <span>Loading evidence…</span>
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div className="ev-timeline ev-timeline--error" role="alert">
        <span>⚠ {loadError ?? 'Failed to load evidence.'}</span>
        <button className="btn-sm btn-outline" onClick={loadEvidence}>Retry</button>
      </div>
    );
  }

  const currentStatusMeta = STATUS_META[data.evidence_status] ?? STATUS_META.unassessed;
  const suggestedStatusMeta = STATUS_META[data.suggested_status] ?? STATUS_META.unassessed;
  const conflicts = data.items.filter(i => i.assessment === 'contradicts');
  const allowedTransitions = ALLOWED_NEXT_STATUSES[data.evidence_status] ?? [];

  return (
    <section className="ev-timeline" aria-label="Evidence timeline">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="ev-header">
        <div className="ev-header__status-row">
          <div className="ev-header__status-block">
            <span className="ev-label">Current status</span>
            <span className={`ev-status-chip ${currentStatusMeta.cls}`} role="status">
              {currentStatusMeta.icon} {currentStatusMeta.label}
            </span>
          </div>

          {data.suggested_status !== data.evidence_status && (
            <div className="ev-header__status-block">
              <span className="ev-label">Suggested</span>
              <span className={`ev-status-chip ev-status-chip--suggested ${suggestedStatusMeta.cls}`} role="note">
                {suggestedStatusMeta.icon} {suggestedStatusMeta.label}
              </span>
            </div>
          )}

          <div className="ev-header__stats">
            <div className="ev-stat">
              <span className="ev-stat__value">{data.independent_source_count}</span>
              <span className="ev-stat__label">independent source{data.independent_source_count !== 1 ? 's' : ''}</span>
            </div>
            {data.conflicts_count > 0 && (
              <div className="ev-stat ev-stat--conflict">
                <span className="ev-stat__value">{data.conflicts_count}</span>
                <span className="ev-stat__label">conflicting</span>
              </div>
            )}
            <div className="ev-stat">
              <span className="ev-stat__value">{data.items.length}</span>
              <span className="ev-stat__label">total items</span>
            </div>
          </div>

          {isCoordinator && allowedTransitions.length > 0 && (
            <button
              className="btn-sm btn-outline ev-header__override-btn"
              onClick={() => setStatusDialog({ ...INITIAL_STATUS_DIALOG, open: true })}
              aria-label="Override evidence status"
            >
              Set Status
            </button>
          )}
        </div>

        {/* Verification availability notice */}
        <div
          className={`ev-verification-notice ${data.verification.verification_available ? 'ev-verification-notice--available' : 'ev-verification-notice--unavailable'}`}
          role="note"
          aria-label={`Verification: ${data.verification.reason}`}
        >
          <span className="ev-verification-notice__icon" aria-hidden="true">
            {data.verification.verification_available ? '🔗' : '⚠'}
          </span>
          <span>
            {data.verification.verification_available
              ? `Live verification available via ${data.verification.provider_name ?? 'external feed'}`
              : `Independent verification is unavailable (${data.verification.reason})`
            }
          </span>
        </div>
      </div>

      {/* ── Conflicts panel ──────────────────────────────────────────────── */}
      {conflicts.length > 0 && (
        <div className="ev-panel ev-panel--conflicts" role="region" aria-label="Conflicting evidence">
          <h3 className="ev-panel__title">
            <span aria-hidden="true">⚡</span> Conflicts ({conflicts.length})
          </h3>
          <p className="ev-panel__desc">
            The following items contradict other evidence. Coordinator review recommended.
          </p>
          {conflicts.map(item => {
            const key = item.independence_group ?? item.id;
            const sameOrigin = Math.max(0, (originGroupCounts[key] ?? 1) - 1);
            return (
              <EvidenceItemCard
                key={item.id}
                item={item}
                sameOriginCount={sameOrigin}
                onReview={isCoordinator ? openReviewDialog : undefined}
                isCoordinator={isCoordinator}
              />
            );
          })}
        </div>
      )}

      {/* ── Missing evidence panel ───────────────────────────────────────── */}
      {data.missing_evidence.length > 0 && (
        <div className="ev-panel ev-panel--missing" role="region" aria-label="Missing evidence gaps">
          <h3 className="ev-panel__title">
            <span aria-hidden="true">📋</span> Missing Evidence ({data.missing_evidence.length})
          </h3>
          <ul className="ev-missing-list" role="list">
            {data.missing_evidence.map((gap: MissingEvidenceGap, i) => (
              <li key={i} className={`ev-missing-item ev-missing-item--${gap.severity}`} role="listitem">
                <span className="ev-missing-item__severity" aria-label={`Severity: ${gap.severity}`}>
                  {gap.severity === 'high' ? '🔴' : gap.severity === 'medium' ? '🟡' : '🔵'}
                </span>
                <div>
                  <span className="ev-missing-item__type">{gap.gap_type.replace(/_/g, ' ')}</span>
                  <p className="ev-missing-item__desc">{gap.description}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Timeline list ─────────────────────────────────────────────────── */}
      <div className="ev-list" role="list" aria-label="Evidence items (chronological)">
        {data.items.length === 0 ? (
          <div className="ev-empty" aria-live="polite">
            No evidence items attached yet.
          </div>
        ) : (
          data.items.map(item => {
            const key = item.independence_group ?? item.id;
            const sameOrigin = Math.max(0, (originGroupCounts[key] ?? 1) - 1);
            return (
              <div key={item.id} role="listitem">
                <EvidenceItemCard
                  item={item}
                  sameOriginCount={sameOrigin}
                  onReview={isCoordinator ? openReviewDialog : undefined}
                  isCoordinator={isCoordinator}
                />
              </div>
            );
          })
        )}
      </div>

      {/* ── Add evidence form ─────────────────────────────────────────────── */}
      {isCoordinator && (
        <div className="ev-add-section">
          {!showAddForm ? (
            <button
              className="ev-add-trigger"
              onClick={() => setShowAddForm(true)}
              aria-expanded="false"
              aria-controls="ev-add-form"
            >
              + Attach Evidence
            </button>
          ) : (
            <form
              id="ev-add-form"
              className="ev-add-form"
              onSubmit={handleAddEvidence}
              aria-label="Attach evidence to incident"
            >
              <h3 className="ev-add-form__title">Attach Evidence</h3>

              <div className="ev-field">
                <label htmlFor="ev-source-name" className="ev-field__label">Source name <span aria-hidden="true">*</span></label>
                <input
                  id="ev-source-name"
                  className="ev-field__input"
                  type="text"
                  required
                  placeholder="e.g. MCGM official bulletin, WhatsApp community group…"
                  value={addForm.source_name}
                  onChange={e => setAddForm(f => ({ ...f, source_name: e.target.value }))}
                  aria-required="true"
                />
              </div>

              <div className="ev-field">
                <label htmlFor="ev-claim-summary" className="ev-field__label">Summary <span aria-hidden="true">*</span></label>
                <textarea
                  id="ev-claim-summary"
                  className="ev-field__textarea"
                  required
                  rows={3}
                  placeholder="Describe what this evidence shows or claims…"
                  value={addForm.claim_summary}
                  onChange={e => setAddForm(f => ({ ...f, claim_summary: e.target.value }))}
                  aria-required="true"
                />
              </div>

              <div className="ev-field-row">
                <div className="ev-field">
                  <label htmlFor="ev-type" className="ev-field__label">Evidence type</label>
                  <select
                    id="ev-type"
                    className="ev-field__select"
                    value={addForm.evidence_type}
                    onChange={e => setAddForm(f => ({ ...f, evidence_type: e.target.value }))}
                  >
                    <option value="user_claim">Community Claim</option>
                    <option value="corroborating_report">Corroborating Report</option>
                    <option value="official_context">Official Context</option>
                    <option value="contradictory">Contradictory</option>
                    <option value="manual_attachment">Coordinator Attachment</option>
                  </select>
                </div>

                <div className="ev-field">
                  <label htmlFor="ev-assessment" className="ev-field__label">Initial assessment</label>
                  <select
                    id="ev-assessment"
                    className="ev-field__select"
                    value={addForm.assessment}
                    onChange={e => setAddForm(f => ({ ...f, assessment: e.target.value }))}
                  >
                    <option value="unassessed">Unassessed</option>
                    <option value="supports">Supports</option>
                    <option value="contradicts">Contradicts</option>
                    <option value="neutral">Neutral</option>
                    <option value="contextual">Contextual</option>
                  </select>
                </div>
              </div>

              <div className="ev-field">
                <label htmlFor="ev-source-url" className="ev-field__label">Source URL <span className="ev-field__hint">(optional — must be HTTPS)</span></label>
                <input
                  id="ev-source-url"
                  className="ev-field__input"
                  type="url"
                  placeholder="https://…"
                  value={addForm.source_url}
                  onChange={e => setAddForm(f => ({ ...f, source_url: e.target.value }))}
                  pattern="https://.*"
                  aria-describedby="ev-source-url-hint"
                />
                <span id="ev-source-url-hint" className="ev-field__hint-text">Only HTTPS URLs accepted. No URL is stored for synthetic items.</span>
              </div>

              <div className="ev-field">
                <label htmlFor="ev-excerpt" className="ev-field__label">Excerpt <span className="ev-field__hint">(optional key quote)</span></label>
                <input
                  id="ev-excerpt"
                  className="ev-field__input"
                  type="text"
                  placeholder="Direct quote or key excerpt…"
                  value={addForm.excerpt}
                  onChange={e => setAddForm(f => ({ ...f, excerpt: e.target.value }))}
                />
              </div>

              {addForm.error && (
                <div className="ev-add-form__error" role="alert">{addForm.error}</div>
              )}

              <div className="ev-add-form__actions">
                <button
                  type="button"
                  className="btn-sm btn-outline"
                  onClick={() => { setShowAddForm(false); setAddForm(INITIAL_FORM); }}
                  disabled={addForm.loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-sm btn-primary"
                  disabled={addForm.loading || !addForm.source_name.trim() || !addForm.claim_summary.trim()}
                  aria-busy={addForm.loading}
                >
                  {addForm.loading ? 'Attaching…' : 'Attach Evidence'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* ── Review dialog ─────────────────────────────────────────────────── */}
      {reviewDialog.open && reviewDialog.item && (
        <div className="ev-dialog-overlay" role="dialog" aria-modal="true" aria-label="Review evidence item">
          <div className="ev-dialog">
            <h2 className="ev-dialog__title">Review Evidence</h2>
            <p className="ev-dialog__subtitle">Source: <strong>{reviewDialog.item.source_name}</strong></p>
            <p className="ev-dialog__claim">{reviewDialog.item.claim_summary}</p>

            <div className="ev-field">
              <label htmlFor="ev-review-assessment" className="ev-field__label">Assessment</label>
              <select
                id="ev-review-assessment"
                className="ev-field__select"
                value={reviewDialog.assessment}
                onChange={e => setReviewDialog(d => ({ ...d, assessment: e.target.value }))}
              >
                <option value="unassessed">Unassessed</option>
                <option value="supports">Supports</option>
                <option value="contradicts">Contradicts</option>
                <option value="neutral">Neutral</option>
                <option value="contextual">Contextual</option>
              </select>
            </div>

            <div className="ev-field">
              <label htmlFor="ev-review-notes" className="ev-field__label">
                Coordinator note <span aria-hidden="true">*</span>
                <span className="ev-field__hint"> (required)</span>
              </label>
              <textarea
                id="ev-review-notes"
                className="ev-field__textarea"
                rows={4}
                required
                placeholder="Explain your assessment decision…"
                value={reviewDialog.notes}
                onChange={e => setReviewDialog(d => ({ ...d, notes: e.target.value }))}
                aria-required="true"
              />
            </div>

            {reviewDialog.error && (
              <div className="ev-add-form__error" role="alert">{reviewDialog.error}</div>
            )}

            <div className="ev-dialog__actions">
              <button
                className="btn-sm btn-outline"
                onClick={() => setReviewDialog(INITIAL_REVIEW)}
                disabled={reviewDialog.loading}
              >
                Cancel
              </button>
              <button
                className="btn-sm btn-primary"
                onClick={handleReviewSubmit}
                disabled={reviewDialog.loading || !reviewDialog.notes.trim()}
                aria-busy={reviewDialog.loading}
              >
                {reviewDialog.loading ? 'Saving…' : 'Save Review'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Status override dialog ────────────────────────────────────────── */}
      {statusDialog.open && (
        <div className="ev-dialog-overlay" role="dialog" aria-modal="true" aria-label="Override verification status">
          <div className="ev-dialog">
            <h2 className="ev-dialog__title">Set Verification Status</h2>
            <p className="ev-dialog__subtitle">
              Current: <span className={`ev-status-chip ${currentStatusMeta.cls}`}>{currentStatusMeta.label}</span>
            </p>

            <div className="ev-field">
              <label htmlFor="ev-status-select" className="ev-field__label">New status <span aria-hidden="true">*</span></label>
              <select
                id="ev-status-select"
                className="ev-field__select"
                value={statusDialog.targetStatus}
                onChange={e => setStatusDialog(d => ({ ...d, targetStatus: e.target.value as EvidenceStatus }))}
                aria-required="true"
              >
                <option value="">— select —</option>
                {allowedTransitions.map(s => (
                  <option key={s} value={s}>{STATUS_META[s]?.label ?? s}</option>
                ))}
              </select>
            </div>

            <div className="ev-field">
              <label htmlFor="ev-status-notes" className="ev-field__label">
                Reason <span aria-hidden="true">*</span>
                <span className="ev-field__hint"> (required — audited)</span>
              </label>
              <textarea
                id="ev-status-notes"
                className="ev-field__textarea"
                rows={3}
                required
                placeholder="Explain why you are overriding the status…"
                value={statusDialog.notes}
                onChange={e => setStatusDialog(d => ({ ...d, notes: e.target.value }))}
                aria-required="true"
              />
            </div>

            {statusDialog.error && (
              <div className="ev-add-form__error" role="alert">{statusDialog.error}</div>
            )}

            <div className="ev-dialog__actions">
              <button
                className="btn-sm btn-outline"
                onClick={() => setStatusDialog(INITIAL_STATUS_DIALOG)}
                disabled={statusDialog.loading}
              >
                Cancel
              </button>
              <button
                className="btn-sm btn-primary"
                onClick={handleStatusOverride}
                disabled={statusDialog.loading || !statusDialog.targetStatus || !statusDialog.notes.trim()}
                aria-busy={statusDialog.loading}
              >
                {statusDialog.loading ? 'Saving…' : 'Override Status'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default EvidenceTimeline;
