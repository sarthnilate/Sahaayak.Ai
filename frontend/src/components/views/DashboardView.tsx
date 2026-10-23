import React from 'react';
import {
  AlertTriangle, ShieldAlert, Radio, CheckSquare, Layers, Clock, ArrowRight,
  TrendingUp, Compass, AlertOctagon, RefreshCw
} from 'lucide-react';
import { Incident, Report, Task } from '../../types';
import { MetricCard } from '../common/MetricCard';
import { PriorityBadge } from '../common/PriorityBadge';
import { StatusBadge } from '../common/StatusBadge';
import { EvidenceBadge } from '../common/EvidenceBadge';

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
