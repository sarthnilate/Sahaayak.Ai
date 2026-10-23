import {
  Report, Incident, IncidentReportLink, EvidenceItem, Task, AuditEvent, SystemHealth, User, PaginatedReports,
  PaginatedIncidents, TimelineEvent, ReportMatchesResponse, IncidentEvidenceListResponse
} from '../types';

const API_BASE = '/api/v1';

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: any;
    request_id: string;
  };
}

export class ApiError extends Error {
  code: string;
  requestId: string;
  details?: any;

  constructor(code: string, message: string, requestId: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

// Extract double-submit CSRF token from browser cookies
function getCsrfToken(): string {
  if (typeof document !== 'undefined') {
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
  }
  return 'sahaayak_csrf_token_verified';
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorJson = await res.json().catch(() => null);
    if (errorJson && errorJson.error) {
      throw new ApiError(
        errorJson.error.code,
        errorJson.error.message,
        errorJson.error.request_id || res.headers.get('X-Request-ID') || 'unknown',
        errorJson.error.details
      );
    }
    const message = (errorJson && errorJson.detail) || `HTTP ${res.status}: ${res.statusText}`;
    throw new ApiError('HTTP_ERROR', message, res.headers.get('X-Request-ID') || 'unknown');
  }
  return res.json();
}

function getDefaultHeaders(isJson = true): HeadersInit {
  const headers: Record<string, string> = {
    'X-CSRF-Token': getCsrfToken()
  };
  if (isJson) {
    headers['Content-Type'] = 'application/json';
  }
  return headers;
}

// ==============================================================================
// Authentication & Profile Services
// ==============================================================================

export async function loginUser(email: string, password: string): Promise<{ user: User; message: string; csrf_token: string }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify({ email, password })
  });
  return handleResponse(res);
}

export async function registerUser(email: string, username: string, password: string, full_name?: string): Promise<{ user: User; message: string; csrf_token: string }> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify({ email, username, password, full_name })
  });
  return handleResponse(res);
}

export async function logoutUser(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse(res);
}

export async function getMe(): Promise<User> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<User>(res);
}

// ==============================================================================
// System & Demo Seed Services
// ==============================================================================

export async function getHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/health`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<SystemHealth>(res);
}

export async function getReadiness(): Promise<{
  status: string;
  database: string;
  dialect: string;
  live_sources_enabled: boolean;
}> {
  const res = await fetch(`${API_BASE}/ready`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse(res);
}

export async function seedDemoData(): Promise<any> {
  const res = await fetch(`${API_BASE}/seed`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse(res);
}

// ==============================================================================
// Reports & Intake Services
// ==============================================================================

export async function listReports(
  status?: string,
  language?: string,
  page = 1,
  limit = 20,
  search?: string
): Promise<PaginatedReports> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (language) params.append('language', language);
  if (search) params.append('search', search);
  params.append('page', String(page));
  params.append('limit', String(limit));

  const res = await fetch(`${API_BASE}/reports?${params.toString()}`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<PaginatedReports>(res);
}

export async function getReport(id: string): Promise<Report> {
  const res = await fetch(`${API_BASE}/reports/${id}`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<Report>(res);
}

export async function lookupReportByReference(referenceCode: string): Promise<Report> {
  const res = await fetch(`${API_BASE}/reports/lookup/${encodeURIComponent(referenceCode)}`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<Report>(res);
}

export function getReportImageUrl(id: string): string {
  return `${API_BASE}/reports/${id}/image`;
}

export async function submitReport(formData: FormData): Promise<Report> {
  const res = await fetch(`${API_BASE}/reports`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'X-CSRF-Token': getCsrfToken()
    },
    body: formData,
  });
  return handleResponse<Report>(res);
}

export async function retryReport(id: string): Promise<Report> {
  const res = await fetch(`${API_BASE}/reports/${id}/retry`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<Report>(res);
}

export async function processReport(id: string): Promise<Report> {
  const res = await fetch(`${API_BASE}/reports/${id}/process`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<Report>(res);
}

export async function submitCoordinatorCorrection(
  id: string,
  payload: {
    corrected_category?: string | null;
    corrected_severity?: string | null;
    corrected_location?: string | null;
    correction_notes: string;
  }
): Promise<Report> {
  const res = await fetch(`${API_BASE}/reports/${id}/correction`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify(payload)
  });
  return handleResponse<Report>(res);
}

export async function getAiStatus(): Promise<{
  mode: string;
  provider: string;
  model: string;
  api_key_configured: boolean;
}> {
  const res = await fetch(`${API_BASE}/settings/ai-status`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse(res);
}

// ==============================================================================
// Incidents & Evidence Services
// ==============================================================================

export async function listIncidents(
  filterOrCategory?: string | {
    category?: string;
    status?: string;
    priority?: string;
    district?: string;
    search?: string;
    page?: number;
    limit?: number;
    sort_by?: string;
    sort_desc?: boolean;
  },
  status?: string,
  priority?: string
): Promise<PaginatedIncidents> {
  const urlParams = new URLSearchParams();
  if (typeof filterOrCategory === 'object' && filterOrCategory !== null) {
    if (filterOrCategory.category) urlParams.append('category', filterOrCategory.category);
    if (filterOrCategory.status) urlParams.append('status', filterOrCategory.status);
    if (filterOrCategory.priority) urlParams.append('priority', filterOrCategory.priority);
    if (filterOrCategory.district) urlParams.append('district', filterOrCategory.district);
    if (filterOrCategory.search) urlParams.append('search', filterOrCategory.search);
    if (filterOrCategory.page) urlParams.append('page', String(filterOrCategory.page));
    if (filterOrCategory.limit) urlParams.append('limit', String(filterOrCategory.limit));
    if (filterOrCategory.sort_by) urlParams.append('sort_by', filterOrCategory.sort_by);
    if (filterOrCategory.sort_desc !== undefined) urlParams.append('sort_desc', String(filterOrCategory.sort_desc));
  } else {
    if (filterOrCategory) urlParams.append('category', filterOrCategory);
    if (status) urlParams.append('status', status);
    if (priority) urlParams.append('priority', priority);
  }
  const res = await fetch(`${API_BASE}/incidents?${urlParams.toString()}`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  const data = await handleResponse<any>(res);
  if (Array.isArray(data)) {
    return { items: data, total: data.length, page: 1, limit: data.length, pages: 1 };
  }
  return data as PaginatedIncidents;
}

export async function getIncidentDetail(id: string): Promise<{
  incident: Incident;
  links: IncidentReportLink[];
  evidence_items: EvidenceItem[];
  tasks: Task[];
  audit_events: AuditEvent[];
  allowed_transitions?: string[];
}> {
  const res = await fetch(`${API_BASE}/incidents/${id}`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse(res);
}

export async function getIncidentTimeline(id: string): Promise<TimelineEvent[]> {
  const res = await fetch(`${API_BASE}/incidents/${id}/timeline`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<TimelineEvent[]>(res);
}

export async function createIncident(payload: {
  title: string;
  summary: string;
  category?: string;
  suggested_priority?: string;
  location_name: string;
  district?: string;
  state?: string;
  district_source?: string;
  state_source?: string;
  latitude?: number;
  longitude?: number;
  location_precision?: string;
  coordinate_source?: string;
  has_grounded_coordinates?: boolean;
}): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify(payload)
  });
  return handleResponse<Incident>(res);
}

export async function createIncidentFromReport(payload: {
  report_id: string;
  title?: string;
  category?: string;
  suggested_priority?: string;
  location_name?: string;
  district?: string;
  state?: string;
  district_source?: string;
  state_source?: string;
}): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents/from-report`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify(payload)
  });
  return handleResponse<Incident>(res);
}

export async function updateIncident(id: string, payload: {
  title?: string;
  summary?: string;
  status?: string;
  close_reason?: string;
  approved_priority?: string;
  priority_override_reason?: string;
  evidence_status?: string;
  location_name?: string;
  district?: string;
  state?: string;
  latitude?: number;
  longitude?: number;
  location_precision?: string;
  coordinate_source?: string;
  has_grounded_coordinates?: boolean;
  version?: number;
}): Promise<Incident> {
  const res = await fetch(`${API_BASE}/incidents/${id}`, {
    method: 'PATCH',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify(payload)
  });
  return handleResponse<Incident>(res);
}

export async function confirmReportMatch(incidentId: string, reportId: string, notes?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/reports/${reportId}/confirm`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify({ action: 'confirm', reviewer_notes: notes })
  });
  return handleResponse(res);
}

export async function rejectReportMatch(incidentId: string, reportId: string, notes?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/reports/${reportId}/reject`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify({ action: 'reject', reviewer_notes: notes })
  });
  return handleResponse(res);
}

export async function getReportMatches(reportId: string): Promise<ReportMatchesResponse> {
  const res = await fetch(`${API_BASE}/reports/${reportId}/matches`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<ReportMatchesResponse>(res);
}

export async function getDuplicateSuggestions(): Promise<IncidentReportLink[]> {
  const res = await fetch(`${API_BASE}/reports/duplicate-suggestions`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<IncidentReportLink[]>(res);
}

export async function getIncidentEvidence(incidentId: string): Promise<IncidentEvidenceListResponse> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/evidence`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<IncidentEvidenceListResponse>(res);
}

export async function addEvidence(incidentId: string, payload: {
  source_name: string;
  claim_summary: string;
  source_url?: string | null;
  source_description?: string | null;
  evidence_type?: string;
  assessment?: string;
  excerpt?: string | null;
  reviewer_notes?: string | null;
}): Promise<EvidenceItem> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/evidence`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify(payload)
  });
  return handleResponse<EvidenceItem>(res);
}

export async function reviewEvidence(evidenceId: string, payload: {
  reviewer_notes: string;
  assessment?: string;
  verification_status?: string;
}): Promise<EvidenceItem> {
  const res = await fetch(`${API_BASE}/evidence/${evidenceId}/review`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify(payload)
  });
  return handleResponse<EvidenceItem>(res);
}

export async function overrideIncidentEvidenceStatus(incidentId: string, payload: {
  status: string;
  reviewer_notes: string;
}): Promise<IncidentEvidenceListResponse> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}/evidence-status`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify(payload)
  });
  return handleResponse<IncidentEvidenceListResponse>(res);
}

export async function listTasks(status?: string, priority?: string, incidentId?: string): Promise<Task[]> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (priority) params.append('priority', priority);
  if (incidentId) params.append('incident_id', incidentId);
  const res = await fetch(`${API_BASE}/tasks?${params.toString()}`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<Task[]>(res);
}

export async function approveTask(taskId: string, assignedTo?: string): Promise<Task> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/approve`, {
    method: 'POST',
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify({ assigned_to: assignedTo })
  });
  return handleResponse<Task>(res);
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
    credentials: 'include',
    headers: getDefaultHeaders(true),
    body: JSON.stringify(payload)
  });
  return handleResponse<Task>(res);
}

export async function listAuditEvents(limit = 50): Promise<AuditEvent[]> {
  const res = await fetch(`${API_BASE}/audit?limit=${limit}`, {
    credentials: 'include',
    headers: getDefaultHeaders(false)
  });
  return handleResponse<AuditEvent[]>(res);
}
