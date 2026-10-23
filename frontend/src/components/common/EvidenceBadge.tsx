import React from 'react';
import { CheckCircle2, AlertOctagon, HelpCircle, AlertCircle } from 'lucide-react';

interface Props {
  status: string;
}

export const EvidenceBadge: React.FC<Props> = ({ status }) => {
  switch (status.toLowerCase()) {
    case 'corroborated':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-[#10291F] text-[#48C78E] border border-[#48C78E]/30">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#48C78E]" />
          Corroborated by Evidence
        </span>
      );
    case 'partially_corroborated':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-[#252B12] text-[#D4FF3F] border border-[#D4FF3F]/30">
          <CheckCircle2 className="w-3.5 h-3.5 text-[#D4FF3F]" />
          Partially Corroborated
        </span>
      );
    case 'conflicting_evidence':
    case 'conflicting':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold bg-[#351316] text-[#FF5C68] border border-[#FF5C68]/50 animate-pulse">
          <AlertOctagon className="w-3.5 h-3.5 text-[#FF5C68]" />
          Conflicting Evidence
        </span>
      );
    case 'unverified':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-[#1E1E1E] text-[#A7A7A7] border border-[#333]">
          <HelpCircle className="w-3.5 h-3.5 text-[#A7A7A7]" />
          Unverified Claims
        </span>
      );
  }
};
