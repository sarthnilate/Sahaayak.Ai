import React from 'react';
import { Clock, Shield, FileText, CheckCircle2, User, Activity, AlertCircle } from 'lucide-react';
import { TimelineEvent } from '../../types';

interface Props {
  events: TimelineEvent[];
  isLoading?: boolean;
}

export const IncidentTimeline: React.FC<Props> = ({ events, isLoading }) => {
  if (isLoading) {
    return (
      <div className="p-8 text-center text-xs font-mono text-[#A7A7A7] space-y-2">
        <div className="w-5 h-5 border-2 border-[#FF2DA8] border-t-transparent rounded-full animate-spin mx-auto" />
        <p>Loading chronological audit timeline...</p>
      </div>
    );
  }

  if (!events || events.length === 0) {
    return (
      <div className="p-8 rounded-xl bg-[#0B0B0B] border border-[#282828] text-center text-xs font-mono text-[#777]">
        No audit or operational timeline events recorded yet for this incident.
      </div>
    );
  }

  const getEventBadge = (type: string, action: string) => {
    if (action.includes('CLOSED')) {
      return {
        bg: 'bg-[#2A1820] text-[#FF5C68] border-[#FF5C68]/40',
        icon: <AlertCircle className="w-3.5 h-3.5" />
      };
    }
    if (action.includes('RESOLVED') || action.includes('CONFIRMED')) {
      return {
        bg: 'bg-[#10291F] text-[#48C78E] border-[#48C78E]/40',
        icon: <CheckCircle2 className="w-3.5 h-3.5" />
      };
    }
    if (type === 'report') {
      return {
        bg: 'bg-[#182635] text-[#3FA9FF] border-[#3FA9FF]/40',
        icon: <FileText className="w-3.5 h-3.5" />
      };
    }
    return {
      bg: 'bg-[#1E1E1E] text-[#D4FF3F] border-[#D4FF3F]/40',
      icon: <Activity className="w-3.5 h-3.5" />
    };
  };

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-[#282828]">
      {events.map((evt) => {
        const badge = getEventBadge(evt.event_type, evt.action);
        const timeStr = new Date(evt.timestamp).toLocaleString(undefined, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        });

        return (
          <div key={evt.id} className="relative group">
            {/* Timeline node icon */}
            <div className={`absolute -left-6 top-1 w-5 h-5 rounded-full flex items-center justify-center border text-[10px] ${badge.bg} shadow-[0_0_8px_rgba(0,0,0,0.5)]`}>
              {badge.icon}
            </div>

            {/* Event Content Card */}
            <div className="bg-[#0E0E0E] border border-[#242424] hover:border-[#383838] transition-colors rounded-xl p-3.5 space-y-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${badge.bg}`}>
                    {evt.action}
                  </span>
                  <span className="text-xs font-bold text-white font-mono flex items-center gap-1">
                    <User className="w-3 h-3 text-[#A7A7A7]" />
                    {evt.actor}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-[#777] flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {timeStr}
                </span>
              </div>

              <p className="text-xs text-[#E5E5E5] leading-relaxed">
                {evt.summary}
              </p>

              {/* Expandable details if present */}
              {evt.details && Object.keys(evt.details).length > 0 && (
                <details className="mt-2 text-[11px] font-mono text-[#A7A7A7] cursor-pointer">
                  <summary className="hover:text-white transition-colors">
                    View State Payload ({Object.keys(evt.details).length} fields)
                  </summary>
                  <pre className="mt-2 p-2 rounded bg-[#070707] border border-[#1F1F1F] text-[#D4FF3F] overflow-x-auto text-[10px] leading-tight">
                    {JSON.stringify(evt.details, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
