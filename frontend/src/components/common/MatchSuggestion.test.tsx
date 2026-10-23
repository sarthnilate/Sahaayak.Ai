import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MatchSuggestion } from './MatchSuggestion';
import { Report, MatchCandidate } from '../../types';

describe('Phase 5: MatchSuggestion & ConfirmActionDialog', () => {
  const mockReport: Report = {
    id: 'rep-test-mr',
    original_text: 'हिंदमाता उड्डाणपुलाखाली पाणी भरले आहे, रस्ता बंद',
    input_language: 'mr',
    location_claim: 'Hindmata Flyover, Dadar',
    processing_status: 'processed',
    extraction_source: 'gemini',
    submitted_at: '2026-10-23T10:00:00Z',
    extracted_json: {
      category: 'waterlogging',
      reported_location_text: 'Hindmata, Dadar',
    },
  };

  const mockCandidate: MatchCandidate = {
    incident_id: 'inc-hindmata-001',
    incident_title: 'Severe Waterlogging at Hindmata Flyover',
    incident_category: 'waterlogging',
    incident_location: 'Hindmata Flyover, Dadar East',
    incident_created_at: '2026-10-23T09:30:00Z',
    band: 'strong',
    score: 0.85,
    rationale: 'Positive match: identical category (waterlogging); strong concept overlap (water/flood, road/traffic, blocked/bridge).',
    signals_for: [
      { name: 'same_category', weight: 0.35, matched: true, detail: 'Both classified as waterlogging' },
      { name: 'concept_overlap', weight: 0.25, matched: true, detail: 'Cross-lingual Marathi-English overlap (Jaccard: 0.60)' },
    ],
    signals_against: [],
    unknowns: ['Coordinates ungrounded on report (not penalized)'],
    is_same_origin: true,
    origin_fingerprint: 'fp-hindmata-broadcast',
    existing_link_status: 'suggested',
  };

  it('renders side-by-side comparison with explainable band and signals (no percentage as proof)', () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onReject = vi.fn().mockResolvedValue(undefined);
    const onCreateNewIncident = vi.fn().mockResolvedValue(undefined);

    render(
      <MatchSuggestion
        report={mockReport}
        candidate={mockCandidate}
        onConfirm={onConfirm}
        onReject={onReject}
        onCreateNewIncident={onCreateNewIncident}
      />
    );

    // Side-by-side report and candidate incident
    expect(screen.getByText(/हिंदमाता उड्डाणपुलाखाली पाणी भरले आहे/)).toBeInTheDocument();
    expect(screen.getByText('Severe Waterlogging at Hindmata Flyover')).toBeInTheDocument();

    // Explainable band (Strong Match with text, not a raw probability)
    expect(screen.getByText('Strong Match')).toBeInTheDocument();

    // Copied-claim indicator
    expect(screen.getByText(/Copied Claim \/ Same Origin/i)).toBeInTheDocument();

    // Signals for, contra, and unknowns
    expect(screen.getByText(/Both classified as waterlogging/i)).toBeInTheDocument();
    expect(screen.getByText(/Coordinates ungrounded on report/i)).toBeInTheDocument();

    // Action buttons
    expect(screen.getByRole('button', { name: /confirm link/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reject match/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create new incident/i })).toBeInTheDocument();
  });

  it('opens accessible ConfirmActionDialog, supports notes, and submits on confirm', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onReject = vi.fn().mockResolvedValue(undefined);
    const onCreateNewIncident = vi.fn().mockResolvedValue(undefined);

    render(
      <MatchSuggestion
        report={mockReport}
        candidate={mockCandidate}
        onConfirm={onConfirm}
        onReject={onReject}
        onCreateNewIncident={onCreateNewIncident}
      />
    );

    // Click Confirm Link
    const confirmBtn = screen.getByRole('button', { name: /confirm link/i });
    await user.click(confirmBtn);

    // Dialog opens with role="dialog" and aria-modal="true"
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByText('Confirm Duplicate Match')).toBeInTheDocument();

    // Type coordinator review notes
    const notesInput = screen.getByLabelText(/Coordinator Review Notes/i);
    fireEvent.change(notesInput, { target: { value: 'Confirmed Marathi report matches Dadar cluster' } });

    // Submit confirm inside dialog
    const submitBtn = within(dialog).getByRole('button', { name: /confirm link/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith(
        'inc-hindmata-001',
        'rep-test-mr',
        'Confirmed Marathi report matches Dadar cluster'
      );
    });
  });

  it('closes ConfirmActionDialog on Escape key press and does not submit', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onReject = vi.fn().mockResolvedValue(undefined);
    const onCreateNewIncident = vi.fn().mockResolvedValue(undefined);

    render(
      <MatchSuggestion
        report={mockReport}
        candidate={mockCandidate}
        onConfirm={onConfirm}
        onReject={onReject}
        onCreateNewIncident={onCreateNewIncident}
      />
    );

    // Click Reject Match
    const rejectBtn = screen.getByRole('button', { name: /reject match/i });
    await user.click(rejectBtn);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Reject Duplicate Suggestion')).toBeInTheDocument();

    // Press Escape
    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(onReject).not.toHaveBeenCalled();
  });
});
