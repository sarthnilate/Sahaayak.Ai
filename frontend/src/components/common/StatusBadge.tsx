import React from 'react';

interface Props {
  status: string;
}

export const StatusBadge: React.FC<Props> = ({ status }) => {
  switch (status.toLowerCase()) {
    case 'processed':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#10291F] text-[#48C78E] border border-[#48C78E]/30">
          <span className="w-1.5 h-1.5 rounded-full bg-[#48C78E] animate-pulse" />
          Processed
        </span>
      );
    case 'processing':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#351024] text-[#FF2DA8] border border-[#FF2DA8]/30">
          <span className="w-1.5 h-1.5 rounded-full bg-[#FF2DA8] animate-ping" />
          Processing AI...
        </span>
      );
    case 'needs_review':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#30240D] text-[#F5B942] border border-[#F5B942]/30">
          <span className="w-1.5 h-1.5 rounded-full bg-[#F5B942]" />
          Needs Review
        </span>
      );
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#351316] text-[#FF5C68] border border-[#FF5C68]/30">
          <span className="w-1.5 h-1.5 rounded-full bg-[#FF5C68]" />
          Failed / Retryable
        </span>
      );
    case 'received':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#1E1E1E] text-[#A7A7A7] border border-[#333]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#A7A7A7]" />
          Received
        </span>
      );
  }
};
