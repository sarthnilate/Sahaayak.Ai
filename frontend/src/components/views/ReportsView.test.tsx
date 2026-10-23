import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReportsView } from './ReportsView';
import { AuthProvider } from '../../contexts/AuthContext';
import { Report } from '../../types';
import * as api from '../../services/api';

vi.mock('../../services/api', () => ({
  getMe: vi.fn().mockResolvedValue({
    id: 'user-coord',
    username: 'coordinator',
    email: 'coord@sahaayak.ai',
    role: 'coordinator',
  }),
  getAiStatus: vi.fn().mockResolvedValue({
    mode: 'demo',
    provider: 'deterministic-demo',
    model: 'demo-ruleset-v1',
    api_key_configured: false,
  }),
  submitReport: vi.fn(),
  retryReport: vi.fn(),
  submitCoordinatorCorrection: vi.fn(),
  getReportImageUrl: vi.fn().mockReturnValue('/api/v1/reports/123/image'),
}));

const mockReport: Report = {
  id: 'rep-test-001',
  reference_code: 'CR-2026-001',
  original_text: 'दादर टीटी सर्कल और हिंदमाता के पास 3 फीट पानी भर गया है',
  input_language: 'hi',
  reporter_name: 'राजेश गुप्ता',
  location_claim: 'दादर टीटी सर्कल',
  processing_status: 'processed',
  extraction_source: 'deterministic-demo',
  extraction_metadata: {
    provider: 'deterministic-demo',
    mode: 'demo',
    model: 'demo-ruleset-v1',
    latency_ms: 12,
    attempt_count: 1,
    schema_version: '1.0.0',
    simulated: true,
    processed_at: '2026-10-23T11:00:00Z',
  },
  extracted_json: {
    category: 'waterlogging',
    short_summary: 'Severe waterlogging at Dadar TT Circle with trapped traffic',
    original_text_language: 'hi',
    reported_location_text: 'Dadar TT Circle and Hindmata',
    location_precision: 'neighborhood',
    location_source: 'extracted_from_text',
    incident_time: null,
    claimed_severity: 'critical',
    safety_concern: true,
    safety_concern_reason: 'Rising water level trapping vehicles and pedestrians',
    people_or_infrastructure_affected: ['Dadar TT underpass', 'Commercial stores', 'City buses'],
    source_attribution: 'Citizen witness report',
    is_forwarded_message: false,
    explicit_facts: [
      '3 feet of water accumulated',
      'Stores and vehicles are submerging',
      'People are stranded',
    ],
    model_inferences: [
      'Likely stormwater drainage capacity failure',
      'Risk of electric hazard from street junction boxes',
    ],
    missing_information: [
      'Exact water depth measurement in centimeters',
      'Presence of injured persons',
    ],
    ambiguities: [],
    contradictions: [],
    follow_up_questions: [
      'Are stormwater pumps currently active at Hindmata?',
      'Has local police cordoned off traffic?',
    ],
  },
  submitted_at: '2026-10-23T10:45:00Z',
};

describe('Phase 3 ReportsView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders report list with DEMO MODE badge and language tags', async () => {
    render(
      <AuthProvider>
        <ReportsView reports={[mockReport]} onRefresh={vi.fn()} isLoading={false} />
      </AuthProvider>
    );

    // Global AI mode badge
    expect(await screen.findByTestId('global-ai-mode-badge')).toHaveTextContent(/DEMO MODE \(simulated\)/i);

    // Report card demo badge
    expect(screen.getByTestId('report-demo-badge')).toHaveTextContent(/DEMO MODE \(simulated\)/i);

    // Original Hindi text with lang attribute
    const reportText = screen.getByText(/दादर टीटी सर्कल और हिंदमाता/i);
    expect(reportText).toBeInTheDocument();
    expect(reportText.getAttribute('lang')).toBe('hi');
  });

  it('opens report detail modal showing dual-column layout with all Phase 3 sections', async () => {
    render(
      <AuthProvider>
        <ReportsView reports={[mockReport]} onRefresh={vi.fn()} isLoading={false} />
      </AuthProvider>
    );

    // Click on report card to open modal
    const inspectBtn = screen.getByText(/INSPECT EXTRACTION/i);
    fireEvent.click(inspectBtn);

    // Verify Modal Header & Demo Badge
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByTestId('detail-demo-badge')).toHaveTextContent(/DEMO MODE \(simulated\)/i);

    // Check Left Column: "Reported (by the person)"
    expect(screen.getByText(/Reported \(by the person\)/i)).toBeInTheDocument();
    const modalReportedText = screen.getAllByText(/दादर टीटी सर्कल और हिंदमाता/i).find(el => el.getAttribute('lang') === 'hi');
    expect(modalReportedText).toBeInTheDocument();

    // Check Right Column 4 Sections:
    // 1. "Extracted by AI"
    expect(screen.getByText(/Extracted by AI/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Severe waterlogging at Dadar TT Circle/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/3 feet of water accumulated/i)).toBeInTheDocument();

    // 2. "Inferred by AI"
    expect(screen.getByText(/Inferred by AI/i)).toBeInTheDocument();
    expect(screen.getByText(/ACTIVE THREAT DETECTED/i)).toBeInTheDocument();
    expect(screen.getByText(/Likely stormwater drainage capacity failure/i)).toBeInTheDocument();

    // 3. "Unknown / missing"
    expect(screen.getByText(/Unknown \/ Missing/i)).toBeInTheDocument();
    expect(screen.getByText(/Exact water depth measurement in centimeters/i)).toBeInTheDocument();

    // 4. "Needs follow-up"
    expect(screen.getByText(/Needs Follow-Up/i)).toBeInTheDocument();
    expect(screen.getByText(/Are stormwater pumps currently active at Hindmata\?/i)).toBeInTheDocument();
  });

  it('supports retry extraction with loading state and aria-live announcements', async () => {
    const updatedReport = {
      ...mockReport,
      processing_status: 'processed' as const,
      attempt_count: 2,
    };
    vi.mocked(api.retryReport).mockResolvedValueOnce(updatedReport);

    render(
      <AuthProvider>
        <ReportsView reports={[mockReport]} onRefresh={vi.fn()} isLoading={false} />
      </AuthProvider>
    );

    // Open detail modal
    fireEvent.click(screen.getByText(/INSPECT EXTRACTION/i));
    await screen.findByRole('dialog');

    // Click Retry Button
    const retryBtn = screen.getByTestId('retry-button');
    expect(retryBtn).toHaveAttribute('aria-live', 'polite');

    fireEvent.click(retryBtn);
    expect(api.retryReport).toHaveBeenCalledWith('rep-test-001');

    await waitFor(() => {
      expect(screen.getByText(/Retry succeeded! Status: processed/i)).toBeInTheDocument();
    });
  });

  it('allows coordinator to submit annotations without overwriting AI extraction', async () => {
    vi.mocked(api.submitCoordinatorCorrection).mockResolvedValueOnce({
      ...mockReport,
      coordinator_correction: {
        corrected_category: 'waterlogging',
        corrected_severity: 'critical',
        correction_notes: 'Verified via CCTV feed dadar-cam-04',
      },
      corrected_by: 'coordinator',
      corrected_at: '2026-10-23T11:15:00Z',
    });

    render(
      <AuthProvider>
        <ReportsView reports={[mockReport]} onRefresh={vi.fn()} isLoading={false} />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText(/INSPECT EXTRACTION/i));
    await screen.findByRole('dialog');

    // Fill notes in Coordinator Form
    const notesInput = screen.getByPlaceholderText(/Explain coordinator rationale/i);
    fireEvent.change(notesInput, { target: { value: 'Verified via CCTV feed dadar-cam-04' } });

    const submitBtn = screen.getByText(/Save Annotation/i);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.submitCoordinatorCorrection).toHaveBeenCalled();
    });
  });
});
