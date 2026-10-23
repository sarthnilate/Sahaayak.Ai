import React from 'react';
import { Landmark, Users, Cpu, AlertTriangle, ShieldCheck } from 'lucide-react';

export type ProvenanceType = 'LIVE_OFFICIAL' | 'COMMUNITY_CLAIM' | 'AI_ANALYSIS' | 'SYNTHETIC';

interface Props {
  type: ProvenanceType;
  label?: string;
  className?: string;
}

export const ProvenanceBadge: React.FC<Props> = ({ type, label, className = '' }) => {
  switch (type) {
    case 'LIVE_OFFICIAL':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold tracking-wide bg-[#0B2E1D] text-[#48C78E] border border-[#48C78E]/60 shadow-[0_0_8px_rgba(72,199,142,0.15)] ${className}`}
          title="Directly retrieved and validated from official government emergency feeds (NDMA / IMD)"
        >
          <Landmark className="w-3.5 h-3.5 text-[#48C78E]" />
          <span>{label || 'LIVE OFFICIAL'}</span>
        </span>
      );

    case 'COMMUNITY_CLAIM':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold tracking-wide bg-[#1A2536] text-[#60A5FA] border border-[#3B82F6]/50 ${className}`}
          title="Submitted by ground citizens or community observers — not an official advisory"
        >
          <Users className="w-3.5 h-3.5 text-[#60A5FA]" />
          <span>{label || 'COMMUNITY CLAIM'}</span>
        </span>
      );

    case 'AI_ANALYSIS':
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold tracking-wide bg-[#2D1B4E] text-[#C084FC] border border-[#A855F7]/50 ${className}`}
          title="Extracted or synthesized by Gemini model intelligence — requires coordinator sign-off"
        >
          <Cpu className="w-3.5 h-3.5 text-[#C084FC]" />
          <span>{label || 'AI ANALYSIS'}</span>
        </span>
      );

    case 'SYNTHETIC':
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-bold tracking-wide bg-[#3A1D0B] text-[#FB923C] border border-[#F97316]/60 animate-pulse ${className}`}
          title="Simulated demo data generated under LIVE_DATA_FALLBACK policy — NOT real emergency data"
        >
          <AlertTriangle className="w-3.5 h-3.5 text-[#FB923C]" />
          <span>{label || 'SYNTHETIC'}</span>
        </span>
      );
  }
};

export const ProvenanceLegend: React.FC = () => {
  return (
    <div className="flex flex-wrap items-center gap-3 p-3 rounded-lg bg-[#141414] border border-[#2B2B2B] text-xs text-gray-400">
      <span className="font-semibold text-gray-300">Data Provenance:</span>
      <ProvenanceBadge type="LIVE_OFFICIAL" />
      <ProvenanceBadge type="COMMUNITY_CLAIM" />
      <ProvenanceBadge type="AI_ANALYSIS" />
      <ProvenanceBadge type="SYNTHETIC" />
    </div>
  );
};
