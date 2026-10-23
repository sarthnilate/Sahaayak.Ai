import React, { useState, useEffect } from 'react';
import {
  Layers, MapPin, ShieldAlert, CheckCircle2, XCircle, AlertOctagon,
  Clock, Plus, Filter, RefreshCw, Compass, Sliders, ExternalLink, MessageSquare, X
} from 'lucide-react';
import { Incident, IncidentReportLink, EvidenceItem, Task, AuditEvent } from '../../types';
import {
  getIncidentDetail, updateIncident, confirmReportMatch,
  rejectReportMatch, addEvidence, reviewEvidence
} from '../../services/api';
import { GroundedMap } from '../GroundedMap';
import { PriorityBadge } from '../common/PriorityBadge';
import { EvidenceBadge } from '../common/EvidenceBadge';
import { StatusBadge } from '../common/StatusBadge';

interface Props {
  incidents: Incident[];
  selectedIncidentId?: string | null;
  onRefresh: () => void;
  isLoading: boolean;
}

export const IncidentsView: React.FC<Props> = ({
  incidents,
  selectedIncidentId: initialSelectedId,
  onRefresh,
  isLoading
}) => {
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(
    initialSelectedId || (incidents.length > 0 ? incidents[0].id : null)
  );

  const [detailData, setDetailData] = useState<{
    incident: Incident;
    links: IncidentReportLink[];
    evidence_items: EvidenceItem[];
    tasks: Task[];
    audit_events: AuditEvent[];
  } | null>(null);

  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overridePriority, setOverridePriority] = useState<string>('high');
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [isUpdating, setIsUpdating] = useState(false);

  // New Evidence Modal
  const [showAddEvidence, setShowAddEvidence] = useState(false);
  const [evSource, setEvSource] = useState('MCGM Disaster Control Telemetry');
  const [evClaim, setEvClaim] = useState('');
  const [evStatus, setEvStatus] = useState('corroborating');

  // Filter
  const [categoryFilter, setCategoryFilter] = useState('all');

  useEffect(() => {
    if (initialSelectedId) {
      setSelectedIncidentId(initialSelectedId);
    }
  }, [initialSelectedId]);

  useEffect(() => {
    if (selectedIncidentId) {
      loadDetail(selectedIncidentId);
    }
  }, [selectedIncidentId]);

  const loadDetail = async (id: string) => {
    setIsLoadingDetail(true);
    try {
      const data = await getIncidentDetail(id);
      setDetailData(data);
      setOverridePriority(data.incident.approved_priority);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleConfirmMatch = async (reportId: string) => {
    if (!selectedIncidentId) return;
    try {
      await confirmReportMatch(selectedIncidentId, reportId, 'Confirmed by coordinator');
      await loadDetail(selectedIncidentId);
      onRefresh();
    } catch (err: any) {
      alert(`Failed to confirm link: ${err.message}`);
    }
  };

  const handleRejectMatch = async (reportId: string) => {
    if (!selectedIncidentId) return;
    try {
      await rejectReportMatch(selectedIncidentId, reportId, 'Rejected non-matching claim');
      await loadDetail(selectedIncidentId);
      onRefresh();
    } catch (err: any) {
      alert(`Failed to reject link: ${err.message}`);
    }
  };

  const handlePriorityOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIncidentId || !overrideReason.trim()) {
      alert('Please provide an override rationale as required by safety policy.');
      return;
    }
    setIsUpdating(true);
    try {
      await updateIncident(selectedIncidentId, {
        approved_priority: overridePriority,
        priority_override_reason: overrideReason
      });
      setShowOverrideModal(false);
      setOverrideReason('');
      await loadDetail(selectedIncidentId);
      onRefresh();
    } catch (err: any) {
      alert(`Override failed: ${err.message}`);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCreateEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIncidentId || !evClaim.trim()) return;
    try {
      await addEvidence(selectedIncidentId, {
        source_type: 'official_bulletin',
        source_name: evSource,
        claim_summary: evClaim,
        verification_status: evStatus,
        reviewer_notes: 'Logged via incident coordinator portal'
      });
      setShowAddEvidence(false);
      setEvClaim('');
      await loadDetail(selectedIncidentId);
      onRefresh();
    } catch (err: any) {
      alert(`Failed to add evidence: ${err.message}`);
    }
  };

  const filteredIncidents = incidents.filter(i => {
    if (categoryFilter !== 'all' && i.category !== categoryFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      
      {/* Top Split: Grounded Map (Left) & Incident Selector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Grounded Map View (7 Cols) */}
        <div className="lg:col-span-7 h-[420px]">
          <GroundedMap
            incidents={incidents}
            selectedIncidentId={selectedIncidentId}
            onSelectIncident={(id) => setSelectedIncidentId(id)}
          />
        </div>

        {/* Incident Selector List (5 Cols) */}
        <div className="lg:col-span-5 bg-[#151515] border border-[#282828] rounded-xl p-4 flex flex-col h-[420px]">
          <div className="flex items-center justify-between pb-3 border-b border-[#282828] mb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#FF2DA8]" />
              <h3 className="font-bold text-xs font-mono uppercase text-white tracking-wider">
                Incident Clusters ({filteredIncidents.length})
              </h3>
            </div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-[#0B0B0B] border border-[#282828] rounded px-2 py-1 text-[11px] font-mono text-[#A7A7A7] outline-none"
            >
              <option value="all">All Categories</option>
              <option value="waterlogging">Waterlogging</option>
              <option value="tree_fall">Tree Fall</option>
            </select>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {filteredIncidents.map((inc) => {
              const isSelected = inc.id === selectedIncidentId;
              return (
                <div
                  key={inc.id}
                  onClick={() => setSelectedIncidentId(inc.id)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#1E1E1E] border-[#FF2DA8] shadow-[0_0_12px_rgba(255,45,168,0.25)]'
                      : 'bg-[#0B0B0B] border-[#242424] hover:border-[#383838]'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <PriorityBadge priority={inc.approved_priority} />
                    <span className="text-[10px] font-mono text-[#A7A7A7]">
                      {inc.has_grounded_coordinates ? '📍 Grounded' : '⚠️ Approx'}
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-white line-clamp-1 mb-1">{inc.title}</h4>
                  <div className="flex items-center justify-between text-[11px] text-[#A7A7A7] font-mono">
                    <span className="truncate">{inc.location_name}</span>
                    <span className="text-[#FF2DA8] shrink-0">{inc.status.toUpperCase()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

      </div>

      {/* Incident Deep-Dive Coordinator Workspace */}
      {detailData && (
        <div className="bg-[#151515] border border-[#282828] rounded-xl p-5 sm:p-6 space-y-6">
          
          {/* Incident Banner & Priority Controls */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-[#282828]">
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <PriorityBadge priority={detailData.incident.approved_priority} />
                <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-[#1E1E1E] text-[#D4FF3F] border border-[#333]">
                  {detailData.incident.category}
                </span>
                <EvidenceBadge status={detailData.incident.evidence_status} />
                <span className="text-xs font-mono text-[#A7A7A7]">
                  STATUS: <strong className="text-white">{detailData.incident.status.toUpperCase()}</strong>
                </span>
              </div>
              <h2 className="text-xl font-black text-white">{detailData.incident.title}</h2>
              <p className="text-xs text-[#A7A7A7] font-mono flex items-center gap-2">
                <Compass className="w-3.5 h-3.5 text-[#FF2DA8]" />
                {detailData.incident.location_name}
                {detailData.incident.has_grounded_coordinates && (
                  <span className="text-[#D4FF3F]">
                    [{detailData.incident.latitude?.toFixed(4)}, {detailData.incident.longitude?.toFixed(4)}]
                  </span>
                )}
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                onClick={() => setShowOverrideModal(true)}
                className="px-3.5 py-2 rounded-lg text-xs font-mono font-bold bg-[#1E1E1E] hover:bg-[#282828] text-white border border-[#444] hover:border-[#FF2DA8] transition-all flex items-center gap-1.5"
              >
                <Sliders className="w-3.5 h-3.5 text-[#FF2DA8]" />
                <span>OVERRIDE PRIORITY</span>
              </button>
              <button
                onClick={() => setShowAddEvidence(true)}
                className="px-3.5 py-2 rounded-lg text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white shadow-[0_0_12px_rgba(255,45,168,0.3)] transition-all flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>ATTACH EVIDENCE</span>
              </button>
            </div>
          </div>

          {/* Explainable AI Priority Card */}
          <div className="p-4 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between text-[#A7A7A7] text-[11px]">
              <span className="text-[#FF2DA8] uppercase font-bold flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5" />
                Explainable Priority Reasoning & Safeguards
              </span>
              <span>AI Suggested: <strong className="text-white">{detailData.incident.suggested_priority.toUpperCase()}</strong></span>
            </div>
            <p className="text-white text-xs leading-relaxed">
              {detailData.incident.priority_rationale || 'Deterministic hazard depth and critical transit arterial impact factors.'}
            </p>
            {detailData.incident.priority_override_reason && (
              <div className="mt-2 p-2 rounded bg-[#351024] border border-[#FF2DA8]/30 text-[#FF2DA8] text-[11px]">
                <strong>Coordinator Override Justification:</strong> {detailData.incident.priority_override_reason}
              </div>
            )}
          </div>

          {/* Linked Reports & Candidate Duplicate Review */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-[#D4FF3F]" />
                <h3 className="font-bold text-xs font-mono uppercase text-white tracking-wide">
                  Candidate Associated Reports ({detailData.links.length})
                </h3>
              </div>
              <span className="text-[11px] font-mono text-[#A7A7A7]">
                Multi-signal matching (Spatial, Landmark & Keyword Overlap)
              </span>
            </div>

            <div className="space-y-2.5">
              {detailData.links.map((link) => {
                const report = link.report;
                const isSuggested = link.status === 'suggested';
                return (
                  <div
                    key={link.id}
                    className={`p-3.5 rounded-xl border transition-all ${
                      isSuggested
                        ? 'bg-[#191919] border-[#D4FF3F]/40 shadow-[0_0_10px_rgba(212,255,63,0.1)]'
                        : 'bg-[#0B0B0B] border-[#282828]'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                          link.status === 'confirmed'
                            ? 'bg-[#10291F] text-[#48C78E] border border-[#48C78E]/30'
                            : link.status === 'rejected'
                            ? 'bg-[#351316] text-[#FF5C68] border border-[#FF5C68]/30'
                            : 'bg-[#252B12] text-[#D4FF3F] border border-[#D4FF3F]/30 animate-pulse'
                        }`}>
                          LINK: {link.status.toUpperCase()}
                        </span>
                        <span className="text-xs font-mono text-white">
                          Match Score: <strong>{(link.similarity_score * 100).toFixed(0)}%</strong>
                        </span>
                        <span className="text-xs font-mono text-[#A7A7A7]">
                          Lang: [{report?.input_language.toUpperCase() || 'EN'}]
                        </span>
                      </div>

                      {/* Coordinator Confirm/Reject Actions */}
                      {isSuggested && (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleConfirmMatch(link.report_id)}
                            className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-[#10291F] hover:bg-[#1a4031] text-[#48C78E] border border-[#48C78E]/40 flex items-center gap-1"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            CONFIRM MATCH
                          </button>
                          <button
                            onClick={() => handleRejectMatch(link.report_id)}
                            className="px-2.5 py-1 rounded text-xs font-mono font-bold bg-[#351316] hover:bg-[#4d1c20] text-[#FF5C68] border border-[#FF5C68]/40 flex items-center gap-1"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            REJECT
                          </button>
                        </div>
                      )}
                    </div>

                    <p className="text-xs text-white italic mb-1.5">
                      "{report?.original_text || 'Report text unavailable'}"
                    </p>

                    <div className="p-2 rounded bg-[#111] text-[11px] font-mono text-[#A7A7A7] border border-[#222]">
                      <span className="text-[#D4FF3F] font-bold">MATCH RATIONALE: </span>
                      {link.match_rationale}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Evidence Verification Items */}
          <div className="space-y-3 pt-3 border-t border-[#282828]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-[#FF5C68]" />
                <h3 className="font-bold text-xs font-mono uppercase text-white tracking-wide">
                  Evidence Items & Corroboration State ({detailData.evidence_items.length})
                </h3>
              </div>
              <span className="text-[11px] font-mono text-[#A7A7A7]">
                Clear distinction between Telemetry vs Forwarded Claims
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {detailData.evidence_items.map((ev) => (
                <div key={ev.id} className="p-3.5 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-white">{ev.source_name}</span>
                    <EvidenceBadge status={ev.verification_status} />
                  </div>
                  <p className="text-xs text-[#E5E5E5]">{ev.claim_summary}</p>
                  {ev.reviewer_notes && (
                    <div className="text-[11px] font-mono text-[#A7A7A7] bg-[#151515] p-2 rounded border border-[#222]">
                      <strong className="text-[#FF2DA8]">Audit note:</strong> {ev.reviewer_notes}
                    </div>
                  )}
                  <div className="text-[10px] font-mono text-[#888] flex items-center justify-between pt-1">
                    <span>{ev.is_simulated ? 'SIMULATED DATA' : 'LIVE FEED'}</span>
                    <span>{new Date(ev.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

      {/* Override Priority Modal */}
      {showOverrideModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#151515] border border-[#FF2DA8] rounded-2xl w-full max-w-md p-6 space-y-4 shadow-[0_0_30px_rgba(255,45,168,0.3)]">
            <div className="flex items-center justify-between pb-2 border-b border-[#282828]">
              <h3 className="text-sm font-bold text-white font-mono uppercase">
                Override AI Priority Assessment
              </h3>
              <button onClick={() => setShowOverrideModal(false)} className="text-[#A7A7A7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handlePriorityOverride} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-[#A7A7A7] mb-1">
                  NEW APPROVED PRIORITY
                </label>
                <select
                  value={overridePriority}
                  onChange={(e) => setOverridePriority(e.target.value)}
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg p-2.5 text-xs text-white font-mono outline-none"
                >
                  <option value="critical">CRITICAL (Life/Safety hazard)</option>
                  <option value="high">HIGH (Arterial block / Major disruption)</option>
                  <option value="medium">MEDIUM (Localized ponding)</option>
                  <option value="low">LOW (Minor advisory)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-[#A7A7A7] mb-1">
                  MANDATORY COORDINATOR JUSTIFICATION *
                </label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Explain operational reason for overriding AI recommendation..."
                  rows={3}
                  required
                  className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-lg p-2.5 text-xs text-white placeholder-[#555] outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowOverrideModal(false)}
                  className="px-4 py-2 rounded-lg text-xs font-mono bg-[#222] text-[#A7A7A7]"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={isUpdating}
                  className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white"
                >
                  {isUpdating ? 'RECORDING OVERRIDE...' : 'COMMIT OVERRIDE'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Evidence Modal */}
      {showAddEvidence && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#151515] border border-[#282828] rounded-2xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#282828]">
              <h3 className="text-sm font-bold text-white font-mono uppercase">
                Attach Corroborating Evidence
              </h3>
              <button onClick={() => setShowAddEvidence(false)} className="text-[#A7A7A7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateEvidence} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-[#A7A7A7] mb-1">SOURCE IDENTIFIER</label>
                <input
                  type="text"
                  value={evSource}
                  onChange={(e) => setEvSource(e.target.value)}
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg p-2 text-xs text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-[#A7A7A7] mb-1">EVIDENCE CLAIM / FINDING</label>
                <textarea
                  value={evClaim}
                  onChange={(e) => setEvClaim(e.target.value)}
                  placeholder="e.g. Ward drainage inspection completed; culvert running at 100%..."
                  rows={2}
                  required
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg p-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-[#A7A7A7] mb-1">VERIFICATION STATUS</label>
                <select
                  value={evStatus}
                  onChange={(e) => setEvStatus(e.target.value)}
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg p-2 text-xs text-white font-mono"
                >
                  <option value="corroborating">Corroborating Claim</option>
                  <option value="conflicting">Conflicting / Refuting Claim</option>
                  <option value="unverified">Unverified Rumor</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddEvidence(false)}
                  className="px-4 py-2 rounded-lg text-xs font-mono bg-[#222] text-[#A7A7A7]"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-[#FF2DA8] text-white"
                >
                  SAVE EVIDENCE
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
