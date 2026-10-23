import {
  Report, Incident, IncidentReportLink, EvidenceItem, Task, AuditEvent, SystemHealth
} from '../types';

const API_BASE = '/api/v1';

export async function getHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function seedDemoData(): Promise<any> {
  const res = await fetch(`${API_BASE}/seed`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to seed demo data');
  return res.json();
}

export async function listReports(status?: string, language?: string): Promise<Report[]> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (language) params.append('language', language);
  const res = await fetch(`${API_BASE}/reports?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch reports');
  return res.json();
}

export async function getReport(id: string): Promise<Report> {
  const res = await fetch(`${API_BASE}/reports/${id}`);
  if (!res.ok) throw new Error('Failed to fetch report');
  return res.json();
}

export async function submitReport(formData: FormData): Promise<Report> {
  const res = await fetch(`${API_BASE}/reports`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to submit report' }));
    throw new Error(err.detail || 'Failed to submit report');
  }
  return res.json();
}

export async function retryReport(id: string): Promise<Report> {
  const res = await fetch(`${API_BASE}/reports/${id}/retry`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to retry report processing');
  return res.json();
}

export async function listIncidents(category?: string, status?: string, priority?: string): Promise<Incident[]> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  if (status) params.append('status', status);
  if (priority) params.append('priority', priority);
  const res = await fetch(`${API_BASE}/incidents?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch incidents');
  return res.json();
}

export async function getIncidentDetail(id: string): Promise<{
  incident: Incident;
  links: IncidentReportLink[];
  evidence_items: EvidenceItem[];
  tasks: Task[];
  audit_events: AuditEvent[];
}> {
  const res = await fetch(`${API_BASE}/incidents/${id}`);
  if (!res.ok) throw new Error('Failed to fetch incident details');
  return res.json();
}

export async function updateIncident(id: string, payload: {
  title?: string;
  summary?: string;
  status?: string;
  approved_priority?: string;
  priority_override_reason?: string;
  evidence_status?: string;
}): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update incident' }));
    throw new Error(err.detail || 'Failed to update incident');
  }
  return res.json();
}

export async function confirmReportMatch(incidentId: string, reportId: string, notes?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/reports/${reportId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'confirm', reviewer_notes: notes })
  });
  if (!res.ok) throw new Error('Failed to confirm match');
  return res.json();
}

export async function rejectReportMatch(incidentId: string, reportId: string, notes?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/reports/${reportId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'reject', reviewer_notes: notes })
  });
  if (!res.ok) throw new Error('Failed to reject match');
  return res.json();
}

export async function addEvidence(incidentId: string, payload: {
  source_type: string;
  source_name: string;
  source_url?: string;
  claim_summary: string;
  verification_status: string;
  reviewer_notes?: string;
}): Promise<EvidenceItem> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/evidence`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, incident_id: incidentId, is_simulated: true })
  });
  if (!res.ok) throw new Error('Failed to add evidence');
  return res.json();
}

export async function reviewEvidence(evidenceId: string, verification_status: string, notes?: string): Promise<EvidenceItem> {
  const res = await fetch(`${API_BASE}/evidence/${evidenceId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ verification_status, reviewer_notes: notes })
  });
  if (!res.ok) throw new Error('Failed to review evidence');
  return res.json();
}

export async function listTasks(status?: string, priority?: string, incidentId?: string): Promise<Task[]> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (priority) params.append('priority', priority);
  if (incidentId) params.append('incident_id', incidentId);
  const res = await fetch(`${API_BASE}/tasks?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch tasks');
  return res.json();
}

export async function approveTask(taskId: string, assignedTo?: string): Promise<Task> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ assigned_to: assignedTo })
  });
  if (!res.ok) throw new Error('Failed to approve task');
  return res.json();
}

export async function updateTask(taskId: string, payload: {
  title?: string;
  description?: string;
  status?: string;
  priority?: string;
  assigned_to?: string;
}): Promise<Task> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to update task');
  return res.json();
}

export async function listAuditEvents(limit = 50): Promise<AuditEvent[]> {
  const res = await fetch(`${API_BASE}/audit?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch audit log');
  return res.json();
}
