import React from 'react';

interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  accent?: 'pink' | 'chartreuse' | 'red' | 'neutral';
}

export const MetricCard: React.FC<Props> = ({
  title,
  value,
  subtitle,
  icon,
  accent = 'pink'
}) => {
  const accentBorder = {
    pink: 'hover:border-[#FF2DA8]/50 group-hover:text-[#FF2DA8]',
    chartreuse: 'hover:border-[#D4FF3F]/50 group-hover:text-[#D4FF3F]',
    red: 'hover:border-[#FF5C68]/50 group-hover:text-[#FF5C68]',
    neutral: 'hover:border-white/30 group-hover:text-white',
  }[accent];

  const barColor = {
    pink: 'bg-[#FF2DA8]',
    chartreuse: 'bg-[#D4FF3F]',
    red: 'bg-[#FF5C68]',
    neutral: 'bg-white',
  }[accent];

  return (
    <div className={`relative bg-[#151515] border border-[#282828] rounded-xl p-5 overflow-hidden transition-all duration-200 group ${accentBorder}`}>
      <div className={`absolute top-0 left-0 right-0 h-[2px] ${barColor} opacity-75`} />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-[#A7A7A7] font-mono">{title}</p>
          <h3 className="text-2xl font-bold text-white mt-1 font-mono tracking-tight">{value}</h3>
          {subtitle && (
            <p className="text-xs text-[#A7A7A7] mt-1">{subtitle}</p>
          )}
        </div>
        <div className="p-2.5 rounded-lg bg-[#1E1E1E] text-white border border-[#333]">
          {icon}
        </div>
      </div>
    </div>
  );
};
