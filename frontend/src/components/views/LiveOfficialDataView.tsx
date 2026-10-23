import React, { useEffect, useState } from 'react';
import { 
  Landmark, 
  RefreshCw, 
  AlertCircle, 
  Clock, 
  ExternalLink, 
  ShieldAlert, 
  CheckCircle2, 
  Search, 
  Filter,
  Radio,
  FileCode,
  MapPin
} from 'lucide-react';
import { ProvenanceBadge, ProvenanceLegend } from '../common/ProvenanceBadge';

interface SourceStatus {
  source_id: string;
  display_name: string;
  status: 'live_ok' | 'live_empty' | 'stale_cache' | 'not_configured' | 'blocked' | 'error';
  last_fetched_at?: string;
  item_count: number;
  http_status?: number;
  error_message?: string;
  details?: Record<string, any>;
}

interface LiveAlert {
  id: string;
  source_id: string;
  external_identifier: string;
  headline: string;
  event: string;
  severity: string;
  urgency?: string;
  certainty?: string;
  area_description: string;
  language: string;
  sender?: string;
  sent_at?: string;
  effective_at?: string;
  expires_at?: string;
  source_url?: string;
  centroid?: string;
  is_synthetic: boolean;
  is_expired: boolean;
  retrieved_at: string;
}

export const LiveOfficialDataView: React.FC = () => {
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [alerts, setAlerts] = useState<LiveAlert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [selectedAlertForCap, setSelectedAlertForCap] = useState<LiveAlert | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const fetchStatusAndAlerts = async () => {
    setIsLoading(true);
    setErrorBanner(null);
    try {
      const [statusRes, alertsRes] = await Promise.all([
        fetch('/api/v1/live-sources/status'),
        fetch('/api/v1/live-alerts?limit=100'),
      ]);

      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setSources(statusData);
      }
      if (alertsRes.ok) {
        const alertsData = await alertsRes.json();
        setAlerts(alertsData);
      }
    } catch (err: any) {
      setErrorBanner('Failed to load live government feeds: ' + (err.message || 'Network error'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatusAndAlerts();
  }, []);

  const handleRefreshSource = async (sourceId: string) => {
    setIsRefreshing(sourceId);
    setErrorBanner(null);
    try {
      const res = await fetch(`/api/v1/live-sources/refresh/${sourceId}`, {
        method: 'POST',
      });
      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || `HTTP ${res.status}`);
      }
      await fetchStatusAndAlerts();
    } catch (err: any) {
      setErrorBanner(`Refresh failed: ${err.message}`);
    } finally {
      setIsRefreshing(null);
    }
  };

  const filteredAlerts = alerts.filter((alert) => {
    const matchesQuery =
      searchQuery === '' ||
      alert.headline.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.area_description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.event.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSeverity =
      selectedSeverity === 'all' ||
      alert.severity.toLowerCase() === selectedSeverity.toLowerCase();

    const matchesSource =
      selectedSource === 'all' || alert.source_id === selectedSource;

    return matchesQuery && matchesSeverity && matchesSource;
  });

  const getStatusBadge = (status: SourceStatus['status']) => {
    switch (status) {
      case 'live_ok':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-500/40">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping mr-0.5" />
            LIVE CONNECTED
          </span>
        );
      case 'live_empty':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/80 text-blue-400 border border-blue-500/40">
            CONNECTED (NO ACTIVE ALERTS)
          </span>
        );
      case 'not_configured':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700">
            KEY NOT CONFIGURED
          </span>
        );
      case 'blocked':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-400 border border-amber-500/40">
            ACCESS RESTRICTED (403/401)
          </span>
        );
      case 'error':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-400 border border-rose-500/40">
            <AlertCircle className="w-3.5 h-3.5" />
            UNAVAILABLE
          </span>
        );
    }
  };

  const getSeverityBadge = (severity: string) => {
    const s = severity.toLowerCase();
    if (s.includes('extreme') || s.includes('danger')) {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-red-950 text-red-400 border border-red-600/60">
          {severity}
        </span>
      );
    }
    if (s.includes('severe') || s.includes('warning')) {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-orange-950 text-orange-400 border border-orange-600/60">
          {severity}
        </span>
      );
    }
    if (s.includes('moderate') || s.includes('alert')) {
      return (
        <span className="px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-amber-950 text-amber-400 border border-amber-600/60">
          {severity}
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider bg-zinc-800 text-zinc-300 border border-zinc-700">
        {severity}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-[#0A0D14] text-gray-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-gray-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <Landmark className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Live Official Emergency Data
                <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono">
                  PHASE 6B
                </span>
              </h1>
              <p className="text-xs text-gray-400 mt-0.5">
                Integrated real-time feeds from NDMA SACHET (CAP 1.2 OASIS Standard) and India Meteorological Department (IMD).
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchStatusAndAlerts()}
            disabled={isLoading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-zinc-800/90 hover:bg-zinc-700 border border-zinc-700 text-xs font-medium text-gray-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh All
          </button>
        </div>
      </div>

      {errorBanner && (
        <div className="p-3.5 rounded-lg bg-red-950/60 border border-red-500/40 text-red-200 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{errorBanner}</span>
        </div>
      )}

      {/* Provenance Banner */}
      <ProvenanceLegend />

      {/* Source Operational Strip */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sources.map((src) => (
          <div
            key={src.source_id}
            className="p-4 rounded-xl bg-[#111622] border border-[#1E2638] flex flex-col justify-between space-y-4 hover:border-gray-700 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-sm text-gray-200">{src.display_name}</h3>
                  {src.source_id === 'ndma_sachet' && (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-700/50">
                      Primary
                    </span>
                  )}
                  {src.source_id === 'imd_api' && (
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
                      Secondary
                    </span>
                  )}
                </div>
                <div className="mt-1 flex items-center gap-3 text-xs text-gray-400">
                  <span>ID: <code className="text-gray-300 font-mono">{src.source_id}</code></span>
                  <span>•</span>
                  <span>Active Warnings: <strong className="text-white">{src.item_count}</strong></span>
                </div>
              </div>
              <div>{getStatusBadge(src.status)}</div>
            </div>

            {src.error_message && (
              <div className="text-xs text-amber-300/80 bg-amber-950/40 p-2.5 rounded border border-amber-800/40">
                {src.error_message}
              </div>
            )}

            <div className="pt-2 border-t border-gray-800/60 flex items-center justify-between text-xs text-gray-400">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-gray-500" />
                Last check: {src.last_fetched_at ? new Date(src.last_fetched_at).toLocaleTimeString() : 'Never'}
              </span>
              <button
                onClick={() => handleRefreshSource(src.source_id)}
                disabled={isRefreshing === src.source_id}
                className="flex items-center gap-1.5 px-3 py-1 rounded bg-[#1B2335] hover:bg-[#253047] border border-[#2B3956] text-xs font-medium text-emerald-400 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 ${isRefreshing === src.source_id ? 'animate-spin' : ''}`} />
                Fetch Live
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-[#111622] border border-[#1E2638]">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search headline, district, state, or event..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#0A0D14] border border-[#222B3D] rounded-lg pl-9 pr-3 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Severity:</span>
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="bg-[#0A0D14] border border-[#222B3D] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none"
            >
              <option value="all">All Severities</option>
              <option value="extreme">Extreme</option>
              <option value="severe">Severe</option>
              <option value="moderate">Moderate</option>
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span>Source:</span>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="bg-[#0A0D14] border border-[#222B3D] rounded px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none"
            >
              <option value="all">All Sources</option>
              <option value="ndma_sachet">NDMA SACHET</option>
              <option value="imd_api">IMD</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alert Feed Table */}
      <div className="rounded-xl bg-[#111622] border border-[#1E2638] overflow-hidden">
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="font-semibold text-sm text-gray-200 flex items-center gap-2">
            Active Government Advisories
            <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-300 font-mono">
              {filteredAlerts.length}
            </span>
          </h2>
          <span className="text-xs text-gray-400">
            Updated in real-time • Grounded against local incident coordinates
          </span>
        </div>

        {filteredAlerts.length === 0 ? (
          <div className="p-12 text-center text-gray-400 space-y-2">
            <Landmark className="w-8 h-8 text-gray-600 mx-auto" />
            <p className="text-sm">No official alerts match current filter criteria.</p>
            <p className="text-xs text-gray-500">
              Click "Fetch Live" on NDMA SACHET to poll active national alerts.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800/60">
            {filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                className="p-4 hover:bg-[#151C2C]/50 transition-colors flex flex-col md:flex-row md:items-start justify-between gap-4"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <ProvenanceBadge
                      type={alert.is_synthetic ? 'SYNTHETIC' : 'LIVE_OFFICIAL'}
                    />
                    {getSeverityBadge(alert.severity)}
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                      {alert.event}
                    </span>
                    <span className="text-xs font-mono text-gray-500">
                      ID: {alert.external_identifier}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-white leading-relaxed">
                    {alert.headline}
                  </h3>

                  <div className="flex items-center gap-1.5 text-xs text-emerald-300/90 bg-emerald-950/20 px-2.5 py-1 rounded border border-emerald-900/40 w-fit">
                    <MapPin className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Area: {alert.area_description}</span>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400 pt-1">
                    {alert.sender && <span>Issued by: <strong className="text-gray-300">{alert.sender}</strong></span>}
                    {alert.sent_at && (
                      <span>Issued: {new Date(alert.sent_at).toLocaleString()}</span>
                    )}
                    {alert.expires_at && (
                      <span>Valid until: <strong className="text-amber-400/90">{new Date(alert.expires_at).toLocaleString()}</strong></span>
                    )}
                  </div>
                </div>

                <div className="flex flex-row md:flex-col items-center md:items-end justify-between gap-2 shrink-0">
                  {alert.source_url && (
                    <a
                      href={alert.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1B2335] hover:bg-[#253047] border border-[#2B3956] text-xs font-medium text-gray-300 transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      Official Portal
                    </a>
                  )}
                  {alert.centroid && (
                    <span className="text-[11px] font-mono text-gray-500">
                      Centroid: {alert.centroid}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
