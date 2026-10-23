import React, { useState, useEffect } from 'react';
import {
  AlertTriangle, ShieldAlert, Radio, CheckSquare, Layers, Clock, ArrowRight,
  TrendingUp, Compass, AlertOctagon, RefreshCw, GitMerge, CheckCircle2, XCircle, X
} from 'lucide-react';
import { Incident, Report, Task, IncidentReportLink, MatchCandidate } from '../../types';
import { MetricCard } from '../common/MetricCard';
import { PriorityBadge } from '../common/PriorityBadge';
import { StatusBadge } from '../common/StatusBadge';
import { EvidenceBadge } from '../common/EvidenceBadge';
import { MatchSuggestion } from '../common/MatchSuggestion';
import {
  getDuplicateSuggestions,
  confirmReportMatch,
  rejectReportMatch,
  createIncidentFromReport
} from '../../services/api';

interface Props {
  incidents: Incident[];
  reports: Report[];
  tasks: Task[];
  onNavigate: (tab: string, incidentId?: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export const DashboardView: React.FC<Props> = ({
  incidents,
  reports,
  tasks,
  onNavigate,
  onRefresh,
  isLoading
}) => {
  const [duplicateSuggestions, setDuplicateSuggestions] = useState<IncidentReportLink[]>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [reviewingSuggestion, setReviewingSuggestion] = useState<IncidentReportLink | null>(null);

  const fetchSuggestions = async () => {
    setIsLoadingSuggestions(true);
    try {
      const suggestions = await getDuplicateSuggestions();
      setDuplicateSuggestions(suggestions);
    } catch (err) {
      console.error('Failed to fetch duplicate suggestions', err);
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  useEffect(() => {
    fetchSuggestions();
  }, [reports, incidents]);

  const handleConfirmMatch = async (incidentId: string, reportId: string, notes: string) => {
    await confirmReportMatch(incidentId, reportId, notes);
    await fetchSuggestions();
    setReviewingSuggestion(null);
    onRefresh();
  };

  const handleRejectMatch = async (incidentId: string, reportId: string, notes: string) => {
    await rejectReportMatch(incidentId, reportId, notes);
    await fetchSuggestions();
    setReviewingSuggestion(null);
    onRefresh();
  };

  const handleCreateNewIncident = async (reportId: string, notes: string) => {
    await createIncidentFromReport({
      report_id: reportId,
      district_source: 'coordinator_set'
    });
    await fetchSuggestions();
    setReviewingSuggestion(null);
    onRefresh();
  };

  const buildCandidateFromLink = (link: IncidentReportLink): MatchCandidate => {
    const inc = link.incident || incidents.find(i => i.id === link.incident_id);
    const signalsFor = link.signals_json?.signals_for || [];
    const signalsAgainst = link.signals_json?.signals_against || [];
    const unknowns = link.signals_json?.unknowns || [];
    const isSameOrigin = link.signals_json?.is_same_origin || false;

    return {
      incident_id: link.incident_id,
      incident_title: inc?.title || `Incident #${link.incident_id.slice(0, 8)}`,
      incident_category: inc?.category || 'waterlogging',
      incident_location: inc?.location_name || 'Mumbai',
      incident_created_at: inc?.created_at || new Date().toISOString(),
      band: (link.match_band as any) || (link.similarity_score >= 0.65 ? 'strong' : link.similarity_score >= 0.35 ? 'possible' : 'weak'),
      score: link.similarity_score,
      rationale: link.match_rationale || 'Suggested based on deterministic baseline lexicon and spatial/temporal alignment.',
      signals_for: signalsFor,
      signals_against: signalsAgainst,
      unknowns: unknowns,
      is_same_origin: isSameOrigin,
      origin_fingerprint: link.signals_json?.origin_fingerprint,
      existing_link_status: link.status,
    };
  };

  const criticalCount = incidents.filter(i => i.approved_priority === 'critical').length;
  const pendingTasksCount = tasks.filter(t => t.status === 'suggested' || t.status === 'pending').length;
  const unreviewedReports = reports.filter(r => r.processing_status === 'needs_review').length;
  const conflictsCount = incidents.filter(i => i.evidence_status === 'conflicting_evidence').length;

  return (
    <div className="space-y-6">
      
      {/* Simulation Banner & Quick Action */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-[#151515] via-[#1E1E1E] to-[#151515] border border-[#FF2DA8]/30 p-4 sm:p-5 shadow-[0_0_20px_rgba(255,45,168,0.12)]">
        <div className="absolute top-0 right-0 w-64 h-full bg-radial from-[#FF2DA8]/10 to-transparent pointer-events-none" />
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#FF2DA8] animate-ping" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#FF2DA8]">
                OPERATIONAL DISASTER SIMULATION RUNTIME
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
              Community Crisis Inundation Dashboard
            </h2>
            <p className="text-xs sm:text-sm text-[#A7A7A7] max-w-2xl">
              Real-time multi-lingual citizen reporting, Google Gemini fact extraction, duplicate candidate linking,
              and human-approved task dispatch for heavy rainfall & waterlogging.
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => onNavigate('reports')}
              className="px-4 py-2 rounded-lg text-xs font-bold font-mono bg-[#FF2DA8] hover:bg-[#E91E93] text-white shadow-[0_0_15px_rgba(255,45,168,0.4)] transition-all flex items-center gap-2"
            >
              <Radio className="w-4 h-4" />
              SUBMIT CITIZEN REPORT
            </button>
            <button
              onClick={onRefresh}
              className="p-2 rounded-lg bg-[#151515] border border-[#282828] text-[#A7A7A7] hover:text-white transition-all"
              title="Refresh State"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Active Incidents"
          value={incidents.length}
          subtitle="Monitored hazard clusters"
          icon={<Layers className="w-5 h-5 text-[#FF2DA8]" />}
          accent="pink"
        />
        <MetricCard
          title="Critical Priority"
          value={criticalCount}
          subtitle="Arterial obstructions & depth >75cm"
          icon={<ShieldAlert className="w-5 h-5 text-[#FF5C68]" />}
          accent="red"
        />
        <MetricCard
          title="Citizen Reports"
          value={reports.length}
          subtitle={`Multi-lingual (EN/HI/MR) • ${unreviewedReports} need review`}
          icon={<Radio className="w-5 h-5 text-[#D4FF3F]" />}
          accent="chartreuse"
        />
        <MetricCard
          title="Action Tasks"
          value={tasks.length}
          subtitle={`${pendingTasksCount} awaiting coordinator action`}
          icon={<CheckSquare className="w-5 h-5 text-white" />}
          accent="neutral"
        />
      </div>

      {/* Duplicate Suggestions Awaiting Review Queue */}
      <div className="bg-[#151515] border border-amber-500/30 rounded-xl p-5 shadow-[0_0_20px_rgba(245,185,66,0.06)] space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#282828]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-950/50 border border-amber-500/30">
              <GitMerge className="w-5 h-5 text-amber-400" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-white font-mono uppercase tracking-wide">
                  Duplicate Suggestions Awaiting Review
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase bg-amber-950/80 text-amber-300 border border-amber-500/40">
                  {duplicateSuggestions.length} PENDING
                </span>
              </div>
              <p className="text-xs text-[#A7A7A7]">
                Explainable cross-lingual candidate matches (English / Hindi / Marathi) requiring human confirmation.
              </p>
            </div>
          </div>
          <button
            onClick={fetchSuggestions}
            disabled={isLoadingSuggestions}
            className="text-xs font-mono text-amber-400 hover:text-amber-300 flex items-center gap-1.5 self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingSuggestions ? 'animate-spin' : ''}`} />
            REFRESH QUEUE
          </button>
        </div>

        {duplicateSuggestions.length === 0 ? (
          <div className="p-6 text-center text-xs font-mono text-zinc-500 bg-[#0E0E10] border border-zinc-800 rounded-lg">
            No duplicate suggestions currently awaiting coordinator review. All citizen reports triaged.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {duplicateSuggestions.map((link) => {
              const rep = link.report;
              const band = link.match_band || (link.similarity_score >= 0.65 ? 'strong' : link.similarity_score >= 0.35 ? 'possible' : 'weak');
              const inc = link.incident || incidents.find(i => i.id === link.incident_id);

              return (
                <div
                  key={link.id}
                  className="bg-[#101012] border border-zinc-800 hover:border-amber-500/50 rounded-xl p-4 transition-all duration-150 space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider font-mono ${
                        band === 'strong'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                          : band === 'possible'
                          ? 'bg-amber-950 text-amber-300 border border-amber-500/40'
                          : 'bg-zinc-800 text-zinc-300 border border-zinc-700'
                      }`}>
                        {band.toUpperCase()} MATCH
                      </span>
                      <span className="text-[11px] font-mono text-zinc-400">
                        [{rep?.input_language?.toUpperCase() || 'EN'}]
                      </span>
                      {link.signals_json?.is_same_origin && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-500/30">
                          COPIED
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500">
                      #{link.report_id.slice(0, 8)}
                    </span>
                  </div>

                  <p className="text-xs text-zinc-200 line-clamp-2 italic bg-black/40 p-2 rounded border border-zinc-900">
                    "{rep?.original_text || 'Report text pending...'}"
                  </p>

                  <div className="text-xs space-y-1">
                    <div className="text-zinc-400 truncate">
                      <strong className="text-zinc-300">Target Incident:</strong> {inc?.title || `Incident #${link.incident_id.slice(0, 8)}`}
                    </div>
                    <p className="text-[11px] text-zinc-400 line-clamp-1">
                      <strong className="text-amber-400/90">Rationale:</strong> {link.match_rationale}
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-zinc-800/80">
                    <button
                      type="button"
                      onClick={() => setReviewingSuggestion(link)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold text-amber-300 bg-amber-950/60 hover:bg-amber-900/80 border border-amber-600/40 transition-colors"
                    >
                      Review Side-by-Side &rarr;
                    </button>
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleConfirmMatch(link.incident_id, link.report_id, 'Quick confirmed from dashboard queue')}
                        title="Quick Confirm"
                        className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-950/60 border border-emerald-800/40"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRejectMatch(link.incident_id, link.report_id, 'Quick rejected from dashboard queue')}
                        title="Quick Reject"
                        className="p-1.5 rounded-lg text-rose-400 hover:bg-rose-950/60 border border-rose-800/40"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Review Side-by-Side Modal */}
      {reviewingSuggestion && reviewingSuggestion.report && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md overflow-y-auto"
        >
          <div className="w-full max-w-4xl my-8">
            <div className="flex justify-end mb-2">
              <button
                onClick={() => setReviewingSuggestion(null)}
                className="p-1.5 rounded-lg bg-zinc-800 text-zinc-300 hover:text-white"
                aria-label="Close match review"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <MatchSuggestion
              report={reviewingSuggestion.report}
              candidate={buildCandidateFromLink(reviewingSuggestion)}
              onConfirm={handleConfirmMatch}
              onReject={handleRejectMatch}
              onCreateNewIncident={handleCreateNewIncident}
            />
          </div>
        </div>
      )}

      {/* Main Grid: Priority Incident Feed + Intelligence Radar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Priority Incidents Feed (2 Cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#FF2DA8]" />
              <h3 className="font-bold text-base text-white font-mono uppercase tracking-wide">
                Active Incident Clusters
              </h3>
            </div>
            <button
              onClick={() => onNavigate('incidents')}
              className="text-xs font-mono text-[#FF2DA8] hover:underline flex items-center gap-1"
            >
              VIEW ALL INCIDENTS <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            {incidents.map((incident) => (
              <div
                key={incident.id}
                onClick={() => onNavigate('incidents', incident.id)}
                className="bg-[#151515] border border-[#282828] hover:border-[#FF2DA8]/60 rounded-xl p-4 sm:p-5 transition-all duration-200 cursor-pointer group hover:bg-[#1a1a1a]"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <PriorityBadge priority={incident.approved_priority} />
                    <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-[#1E1E1E] text-[#A7A7A7] border border-[#333]">
                      {incident.category.replace('_', ' ')}
                    </span>
                    <EvidenceBadge status={incident.evidence_status} />
                  </div>
                  <span className="text-[11px] font-mono text-[#A7A7A7] flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {new Date(incident.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                <h4 className="font-bold text-base text-white group-hover:text-[#FF2DA8] transition-colors mb-1.5">
                  {incident.title}
                </h4>
                <p className="text-xs sm:text-sm text-[#A7A7A7] line-clamp-2 mb-3">
                  {incident.summary}
                </p>

                {incident.priority_rationale && (
                  <div className="p-2.5 rounded-lg bg-[#0B0B0B] border border-[#282828] text-xs font-mono text-[#D4FF3F] mb-3">
                    <span className="text-[#A7A7A7] block text-[10px] uppercase font-bold mb-0.5">
                      EXPLAINABLE AI RATIONALE:
                    </span>
                    {incident.priority_rationale}
                  </div>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-[#222] text-xs text-[#A7A7A7]">
                  <span className="font-mono text-[11px] flex items-center gap-1">
                    <Compass className="w-3.5 h-3.5 text-[#D4FF3F]" />
                    {incident.location_name}
                  </span>
                  <span className="text-xs font-semibold text-[#FF2DA8] group-hover:translate-x-1 transition-transform flex items-center gap-1 font-mono">
                    COORDINATE INCIDENT &rarr;
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Side Panel: Verification & Conflict Radar (1 Col) */}
        <div className="space-y-6">
          
          {/* Conflict & Verification Radar */}
          <div className="bg-[#151515] border border-[#282828] rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-[#FF5C68]" />
                <h3 className="font-bold text-xs font-mono text-white uppercase tracking-wider">
                  Verification & Conflict Radar
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#351316] text-[#FF5C68] border border-[#FF5C68]/30">
                ACTIVE CHECK
              </span>
            </div>

            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-[#1D1D1D] border border-[#333] space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-[#FF5C68] font-mono">Conflicting Claims</span>
                  <span className="font-mono font-bold text-white">{conflictsCount} Flagged</span>
                </div>
                <p className="text-[11px] text-[#A7A7A7]">
                  Unverified social media rumors regarding culvert breach isolated and refuted by municipal inspection.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#1D1D1D] border border-[#333] space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-[#D4FF3F] font-mono">Multi-lingual Corroboration</span>
                  <span className="font-mono font-bold text-white">3 Languages</span>
                </div>
                <p className="text-[11px] text-[#A7A7A7]">
                  Cross-lingual signal alignment: English, Hindi (हिंदी), and Marathi (मराठी) reporting Dadar inundation.
                </p>
              </div>

              <div className="p-3 rounded-lg bg-[#1D1D1D] border border-[#333] space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-[#F5B942] font-mono">Location Ambiguity</span>
                  <span className="font-mono font-bold text-white">{unreviewedReports} In Review</span>
                </div>
                <p className="text-[11px] text-[#A7A7A7]">
                  Coordinates withheld on vague landmark claims to prevent map hallucination until coordinator verifies.
                </p>
              </div>
            </div>
          </div>

          {/* Quick Pending Tasks */}
          <div className="bg-[#151515] border border-[#282828] rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <CheckSquare className="w-4 h-4 text-[#D4FF3F]" />
                <h3 className="font-bold text-xs font-mono text-white uppercase tracking-wider">
                  Pending Task Approvals
                </h3>
              </div>
              <button
                onClick={() => onNavigate('tasks')}
                className="text-[11px] font-mono text-[#D4FF3F] hover:underline"
              >
                DISPATCH ({pendingTasksCount})
              </button>
            </div>

            <div className="space-y-2.5">
              {tasks.filter(t => t.status === 'suggested' || t.status === 'pending').slice(0, 3).map(task => (
                <div key={task.id} className="p-3 rounded-lg bg-[#1D1D1D] border border-[#2E2E2E]">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-bold text-white truncate">{task.title}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-bold uppercase ${
                      task.status === 'suggested' ? 'bg-[#30240D] text-[#F5B942]' : 'bg-[#10291F] text-[#48C78E]'
                    }`}>
                      {task.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#A7A7A7] line-clamp-1">{task.description}</p>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};
