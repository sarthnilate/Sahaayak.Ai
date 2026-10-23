export interface ExtractedDetails {
  hazard_type: string;
  severity: string;
  water_depth_cm?: number | null;
  location_name?: string | null;
  approximate_lat?: number | null;
  approximate_lng?: number | null;
  has_grounded_coordinates: boolean;
  affected_infrastructure: string[];
  urgent_needs: string[];
  casualties_flag: boolean;
  confidence_score: number;
  sentiment_urgency: string;
  language_detected: string;
  summary: string;
  _provider_error?: string;
  _fallback_to_demo?: boolean;
}

export interface Report {
  id: string;
  original_text: string;
  media_path?: string | null;
  media_type?: string | null;
  input_language: string;
  reporter_name?: string | null;
  reporter_contact?: string | null;
  location_claim?: string | null;
  coordinates_lat?: number | null;
  coordinates_lng?: number | null;
  processing_status: 'received' | 'processing' | 'processed' | 'needs_review' | 'failed';
  error_message?: string | null;
  extraction_source: string;
  extracted_json?: ExtractedDetails | null;
  submitted_at: string;
  processed_at?: string | null;
}

export interface Incident {
  id: string;
  title: string;
  summary: string;
  category: string;
  status: 'open' | 'investigating' | 'mitigating' | 'resolved' | 'closed';
  suggested_priority: 'critical' | 'high' | 'medium' | 'low';
  approved_priority: 'critical' | 'high' | 'medium' | 'low';
  priority_rationale?: string | null;
  priority_override_reason?: string | null;
  location_name: string;
  latitude?: number | null;
  longitude?: number | null;
  has_grounded_coordinates: boolean;
  evidence_status: 'unverified' | 'partially_corroborated' | 'conflicting_evidence' | 'corroborated';
  is_simulated: boolean;
  created_at: string;
  updated_at: string;
}

export interface IncidentReportLink {
  id: string;
  incident_id: string;
  report_id: string;
  status: 'suggested' | 'confirmed' | 'rejected';
  similarity_score: number;
  match_rationale?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  report?: Report;
}

export interface EvidenceItem {
  id: string;
  incident_id: string;
  report_id?: string | null;
  source_type: string;
  source_name: string;
  source_url?: string | null;
  is_simulated: boolean;
  claim_summary: string;
  verification_status: 'corroborating' | 'conflicting' | 'unverified' | 'disproven';
  reviewer_notes?: string | null;
  created_at: string;
}

export interface Task {
  id: string;
  incident_id: string;
  title: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'suggested' | 'pending' | 'in_progress' | 'completed' | 'cancelled';
  assigned_to?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: Record<string, any> | null;
  timestamp: string;
}

export interface SystemHealth {
  status: string;
  version: string;
  environment: string;
  ai_provider: string;
  database: string;
  is_demo_mode: boolean;
}
