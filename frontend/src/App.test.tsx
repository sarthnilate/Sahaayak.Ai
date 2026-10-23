import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import App from './App';

describe('Sahaayak AI Shell & Application', () => {
  beforeEach(() => {
    // Mock global fetch
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: 'usr-coord-001',
            username: 'coordinator',
            email: 'coordinator@sahaayak.ai',
            role: 'coordinator',
            full_name: 'Emergency Response Coordinator',
            created_at: new Date().toISOString()
          }),
          headers: new Headers({ 'X-Request-ID': 'test-req-auth' })
        });
      }
      if (url.includes('/health')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'healthy',
            version: '1.0.0',
            environment: 'test',
            ai_provider: 'Deterministic Demo Adapter',
            database: 'connected',
            is_demo_mode: true
          }),
          headers: new Headers({ 'X-Request-ID': 'test-req-123' })
        });
      }
      if (url.includes('/ready')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'ready',
            database: 'connected',
            dialect: 'sqlite',
            live_sources_enabled: false
          }),
          headers: new Headers({ 'X-Request-ID': 'test-req-456' })
        });
      }
      // Return empty list for incidents, reports, tasks by default
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
        headers: new Headers()
      });
    }));
  });

  it('renders the Sahaayak AI header with brand name', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByTestId('brand-title')).toHaveTextContent('SAHAAYAK.AI');
      expect(screen.getByText('CRISIS OPS')).toBeInTheDocument();
    });
  });

  it('displays active AI provider and demo indicator', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/DEMO/i)).toBeInTheDocument();
    });
  });

  it('passes automated accessibility audit with vitest-axe', async () => {
    const { container } = render(<App />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
