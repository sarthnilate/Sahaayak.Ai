import React, { useState, useEffect } from 'react';
import { Database, Shield, Clock, RefreshCw, Filter, User, Cpu } from 'lucide-react';
import { AuditEvent, SystemHealth } from '../../types';
import { listAuditEvents } from '../../services/api';

interface Props {
  health: SystemHealth | null;
}

export const AuditView: React.FC<Props> = ({ health }) => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filterType, setFilterType] = useState('all');

  const loadAudit = async () => {
    setIsLoading(true);
    try {
      const data = await listAuditEvents(60);
      setEvents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, []);

  const filteredEvents = events.filter((e) => {
    if (filterType !== 'all' && e.entity_type !== filterType) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      
      {/* Telemetry and System Integrity Header */}
      <div className="bg-[#151515] border border-[#282828] rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#282828]">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-[#FF2DA8]" />
            <h2 className="text-base font-bold text-white font-mono uppercase tracking-wide">
              System Audit Trail & AI Engine Telemetry
            </h2>
          </div>
          <button
            onClick={loadAudit}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono bg-[#1E1E1E] text-white hover:bg-[#282828] border border-[#333]"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>REFRESH AUDIT LOG</span>
          </button>
        </div>

        {/* Engine Telemetry Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
          <div className="p-3 rounded-lg bg-[#0B0B0B] border border-[#282828] space-y-1">
            <span className="text-[#A7A7A7] block text-[10px] uppercase">AI INFERENCE PROVIDER</span>
            <div className="flex items-center gap-2 text-white font-bold">
              <Cpu className="w-4 h-4 text-[#D4FF3F]" />
              <span>{health?.ai_provider || 'Google Gemini'}</span>
            </div>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0B0B] border border-[#282828] space-y-1">
            <span className="text-[#A7A7A7] block text-[10px] uppercase">PERSISTENCE STORAGE</span>
            <div className="flex items-center gap-2 text-white font-bold">
              <Database className="w-4 h-4 text-[#FF2DA8]" />
              <span>SQLite ORM (WAL Persistent)</span>
            </div>
          </div>
          <div className="p-3 rounded-lg bg-[#0B0B0B] border border-[#282828] space-y-1">
            <span className="text-[#A7A7A7] block text-[10px] uppercase">INTEGRITY POLICY</span>
            <div className="flex items-center gap-2 text-[#48C78E] font-bold">
              <Shield className="w-4 h-4" />
              <span>Append-Only Immutable Log</span>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Events Filter */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {['all', 'report', 'incident', 'task', 'link', 'evidence'].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-3 py-1 rounded-lg text-xs font-mono font-bold uppercase transition-all ${
                filterType === t
                  ? 'bg-[#FF2DA8] text-white'
                  : 'bg-[#151515] text-[#A7A7A7] hover:text-white border border-[#282828]'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <span className="text-xs font-mono text-[#A7A7A7]">
          Showing {filteredEvents.length} Recorded Trace Events
        </span>
      </div>

      {/* Events Timeline */}
      <div className="space-y-2.5 font-mono text-xs">
        {filteredEvents.length === 0 ? (
          <div className="bg-[#151515] border border-[#282828] rounded-xl p-8 text-center text-[#A7A7A7]">
            No audit records found.
          </div>
        ) : (
          filteredEvents.map((evt) => (
            <div
              key={evt.id}
              className="p-3.5 rounded-xl bg-[#151515] border border-[#282828] hover:border-[#383838] transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#1D1D1D] text-[#D4FF3F] border border-[#333]">
                    {evt.action}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase bg-[#0B0B0B] text-[#A7A7A7] border border-[#222]">
                    ENTITY: {evt.entity_type}
                  </span>
                  <span className="text-[#A7A7A7] text-[11px] flex items-center gap-1">
                    <User className="w-3 h-3 text-[#FF2DA8]" />
                    {evt.actor}
                  </span>
                </div>
                {evt.details && (
                  <div className="text-[11px] text-[#A7A7A7] truncate max-w-xl">
                    {JSON.stringify(evt.details)}
                  </div>
                )}
              </div>

              <div className="text-[11px] text-[#666] shrink-0 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{new Date(evt.timestamp).toLocaleString()}</span>
              </div>
            </div>
          ))
        )}
      </div>

    </div>
  );
};
