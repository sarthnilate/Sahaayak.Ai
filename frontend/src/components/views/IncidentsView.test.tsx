import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { IncidentsView } from './IncidentsView';
import { AuthProvider } from '../../contexts/AuthContext';
import { Incident } from '../../types';
import * as api from '../../services/api';

vi.mock('../../services/api', () => ({
  getMe: vi.fn().mockResolvedValue({
    id: 'user-coord',
    username: 'coordinator',
    email: 'coord@sahaayak.ai',
    role: 'coordinator',
  }),
  getIncidentDetail: vi.fn(),
  getIncidentTimeline: vi.fn(),
  updateIncident: vi.fn(),
  confirmReportMatch: vi.fn(),
  rejectReportMatch: vi.fn(),
  addEvidence: vi.fn(),
  createIncident: vi.fn(),
  createIncidentFromReport: vi.fn(),
}));

// Mock GroundedMap because leaflet requires DOM dimensions and canvas
vi.mock('../GroundedMap', () => ({
  GroundedMap: () => <div data-testid="grounded-map-mock">Grounded Map Mock</div>
}));

const mockIncidents: Incident[] = [
  {
    id: 'inc-001',
    title: 'Severe Waterlogging at Dadar TT Flyover',
    summary: 'Localized flooding across junction with 3ft water',
    category: 'waterlogging',
    status: 'open',
    suggested_priority: 'critical',
    approved_priority: 'critical',
    priority_rationale: 'Submerged arterial transit corridor',
    location_name: 'Hindmata Flyover, Dadar',
    district: 'Mumbai City',
    state: 'Maharashtra',
    district_source: 'coordinator_set',
    state_source: 'coordinator_set',
    latitude: 19.0178,
    longitude: 72.8478,
    location_precision: 'exact',
    coordinate_source: 'coordinator_pinned',
    has_grounded_coordinates: true,
    evidence_status: 'corroborated',
    assigned_coordinator_id: 'user-coord',
    version: 1,
    is_simulated: false,
    created_at: '2026-10-23T10:00:00Z',
    updated_at: '2026-10-23T10:05:00Z'
  },
  {
    id: 'inc-002',
    title: 'Bandra S.V. Road Uprooted Banyan Tree',
    summary: 'Tree blocking southbound carriageway',
    category: 'tree_fall',
    status: 'investigating',
    suggested_priority: 'high',
    approved_priority: 'high',
    priority_rationale: 'Traffic stoppage on main bypass',
    location_name: 'S.V. Road, Bandra West',
    district: 'Mumbai Suburban',
    state: 'Maharashtra',
    district_source: 'reporter_stated',
    state_source: 'reporter_stated',
    latitude: 19.0596,
    longitude: 72.8295,
    location_precision: 'neighborhood',
    coordinate_source: 'coordinator_pinned',
    has_grounded_coordinates: true,
    evidence_status: 'partially_corroborated',
    assigned_coordinator_id: null,
    version: 2,
    is_simulated: false,
    created_at: '2026-10-23T09:30:00Z',
    updated_at: '2026-10-23T09:45:00Z'
  }
];

describe('IncidentsView Phase 4 Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getIncidentDetail).mockResolvedValue({
      incident: mockIncidents[0],
      links: [
        {
          id: 'link-1',
          incident_id: 'inc-001',
          report_id: 'rep-001',
          status: 'suggested',
          similarity_score: 0.92,
          match_rationale: 'Spatial proximity < 100m and waterlogging keyword overlap',
          report: {
            id: 'rep-001',
            reference_code: 'CR-101',
            original_text: 'Dadar TT has 3 feet water, bus cannot pass',
            input_language: 'en',
            processing_status: 'processed',
            extraction_source: 'gemini',
            submitted_at: '2026-10-23T09:55:00Z'
          }
        }
      ],
      evidence_items: [],
      tasks: [],
      audit_events: [],
      allowed_transitions: ['investigating', 'mitigating', 'closed']
    });

    vi.mocked(api.getIncidentTimeline).mockResolvedValue([
      {
        id: 'evt-1',
        event_type: 'audit',
        action: 'INCIDENT_CREATED',
        actor: 'coord@sahaayak.ai',
        summary: 'Incident cluster initially established with 1 report',
        timestamp: '2026-10-23T10:00:00Z'
      }
    ]);
  });

  it('renders incident list with status pills and search filter', async () => {
    render(
      <AuthProvider>
        <IncidentsView
          incidents={mockIncidents}
          onRefresh={vi.fn()}
          isLoading={false}
        />
      </AuthProvider>
    );

    expect(screen.getByText('Incident Operations Center')).toBeInTheDocument();
    expect(screen.getByText('Severe Waterlogging at Dadar TT Flyover')).toBeInTheDocument();
    expect(screen.getByText('Bandra S.V. Road Uprooted Banyan Tree')).toBeInTheDocument();
    expect(screen.getByText('All Statuses')).toBeInTheDocument();
  });

  it('filters incidents by text search query', async () => {
    render(
      <AuthProvider>
        <IncidentsView
          incidents={mockIncidents}
          onRefresh={vi.fn()}
          isLoading={false}
        />
      </AuthProvider>
    );

    const searchInput = screen.getByPlaceholderText(/search by title/i);
    fireEvent.change(searchInput, { target: { value: 'Bandra' } });

    expect(screen.getByText('Bandra S.V. Road Uprooted Banyan Tree')).toBeInTheDocument();
    expect(screen.queryByText('Severe Waterlogging at Dadar TT Flyover')).not.toBeInTheDocument();
  });

  it('displays state transition buttons and switches tabs to timeline', async () => {
    render(
      <AuthProvider>
        <IncidentsView
          incidents={mockIncidents}
          selectedIncidentId="inc-001"
          onRefresh={vi.fn()}
          isLoading={false}
        />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('TRANSITION TO INVESTIGATING')).toBeInTheDocument();
      expect(screen.getByText('TRANSITION TO CLOSED')).toBeInTheDocument();
    });

    // Switch to Audit Timeline tab
    const timelineTab = screen.getByRole('button', { name: /audit timeline/i });
    fireEvent.click(timelineTab);

    await waitFor(() => {
      expect(screen.getByText('INCIDENT_CREATED')).toBeInTheDocument();
      expect(screen.getByText(/Incident cluster initially established/)).toBeInTheDocument();
    });
  });

  it('detects concurrency conflict on status update and displays alert', async () => {
    vi.mocked(api.updateIncident).mockRejectedValueOnce(
      new Error('Concurrency conflict: expected version 1, current is 2. OPTIMISTIC_CONCURRENCY_CONFLICT')
    );

    render(
      <AuthProvider>
        <IncidentsView
          incidents={mockIncidents}
          selectedIncidentId="inc-001"
          onRefresh={vi.fn()}
          isLoading={false}
        />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('TRANSITION TO INVESTIGATING')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('TRANSITION TO INVESTIGATING'));

    await waitFor(() => {
      expect(screen.getByText(/CONCURRENCY CONFLICT DETECTED/i)).toBeInTheDocument();
      expect(screen.getByText('RELOAD LATEST VERSION')).toBeInTheDocument();
    });
  });
});
