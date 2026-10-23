import React from 'react';
import { AlertTriangle, AlertCircle, Info, ShieldAlert } from 'lucide-react';

interface Props {
  priority: string;
  showIcon?: boolean;
}

export const PriorityBadge: React.FC<Props> = ({ priority, showIcon = true }) => {
  switch (priority.toLowerCase()) {
    case 'critical':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#351316] text-[#FF5C68] border border-[#FF5C68]/50 shadow-[0_0_10px_rgba(255,92,104,0.25)]">
          {showIcon && <ShieldAlert className="w-3.5 h-3.5" />}
          CRITICAL
        </span>
      );
    case 'high':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#351024] text-[#FF2DA8] border border-[#FF2DA8]/40 shadow-[0_0_8px_rgba(255,45,168,0.2)]">
          {showIcon && <AlertTriangle className="w-3.5 h-3.5" />}
          HIGH
        </span>
      );
    case 'medium':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#30240D] text-[#F5B942] border border-[#F5B942]/40">
          {showIcon && <AlertCircle className="w-3.5 h-3.5" />}
          MEDIUM
        </span>
      );
    case 'low':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#252B12] text-[#D4FF3F] border border-[#D4FF3F]/40">
          {showIcon && <Info className="w-3.5 h-3.5" />}
          LOW
        </span>
      );
  }
};
