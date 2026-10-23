import React, { useState, useEffect, useMemo } from 'react';
import {
  Layers, MapPin, ShieldAlert, CheckCircle2, XCircle, AlertOctagon,
  Clock, Plus, Filter, RefreshCw, Compass, Sliders, ExternalLink,
  MessageSquare, X, AlertTriangle, ArrowRight, CheckSquare, Search,
  ChevronRight, AlertCircle, FileText, UserCheck, ShieldCheck
} from 'lucide-react';
import { Incident, IncidentReportLink, EvidenceItem, Task, AuditEvent, TimelineEvent } from '../../types';
import {
  getIncidentDetail, updateIncident, confirmReportMatch,
  rejectReportMatch, addEvidence, getIncidentTimeline, createIncident
} from '../../services/api';
import { GroundedMap } from '../GroundedMap';
import { PriorityBadge } from '../common/PriorityBadge';
import { EvidenceBadge } from '../common/EvidenceBadge';
import { StatusBadge } from '../common/StatusBadge';
import { IncidentTimeline } from '../common/IncidentTimeline';
import { ConfirmActionDialog } from '../common/ConfirmActionDialog';
import { EvidenceTimeline } from '../common/EvidenceTimeline';
import { useAuth } from '../../contexts/AuthContext';

interface Props {
  incidents: Incident[];
  selectedIncidentId?: string | null;
  onRefresh: () => void;
  isLoading: boolean;
  onNavigateToReport?: (reportId: string) => void;
}

export const IncidentsView: React.FC<Props> = ({
  incidents,
  selectedIncidentId: initialSelectedId,
  onRefresh,
  isLoading,
  onNavigateToReport
}) => {
  const { hasRole } = useAuth();
  const isCoordinator = hasRole('coordinator') || hasRole('admin');

  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(
    initialSelectedId || (incidents.length > 0 ? incidents[0].id : null)
  );

  const [detailData, setDetailData] = useState<{
    incident: Incident;
    links: IncidentReportLink[];
    evidence_items: EvidenceItem[];
    tasks: Task[];
    audit_events: AuditEvent[];
    allowed_transitions?: string[];
  } | null>(null);

  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isLoadingTimeline, setIsLoadingTimeline] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'reports' | 'timeline' | 'tasks'>('overview');

  // Modals & State Controls
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overridePriority, setOverridePriority] = useState<string>('high');
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [isUpdating, setIsUpdating] = useState(false);

  // Close Incident Modal
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [closeReason, setCloseReason] = useState('');
  const [transitionError, setTransitionError] = useState<string | null>(null);

  // Link Action Dialog State (Confirm/Reject with notes)
  const [linkActionDialog, setLinkActionDialog] = useState<{
    type: 'confirm' | 'reject';
    reportId: string;
    reportSnippet: string;
  } | null>(null);

  // Optimistic Concurrency Conflict State
  const [concurrencyConflict, setConcurrencyConflict] = useState<string | null>(null);

  // New Evidence Modal
  const [showAddEvidence, setShowAddEvidence] = useState(false);
  const [evSource, setEvSource] = useState('MCGM Disaster Control Telemetry');
  const [evClaim, setEvClaim] = useState('');
  const [evStatus, setEvStatus] = useState('corroborating');

  // New Incident Modal
  const [showCreateIncidentModal, setShowCreateIncidentModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newSummary, setNewSummary] = useState('');
  const [newCategory, setNewCategory] = useState('waterlogging');
  const [newPriority, setNewPriority] = useState('medium');
  const [newLocationName, setNewLocationName] = useState('');
  const [newDistrict, setNewDistrict] = useState('Mumbai City');
  const [newState, setNewState] = useState('Maharashtra');
  const [newLatitude, setNewLatitude] = useState('');
  const [newLongitude, setNewLongitude] = useState('');
  const [newPrecision, setNewPrecision] = useState('exact');
  const [newCoordSource, setNewCoordSource] = useState('coordinator_pinned');
  const [isCreatingIncident, setIsCreatingIncident] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [districtFilter, setDistrictFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'created_desc' | 'created_asc' | 'priority' | 'updated_desc'>('created_desc');

  useEffect(() => {
    if (initialSelectedId) {
      setSelectedIncidentId(initialSelectedId);
    } else if (!selectedIncidentId && incidents.length > 0) {
      setSelectedIncidentId(incidents[0].id);
    }
  }, [initialSelectedId, incidents, selectedIncidentId]);

  useEffect(() => {
    if (selectedIncidentId) {
      loadDetail(selectedIncidentId);
    } else {
      setDetailData(null);
    }
  }, [selectedIncidentId]);

  const loadDetail = async (id: string) => {
    setIsLoadingDetail(true);
    setTransitionError(null);
    setConcurrencyConflict(null);
    try {
      const data = await getIncidentDetail(id);
      setDetailData(data);
      setOverridePriority(data.incident.approved_priority);
      loadTimeline(id);
    } catch (e: any) {
      console.error('Failed to load incident detail', e);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const loadTimeline = async (id: string) => {
    setIsLoadingTimeline(true);
    try {
      const events = await getIncidentTimeline(id);
      setTimelineEvents(events);
    } catch (e) {
      console.error('Failed to load timeline', e);
    } finally {
      setIsLoadingTimeline(false);
    }
  };

  // Status Machine Transition Handler
  const handleStatusTransition = async (targetStatus: string, reason?: string) => {
    if (!selectedIncidentId || !detailData) return;
    setTransitionError(null);
    setConcurrencyConflict(null);
    setIsUpdating(true);

    try {
      const updated = await updateIncident(selectedIncidentId, {
        status: targetStatus,
        close_reason: reason,
        version: detailData.incident.version
      });

      setShowCloseModal(false);
      setCloseReason('');
      await loadDetail(selectedIncidentId);
      onRefresh();
    } catch (err: any) {
      console.error('Status transition error:', err);
      if (err.message && err.message.includes('Concurrency conflict') || err.message?.includes('OPTIMISTIC_CONCURRENCY_CONFLICT') || err.message?.includes('409')) {
        setConcurrencyConflict('This incident was modified by another coordinator. Please reload the latest state to view recent changes before modifying.');
      } else {
        setTransitionError(err.message || 'Failed to transition incident status.');
      }
    } finally {
      setIsUpdating(false);
    }
  };

  const handleConfirmMatch = async (reportId: string, notes?: string) => {
    if (!selectedIncidentId) return;
    try {
      await confirmReportMatch(selectedIncidentId, reportId, notes || 'Confirmed by coordinator');
      setLinkActionDialog(null);
      await loadDetail(selectedIncidentId);
      onRefresh();
    } catch (err: any) {
      alert(`Failed to confirm link: ${err.message}`);
    }
  };

  const handleRejectMatch = async (reportId: string, notes?: string) => {
    if (!selectedIncidentId) return;
    try {
      await rejectReportMatch(selectedIncidentId, reportId, notes || 'Rejected non-matching claim');
      setLinkActionDialog(null);
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
    setConcurrencyConflict(null);
    try {
      await updateIncident(selectedIncidentId, {
        approved_priority: overridePriority,
        priority_override_reason: overrideReason,
        version: detailData?.incident.version
      });
      setShowOverrideModal(false);
      setOverrideReason('');
      await loadDetail(selectedIncidentId);
      onRefresh();
    } catch (err: any) {
      if (err.message && (err.message.includes('Concurrency conflict') || err.message?.includes('409'))) {
        setConcurrencyConflict('This incident was modified by another coordinator. Please reload to see the latest version.');
      } else {
        alert(`Override failed: ${err.message}`);
      }
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCreateEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIncidentId || !evClaim.trim()) return;
    try {
      await addEvidence(selectedIncidentId, {
        source_name: evSource,
        claim_summary: evClaim,
        evidence_type: 'manual_attachment',
        assessment: 'unassessed',
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

  const handleCreateIncidentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    if (!newTitle.trim() || !newSummary.trim() || !newLocationName.trim()) {
      setCreateError('Title, summary, and location are required.');
      return;
    }

    const payload: any = {
      title: newTitle,
      summary: newSummary,
      category: newCategory,
      suggested_priority: newPriority,
      location_name: newLocationName,
      district: newDistrict,
      state: newState,
      district_source: 'coordinator_set',
      state_source: 'coordinator_set'
    };

    if (newLatitude && newLongitude) {
      const lat = parseFloat(newLatitude);
      const lng = parseFloat(newLongitude);
      if (isNaN(lat) || lat < -90 || lat > 90) {
        setCreateError('Latitude must be a valid number between -90 and 90.');
        return;
      }
      if (isNaN(lng) || lng < -180 || lng > 180) {
        setCreateError('Longitude must be a valid number between -180 and 180.');
        return;
      }
      payload.latitude = lat;
      payload.longitude = lng;
      payload.location_precision = newPrecision;
      payload.coordinate_source = newCoordSource;
      payload.has_grounded_coordinates = true;
    }

    setIsCreatingIncident(true);
    try {
      const created = await createIncident(payload);
      setShowCreateIncidentModal(false);
      // Reset form
      setNewTitle('');
      setNewSummary('');
      setNewLocationName('');
      setNewLatitude('');
      setNewLongitude('');
      onRefresh();
      setSelectedIncidentId(created.id);
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create incident');
    } finally {
      setIsCreatingIncident(false);
    }
  };

  // Filtered & Sorted Incidents
  const filteredIncidents = useMemo(() => {
    return incidents.filter(i => {
      if (statusFilter !== 'all' && i.status !== statusFilter) return false;
      if (categoryFilter !== 'all' && i.category !== categoryFilter) return false;
      if (priorityFilter !== 'all' && i.approved_priority !== priorityFilter) return false;
      if (districtFilter !== 'all' && i.district !== districtFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = i.title.toLowerCase().includes(q);
        const matchesLoc = i.location_name.toLowerCase().includes(q);
        const matchesSummary = i.summary.toLowerCase().includes(q);
        if (!matchesTitle && !matchesLoc && !matchesSummary) return false;
      }
      return true;
    }).sort((a, b) => {
      if (sortBy === 'created_desc') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      if (sortBy === 'created_asc') return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      if (sortBy === 'updated_desc') return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      if (sortBy === 'priority') {
        const pWeights: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };
        return (pWeights[b.approved_priority] || 0) - (pWeights[a.approved_priority] || 0);
      }
      return 0;
    });
  }, [incidents, statusFilter, categoryFilter, priorityFilter, districtFilter, searchQuery, sortBy]);

  // Open tasks check for close block
  const openTasksCount = useMemo(() => {
    if (!detailData || !detailData.tasks) return 0;
    return detailData.tasks.filter(t => ['suggested', 'pending', 'in_progress'].includes(t.status)).length;
  }, [detailData]);

  const allowedTransitions = useMemo(() => {
    if (detailData?.allowed_transitions) return detailData.allowed_transitions;
    if (!detailData) return [];
    const status = detailData.incident.status;
    const rules: Record<string, string[]> = {
      open: ['investigating', 'mitigating', 'closed'],
      investigating: ['mitigating', 'resolved', 'open'],
      mitigating: ['resolved', 'investigating'],
      resolved: ['closed', 'investigating'],
      closed: []
    };
    return rules[status] || [];
  }, [detailData]);

  return (
    <div className="space-y-6">

      {/* Filter & Incident Management Bar */}
      <div className="bg-[#151515] border border-[#282828] rounded-2xl p-4 sm:p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#1E1E1E] border border-[#333] flex items-center justify-center text-[#FF2DA8]">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-white">
                Incident Operations Center
              </h2>
              <p className="text-xs text-[#A7A7A7] font-mono">
                {incidents.length} total verified incidents across monitoring wards
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCreateIncidentModal(true)}
              className="px-4 py-2 rounded-xl text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white shadow-[0_0_15px_rgba(255,45,168,0.3)] transition-all flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              <span>NEW INCIDENT</span>
            </button>
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2.5 rounded-xl bg-[#1E1E1E] hover:bg-[#282828] text-white border border-[#333] transition-colors"
              title="Refresh Incident Data"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-[#FF2DA8]' : ''}`} />
            </button>
          </div>
        </div>

        {/* Status Pills Bar */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs font-mono">
          {[
            { id: 'all', label: 'All Statuses', count: incidents.length },
            { id: 'open', label: 'Open', count: incidents.filter(i => i.status === 'open').length, color: 'text-[#3FA9FF]' },
            { id: 'investigating', label: 'Investigating', count: incidents.filter(i => i.status === 'investigating').length, color: 'text-[#F5B942]' },
            { id: 'mitigating', label: 'Mitigating', count: incidents.filter(i => i.status === 'mitigating').length, color: 'text-[#FF2DA8]' },
            { id: 'resolved', label: 'Resolved', count: incidents.filter(i => i.status === 'resolved').length, color: 'text-[#48C78E]' },
            { id: 'closed', label: 'Closed', count: incidents.filter(i => i.status === 'closed').length, color: 'text-[#777]' },
          ].map((pill) => {
            const isActive = statusFilter === pill.id;
            return (
              <button
                key={pill.id}
                onClick={() => setStatusFilter(pill.id)}
                className={`px-3 py-1.5 rounded-lg border flex items-center gap-2 whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-[#1E1E1E] border-[#FF2DA8] text-white shadow-[0_0_10px_rgba(255,45,168,0.2)]'
                    : 'bg-[#0B0B0B] border-[#242424] text-[#A7A7A7] hover:border-[#383838]'
                }`}
              >
                <span>{pill.label}</span>
                <span className={`px-1.5 py-0.2 rounded bg-[#151515] text-[10px] ${pill.color || 'text-white'}`}>
                  {pill.count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search & Granular Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-2 border-t border-[#222]">
          {/* Search Box */}
          <div className="relative lg:col-span-2">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-[#777]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by title, landmark, or description..."
              className="w-full pl-9 pr-3 py-2 bg-[#0B0B0B] border border-[#282828] rounded-xl text-xs text-white placeholder-[#555] font-mono outline-none focus:border-[#FF2DA8]"
            />
          </div>

          {/* Category Dropdown */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-[#0B0B0B] border border-[#282828] rounded-xl px-3 py-2 text-xs font-mono text-[#A7A7A7] outline-none"
          >
            <option value="all">Category: All</option>
            <option value="waterlogging">Waterlogging</option>
            <option value="tree_fall">Tree Fall</option>
            <option value="landslide">Landslide</option>
            <option value="structural_damage">Structural Damage</option>
            <option value="power_outage">Power Outage</option>
          </select>

          {/* Priority Dropdown */}
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-[#0B0B0B] border border-[#282828] rounded-xl px-3 py-2 text-xs font-mono text-[#A7A7A7] outline-none"
          >
            <option value="all">Priority: All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          {/* Sort Selector */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="bg-[#0B0B0B] border border-[#282828] rounded-xl px-3 py-2 text-xs font-mono text-[#A7A7A7] outline-none"
          >
            <option value="created_desc">Sort: Newest First</option>
            <option value="created_asc">Sort: Oldest First</option>
            <option value="priority">Sort: Priority High-Low</option>
            <option value="updated_desc">Sort: Recently Updated</option>
          </select>
        </div>
      </div>

      {/* Top Split: Grounded Map (Left) & Incident Selector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Grounded Map View (7 Cols) */}
        <div className="lg:col-span-7 h-[440px]">
          <GroundedMap
            incidents={filteredIncidents}
            selectedIncidentId={selectedIncidentId}
            onSelectIncident={(id) => setSelectedIncidentId(id)}
          />
        </div>

        {/* Incident Selector List (5 Cols) */}
        <div className="lg:col-span-5 bg-[#151515] border border-[#282828] rounded-2xl p-4 flex flex-col h-[440px]">
          <div className="flex items-center justify-between pb-3 border-b border-[#282828] mb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#FF2DA8]" />
              <h3 className="font-bold text-xs font-mono uppercase text-white tracking-wider">
                Active Incidents ({filteredIncidents.length})
              </h3>
            </div>
            <span className="text-[11px] font-mono text-[#777]">
              Click card to inspect
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {filteredIncidents.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-xs font-mono text-[#777]">
                <Filter className="w-6 h-6 mb-2 opacity-50" />
                <p>No incidents match the active filters.</p>
              </div>
            ) : (
              filteredIncidents.map((inc) => {
                const isSelected = inc.id === selectedIncidentId;
                return (
                  <div
                    key={inc.id}
                    onClick={() => setSelectedIncidentId(inc.id)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-[#1E1E1E] border-[#FF2DA8] shadow-[0_0_15px_rgba(255,45,168,0.25)]'
                        : 'bg-[#0B0B0B] border-[#242424] hover:border-[#383838]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <PriorityBadge priority={inc.approved_priority} />
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#181818] text-[#D4FF3F] border border-[#333]">
                          {inc.category}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[10px] font-mono text-[#A7A7A7]">
                        <span>v{inc.version}</span>
                        <span>•</span>
                        <span>{inc.has_grounded_coordinates ? '📍 Pin' : '⚠️ Approx'}</span>
                      </div>
                    </div>

                    <h4 className="text-xs font-bold text-white line-clamp-1 mb-1">{inc.title}</h4>
                    <p className="text-[11px] text-[#888] line-clamp-1 mb-2 font-mono">
                      {inc.summary}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-[#A7A7A7] font-mono pt-1.5 border-t border-[#1C1C1C]">
                      <span className="truncate max-w-[60%] flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-[#FF2DA8]" />
                        {inc.location_name}
                      </span>
                      <StatusBadge status={inc.status} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Incident Deep-Dive Coordinator Workspace */}
      {detailData && (
        <div className="bg-[#151515] border border-[#282828] rounded-2xl p-5 sm:p-6 space-y-6">

          {/* Optimistic Concurrency Conflict Alert */}
          {concurrencyConflict && (
            <div className="p-4 rounded-xl bg-[#351024] border border-[#FF2DA8] text-white flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-[0_0_20px_rgba(255,45,168,0.3)]">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-[#FF2DA8] shrink-0" />
                <div className="text-xs font-mono">
                  <strong className="text-[#FF2DA8] block">CONCURRENCY CONFLICT DETECTED</strong>
                  <span>{concurrencyConflict}</span>
                </div>
              </div>
              <button
                onClick={() => loadDetail(detailData.incident.id)}
                className="px-4 py-2 rounded-lg text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white whitespace-nowrap"
              >
                RELOAD LATEST VERSION
              </button>
            </div>
          )}

          {/* Transition Error Message */}
          {transitionError && (
            <div className="p-4 rounded-xl bg-[#351316] border border-[#FF5C68]/50 text-xs font-mono text-[#FF5C68] flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{transitionError}</span>
              </div>
              <button
                onClick={() => setTransitionError(null)}
                className="text-[#FF5C68] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Incident Banner & State Transition Controls */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5 pb-6 border-b border-[#282828]">
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <PriorityBadge priority={detailData.incident.approved_priority} />
                <span className="text-xs font-mono uppercase px-2.5 py-0.5 rounded bg-[#1E1E1E] text-[#D4FF3F] border border-[#333]">
                  {detailData.incident.category}
                </span>
                <EvidenceBadge status={detailData.incident.evidence_status} />
                <StatusBadge status={detailData.incident.status} />
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#0B0B0B] border border-[#282828] text-[#A7A7A7]">
                  Revision v{detailData.incident.version}
                </span>
              </div>

              <h2 className="text-2xl font-black text-white">{detailData.incident.title}</h2>

              <div className="flex items-center gap-3 text-xs text-[#A7A7A7] font-mono flex-wrap">
                <span className="flex items-center gap-1.5 text-white">
                  <MapPin className="w-3.5 h-3.5 text-[#FF2DA8]" />
                  {detailData.incident.location_name}
                </span>
                {detailData.incident.district && (
                  <span className="px-2 py-0.5 rounded bg-[#0B0B0B] border border-[#222]">
                    District: <strong className="text-white">{detailData.incident.district}</strong> ({detailData.incident.district_source || 'stated'})
                  </span>
                )}
                {detailData.incident.has_grounded_coordinates && (
                  <span className="text-[#D4FF3F] flex items-center gap-1">
                    <Compass className="w-3.5 h-3.5" />
                    [{detailData.incident.latitude?.toFixed(4)}, {detailData.incident.longitude?.toFixed(4)}] ({detailData.incident.location_precision || 'pinned'})
                  </span>
                )}
              </div>
            </div>

            {/* State Machine Transition Actions Bar */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
              {allowedTransitions.map((nextStatus) => {
                const isClose = nextStatus === 'closed';
                return (
                  <button
                    key={nextStatus}
                    onClick={() => {
                      if (isClose) {
                        setShowCloseModal(true);
                      } else {
                        handleStatusTransition(nextStatus);
                      }
                    }}
                    disabled={isUpdating}
                    className={`px-3.5 py-2 rounded-xl text-xs font-mono font-bold flex items-center justify-center gap-1.5 transition-all ${
                      isClose
                        ? 'bg-[#351316] hover:bg-[#4d1c20] text-[#FF5C68] border border-[#FF5C68]/40'
                        : 'bg-[#1E1E1E] hover:bg-[#282828] text-white border border-[#444] hover:border-[#D4FF3F]'
                    }`}
                  >
                    <ArrowRight className="w-3.5 h-3.5 text-[#FF2DA8]" />
                    <span>TRANSITION TO {nextStatus.toUpperCase()}</span>
                  </button>
                );
              })}

              <button
                onClick={() => setShowOverrideModal(true)}
                className="px-3.5 py-2 rounded-xl text-xs font-mono font-bold bg-[#1E1E1E] hover:bg-[#282828] text-white border border-[#444] hover:border-[#FF2DA8] transition-all flex items-center justify-center gap-1.5"
              >
                <Sliders className="w-3.5 h-3.5 text-[#FF2DA8]" />
                <span>OVERRIDE PRIORITY</span>
              </button>

              <button
                onClick={() => setShowAddEvidence(true)}
                className="px-3.5 py-2 rounded-xl text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white shadow-[0_0_12px_rgba(255,45,168,0.3)] transition-all flex items-center justify-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>ATTACH EVIDENCE</span>
              </button>
            </div>
          </div>

          {/* Close Block Warning if tasks open */}
          {openTasksCount > 0 && detailData.incident.status !== 'closed' && (
            <div className="p-3.5 rounded-xl bg-[#241C12] border border-[#F5B942]/40 text-[#F5B942] text-xs font-mono flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-[#F5B942]" />
              <span>
                Safety policy (D-001): <strong>{openTasksCount} operational task(s)</strong> are currently open. Complete or cancel tasks before closing this incident.
              </span>
            </div>
          )}

          {/* Close reason banner if incident closed */}
          {detailData.incident.status === 'closed' && detailData.incident.close_reason && (
            <div className="p-4 rounded-xl bg-[#101010] border border-[#333] text-xs font-mono space-y-1">
              <span className="text-[#A7A7A7] block text-[10px]">INCIDENT CLOSED • RESOLUTION SUMMARY:</span>
              <p className="text-[#48C78E] font-medium">"{detailData.incident.close_reason}"</p>
            </div>
          )}

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
              <div className="mt-2 p-2.5 rounded bg-[#351024] border border-[#FF2DA8]/30 text-[#FF2DA8] text-[11px]">
                <strong>Coordinator Override Justification:</strong> {detailData.incident.priority_override_reason}
              </div>
            )}
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-[#282828] pb-1 text-xs font-mono">
            {[
              { id: 'overview', label: `Candidate Reports (${detailData.links.length})`, icon: <MessageSquare className="w-3.5 h-3.5" /> },
              { id: 'timeline', label: `Audit Timeline (${timelineEvents.length})`, icon: <Clock className="w-3.5 h-3.5" /> },
              { id: 'tasks', label: `Evidence & Tasks (${detailData.evidence_items.length + detailData.tasks.length})`, icon: <CheckSquare className="w-3.5 h-3.5" /> },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2 rounded-t-lg font-bold flex items-center gap-2 transition-all ${
                  activeTab === tab.id
                    ? 'bg-[#1E1E1E] text-white border-t-2 border-[#FF2DA8]'
                    : 'text-[#A7A7A7] hover:text-white'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Tab 1: Linked Reports */}
          {activeTab === 'overview' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-[#A7A7A7]">
                  Multi-signal matching: Spatial Proximity, Named Landmarks & Incident Lexicon
                </span>
              </div>

              {detailData.links.length === 0 ? (
                <div className="p-8 text-center text-xs font-mono text-[#777] bg-[#0B0B0B] border border-[#282828] rounded-xl">
                  No candidate reports currently associated with this incident.
                </div>
              ) : (
                <div className="space-y-3">
                  {detailData.links.map((link) => {
                    const report = link.report;
                    const isSuggested = link.status === 'suggested';
                    return (
                      <div
                        key={link.id}
                        className={`p-4 rounded-xl border transition-all ${
                          isSuggested
                            ? 'bg-[#191919] border-[#D4FF3F]/40 shadow-[0_0_12px_rgba(212,255,63,0.1)]'
                            : 'bg-[#0B0B0B] border-[#282828]'
                        }`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2.5">
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

                            {/* Phase 5 Band Badge (Never raw probabilities) */}
                            {(() => {
                              const band = link.match_band || (link.similarity_score >= 0.65 ? 'strong' : link.similarity_score >= 0.35 ? 'possible' : 'weak');
                              return (
                                <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                                  band === 'strong'
                                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                                    : band === 'possible'
                                    ? 'bg-amber-950 text-amber-300 border border-amber-500/40'
                                    : 'bg-zinc-800 text-zinc-300 border border-zinc-700'
                                }`}>
                                  BAND: {band.toUpperCase()}
                                </span>
                              );
                            })()}

                            <span className="text-xs font-mono text-[#A7A7A7]">
                              Lang: [{report?.input_language.toUpperCase() || 'EN'}]
                            </span>
                            {report?.reference_code && (
                              <span className="text-xs font-mono text-[#FF2DA8]">
                                #{report.reference_code}
                              </span>
                            )}
                          </div>

                          {/* Coordinator Confirm/Reject Actions */}
                          {isSuggested && (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setLinkActionDialog({
                                  type: 'confirm',
                                  reportId: link.report_id,
                                  reportSnippet: report?.original_text || 'Report'
                                })}
                                className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[#10291F] hover:bg-[#1a4031] text-[#48C78E] border border-[#48C78E]/40 flex items-center gap-1.5 transition-colors"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                CONFIRM MATCH
                              </button>
                              <button
                                onClick={() => setLinkActionDialog({
                                  type: 'reject',
                                  reportId: link.report_id,
                                  reportSnippet: report?.original_text || 'Report'
                                })}
                                className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[#351316] hover:bg-[#4d1c20] text-[#FF5C68] border border-[#FF5C68]/40 flex items-center gap-1.5 transition-colors"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                                REJECT
                              </button>
                            </div>
                          )}
                        </div>

                        <p className="text-xs text-white italic mb-2.5 leading-relaxed bg-black/40 p-2.5 rounded border border-zinc-900">
                          "{report?.original_text || 'Report text unavailable'}"
                        </p>

                        {/* Review History / Coordinator Audit Trail */}
                        {link.reviewed_by && (
                          <div className={`p-2.5 rounded-lg text-[11px] font-mono mb-2 border ${
                            link.status === 'confirmed'
                              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/40'
                              : 'bg-rose-950/40 text-rose-300 border-rose-800/40'
                          }`}>
                            <div className="flex items-center justify-between font-bold">
                              <span>REVIEWED BY: {link.reviewed_by}</span>
                              {link.reviewed_at && (
                                <span className="text-[10px] text-zinc-400">
                                  {new Date(link.reviewed_at).toLocaleString()}
                                </span>
                              )}
                            </div>
                            {link.reviewer_notes && (
                              <p className="text-zinc-300 mt-1 italic">
                                Notes: "{link.reviewer_notes}"
                              </p>
                            )}
                          </div>
                        )}

                        <div className="p-2.5 rounded-lg bg-[#111] text-[11px] font-mono text-[#A7A7A7] border border-[#222]">
                          <span className="text-[#D4FF3F] font-bold">MATCH RATIONALE: </span>
                          {link.match_rationale}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Chronological Audit Timeline */}
          {activeTab === 'timeline' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2">
                <span className="text-xs font-mono text-[#A7A7A7]">
                  Immutable audit trail of state transitions, coordinator reviews, and report linkages.
                </span>
                <button
                  onClick={() => loadTimeline(detailData.incident.id)}
                  className="px-3 py-1 rounded bg-[#1E1E1E] hover:bg-[#282828] text-xs font-mono text-white flex items-center gap-1.5 border border-[#333]"
                >
                  <RefreshCw className={`w-3 h-3 ${isLoadingTimeline ? 'animate-spin text-[#FF2DA8]' : ''}`} />
                  REFRESH
                </button>
              </div>

              <IncidentTimeline events={timelineEvents} isLoading={isLoadingTimeline} />
            </div>
          )}

          {/* Tab 3: Evidence & Tasks */}
          {activeTab === 'tasks' && (
            <div className="space-y-6">
              {/* Evidence Section — Phase 6 EvidenceTimeline */}
              <div className="space-y-3">
                <EvidenceTimeline
                  incidentId={selectedIncidentId!}
                  isCoordinator={isCoordinator}
                />
              </div>

              {/* Tasks Section */}
              <div className="space-y-3 pt-4 border-t border-[#282828]">
                <h4 className="text-xs font-mono font-bold uppercase text-white flex items-center gap-2">
                  <CheckSquare className="w-4 h-4 text-[#D4FF3F]" />
                  Associated Operational Tasks ({detailData.tasks.length})
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {detailData.tasks.map((task) => (
                    <div key={task.id} className="p-3.5 rounded-xl bg-[#0B0B0B] border border-[#282828] space-y-2">
                      <div className="flex items-center justify-between">
                        <h5 className="text-xs font-bold text-white">{task.title}</h5>
                        <StatusBadge status={task.status} />
                      </div>
                      <p className="text-xs text-[#A7A7A7] leading-relaxed">{task.description}</p>
                      <div className="flex items-center justify-between text-[10px] font-mono text-[#777] pt-1">
                        <span>Assignee: <strong className="text-white">{task.assigned_to || 'Unassigned'}</strong></span>
                        <PriorityBadge priority={task.priority} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </div>
      )}

      {/* Close Incident Modal */}
      {showCloseModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#151515] border border-[#FF5C68] rounded-2xl w-full max-w-md p-6 space-y-4 shadow-[0_0_30px_rgba(255,92,104,0.25)]">
            <div className="flex items-center justify-between pb-2 border-b border-[#282828]">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-[#FF5C68]" />
                <h3 className="text-sm font-bold text-white font-mono uppercase">
                  Close Incident Confirmation
                </h3>
              </div>
              <button onClick={() => setShowCloseModal(false)} className="text-[#A7A7A7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {openTasksCount > 0 ? (
              <div className="p-4 rounded-xl bg-[#351316] border border-[#FF5C68]/50 text-xs font-mono text-[#FF5C68] space-y-2">
                <p className="font-bold">Cannot close incident!</p>
                <p>
                  Safety Policy D-001 blocks closing incidents while operational tasks remain open. There are currently <strong>{openTasksCount} task(s)</strong> requiring completion or cancellation first.
                </p>
                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => setShowCloseModal(false)}
                    className="px-4 py-1.5 rounded-lg text-xs font-mono font-bold bg-[#FF5C68] text-white"
                  >
                    UNDERSTOOD
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={(e) => {
                e.preventDefault();
                handleStatusTransition('closed', closeReason);
              }} className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-[#A7A7A7] mb-1">
                    MANDATORY RESOLUTION / CLOSING JUSTIFICATION *
                  </label>
                  <textarea
                    value={closeReason}
                    onChange={(e) => setCloseReason(e.target.value)}
                    placeholder="Describe how the hazard was mitigated or confirmed resolved (e.g., Floodwaters receded, MCGM pump squad completed de-watering)..."
                    rows={3}
                    required
                    className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF5C68] rounded-xl p-3 text-xs text-white placeholder-[#555] font-mono outline-none"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCloseModal(false)}
                    className="px-4 py-2 rounded-xl text-xs font-mono bg-[#222] text-[#A7A7A7] hover:bg-[#2A2A2A]"
                  >
                    CANCEL
                  </button>
                  <button
                    type="submit"
                    disabled={isUpdating || !closeReason.trim()}
                    className="px-5 py-2 rounded-xl text-xs font-mono font-bold bg-[#FF5C68] hover:bg-[#ff3b4b] text-white disabled:opacity-50"
                  >
                    {isUpdating ? 'CLOSING INCIDENT...' : 'CONFIRM & CLOSE'}
                  </button>
                </div>
              </form>
            )}
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
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2.5 text-xs text-white font-mono outline-none"
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
                  className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-xl p-3 text-xs text-white placeholder-[#555] font-mono outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowOverrideModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-mono bg-[#222] text-[#A7A7A7]"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={isUpdating}
                  className="px-5 py-2 rounded-xl text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white"
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
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2.5 text-xs text-white font-mono"
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
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2.5 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-[#A7A7A7] mb-1">VERIFICATION STATUS</label>
                <select
                  value={evStatus}
                  onChange={(e) => setEvStatus(e.target.value)}
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2.5 text-xs text-white font-mono"
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
                  className="px-4 py-2 rounded-xl text-xs font-mono bg-[#222] text-[#A7A7A7]"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl text-xs font-mono font-bold bg-[#FF2DA8] text-white"
                >
                  SAVE EVIDENCE
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manual Create Incident Modal */}
      {showCreateIncidentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-[#151515] border border-[#FF2DA8] rounded-2xl w-full max-w-lg p-6 space-y-4 my-8 shadow-[0_0_40px_rgba(255,45,168,0.25)]">
            <div className="flex items-center justify-between pb-2 border-b border-[#282828]">
              <div className="flex items-center gap-2">
                <Plus className="w-5 h-5 text-[#FF2DA8]" />
                <h3 className="text-sm font-bold text-white font-mono uppercase">
                  Create New Incident Cluster
                </h3>
              </div>
              <button onClick={() => setShowCreateIncidentModal(false)} className="text-[#A7A7A7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {createError && (
              <div className="p-3 rounded-xl bg-[#351316] border border-[#FF5C68]/50 text-xs font-mono text-[#FF5C68]">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateIncidentSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-[#A7A7A7] mb-1">INCIDENT TITLE *</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Severe Inundation at Kurla Station West"
                  required
                  className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-xl p-2.5 text-xs text-white font-mono outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-[#A7A7A7] mb-1">SUMMARY *</label>
                <textarea
                  value={newSummary}
                  onChange={(e) => setNewSummary(e.target.value)}
                  placeholder="Operational overview of situation, affected infrastructure, and hazards..."
                  rows={2}
                  required
                  className="w-full bg-[#0B0B0B] border border-[#282828] focus:border-[#FF2DA8] rounded-xl p-2.5 text-xs text-white font-mono outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-[#A7A7A7] mb-1">CATEGORY</label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2 text-xs text-white font-mono"
                  >
                    <option value="waterlogging">Waterlogging</option>
                    <option value="tree_fall">Tree Fall</option>
                    <option value="landslide">Landslide</option>
                    <option value="structural_damage">Structural Damage</option>
                    <option value="power_outage">Power Outage</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-mono text-[#A7A7A7] mb-1">SUGGESTED PRIORITY</label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}
                    className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2 text-xs text-white font-mono"
                  >
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-[#A7A7A7] mb-1">LOCATION DESCRIPTION *</label>
                <input
                  type="text"
                  value={newLocationName}
                  onChange={(e) => setNewLocationName(e.target.value)}
                  placeholder="e.g. S.V. Road, Bandra West near Lucky Restaurant"
                  required
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2.5 text-xs text-white font-mono"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-mono text-[#A7A7A7] mb-1">DISTRICT</label>
                  <input
                    type="text"
                    value={newDistrict}
                    onChange={(e) => setNewDistrict(e.target.value)}
                    className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono text-[#A7A7A7] mb-1">STATE</label>
                  <input
                    type="text"
                    value={newState}
                    onChange={(e) => setNewState(e.target.value)}
                    className="w-full bg-[#0B0B0B] border border-[#282828] rounded-xl p-2 text-xs text-white font-mono"
                  />
                </div>
              </div>

              {/* Coordinates with precision and source requirements */}
              <div className="p-3 rounded-xl bg-[#0B0B0B] border border-[#222] space-y-2.5">
                <span className="text-[11px] font-mono text-[#A7A7A7] block font-bold">
                  OPTIONAL GROUNDED COORDINATES (Safety Validated)
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={newLatitude}
                    onChange={(e) => setNewLatitude(e.target.value)}
                    placeholder="Latitude (e.g. 19.0760)"
                    className="w-full bg-[#121212] border border-[#282828] rounded-lg p-2 text-xs text-white font-mono"
                  />
                  <input
                    type="text"
                    value={newLongitude}
                    onChange={(e) => setNewLongitude(e.target.value)}
                    placeholder="Longitude (e.g. 72.8777)"
                    className="w-full bg-[#121212] border border-[#282828] rounded-lg p-2 text-xs text-white font-mono"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={newPrecision}
                    onChange={(e) => setNewPrecision(e.target.value)}
                    className="w-full bg-[#121212] border border-[#282828] rounded-lg p-2 text-[11px] text-white font-mono"
                  >
                    <option value="exact">Precision: Exact Landmark</option>
                    <option value="neighborhood">Precision: Neighborhood / Ward</option>
                    <option value="district">Precision: District Level</option>
                  </select>
                  <select
                    value={newCoordSource}
                    onChange={(e) => setNewCoordSource(e.target.value)}
                    className="w-full bg-[#121212] border border-[#282828] rounded-lg p-2 text-[11px] text-white font-mono"
                  >
                    <option value="coordinator_pinned">Source: coordinator_pinned</option>
                    <option value="simulated_seed">Source: simulated_seed</option>
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateIncidentModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-mono bg-[#222] text-[#A7A7A7]"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={isCreatingIncident}
                  className="px-5 py-2 rounded-xl text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white disabled:opacity-50"
                >
                  {isCreatingIncident ? 'CREATING...' : 'CREATE INCIDENT'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Link Confirm / Reject Action Dialog */}
      {linkActionDialog && (
        <ConfirmActionDialog
          isOpen={true}
          title={linkActionDialog.type === 'confirm' ? 'Confirm Incident Link' : 'Reject Match Suggestion'}
          description={
            linkActionDialog.type === 'confirm'
              ? `Confirm Report #${linkActionDialog.reportId.slice(0, 8)} as a linked corroborating report for this incident? The report will be linked without altering original citizen text.`
              : `Reject candidate match for Report #${linkActionDialog.reportId.slice(0, 8)}? This suggestion will not be re-suggested unless new evidence or updates are provided.`
          }
          actionType={linkActionDialog.type}
          confirmLabel={linkActionDialog.type === 'confirm' ? 'Confirm Link' : 'Reject Suggestion'}
          placeholderNotes={
            linkActionDialog.type === 'confirm'
              ? 'e.g. Verified multi-lingual match refers to same Hindmata junction flooding.'
              : 'e.g. Separate localized puddle on eastern slipway, not central underpass.'
          }
          onConfirm={(notes) => {
            if (linkActionDialog.type === 'confirm') {
              handleConfirmMatch(linkActionDialog.reportId, notes);
            } else {
              handleRejectMatch(linkActionDialog.reportId, notes);
            }
          }}
          onCancel={() => setLinkActionDialog(null)}
        />
      )}

    </div>
  );
};
