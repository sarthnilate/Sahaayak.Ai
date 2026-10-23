import React, { useState, useEffect } from 'react';
import {
  Activity, Shield, Database, Radio, RefreshCw, CheckCircle, AlertTriangle, Layers
} from 'lucide-react';
import { SystemHealth } from '../../types';

interface Props {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  health: SystemHealth | null;
  onSeedDemo: () => Promise<void>;
  isSeeding: boolean;
}

export const Navbar: React.FC<Props> = ({
  activeTab,
  setActiveTab,
  health,
  onSeedDemo,
  isSeeding
}) => {
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <Activity className="w-4 h-4" /> },
    { id: 'reports', label: 'Reports Intake', icon: <Radio className="w-4 h-4" /> },
    { id: 'incidents', label: 'Incidents & Map', icon: <Layers className="w-4 h-4" /> },
    { id: 'tasks', label: 'Tasks & Dispatch', icon: <CheckCircle className="w-4 h-4" /> },
    { id: 'audit', label: 'Audit Trail', icon: <Database className="w-4 h-4" /> },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#0B0B0B]/95 backdrop-blur border-b border-[#282828] px-4 lg:px-8 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#FF2DA8] to-[#151515] p-0.5 shadow-[0_0_15px_rgba(255,45,168,0.4)]">
            <div className="w-full h-full bg-[#0B0B0B] rounded-[10px] flex items-center justify-center">
              <span className="font-mono font-black text-sm text-[#FF2DA8]">SA</span>
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-extrabold text-base tracking-wider text-white font-mono">SAHAAYAK.AI</h1>
              <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold uppercase bg-[#D4FF3F]/15 text-[#D4FF3F] border border-[#D4FF3F]/40">
                OPS v1.0
              </span>
            </div>
            <p className="text-[11px] text-[#A7A7A7] font-mono tracking-wide">
              FROM CHAOS TO ACTION • URBAN CRISIS INTELLIGENCE
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-[#151515] border border-[#282828] p-1 rounded-xl">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-[#FF2DA8] text-white shadow-[0_0_12px_rgba(255,45,168,0.35)]'
                    : 'text-[#A7A7A7] hover:text-white hover:bg-[#1E1E1E]'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Engine status & actions */}
        <div className="flex items-center gap-3">
          {/* AI Provider Status */}
          <div className="hidden sm:flex flex-col text-right">
            <div className="flex items-center justify-end gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#D4FF3F] animate-pulse" />
              <span className="text-xs font-mono font-semibold text-white">
                {health?.ai_provider || 'Google Gemini'}
              </span>
            </div>
            <span className="text-[10px] font-mono text-[#A7A7A7]">
              {health?.is_demo_mode ? 'Deterministic Fallback Ready' : 'Live Google API Active'}
            </span>
          </div>

          {/* Seed Dataset button */}
          <button
            onClick={onSeedDemo}
            disabled={isSeeding}
            title="Seed the official deterministic 5-minute hackathon dataset"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[#1E1E1E] hover:bg-[#282828] text-[#D4FF3F] border border-[#D4FF3F]/30 transition-all hover:border-[#D4FF3F]"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? 'animate-spin' : ''}`} />
            <span>{isSeeding ? 'SEEDING...' : 'SEED DEMO'}</span>
          </button>

          {/* Live Clock */}
          <div className="hidden xl:block px-2.5 py-1 rounded bg-[#151515] border border-[#282828] text-xs font-mono text-[#A7A7A7]">
            {time || '00:00:00'} IST
          </div>
        </div>

      </div>
    </header>
  );
};
