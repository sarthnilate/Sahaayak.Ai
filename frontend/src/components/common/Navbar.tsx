import React, { useState, useEffect } from 'react';
import {
  Activity, Shield, Database, Radio, RefreshCw, CheckCircle, Layers,
  Send, LogOut, User as UserIcon
} from 'lucide-react';
import { SystemHealth } from '../../types';
import { useAuth } from '../../contexts/AuthContext';

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
  const { user, logout, hasRole } = useAuth();
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

  // Build nav items based on role
  const navItems = [
    ...(hasRole('coordinator', 'admin')
      ? [{ id: 'dashboard', label: 'Dashboard', icon: <Activity className="w-4 h-4" /> }]
      : []),
    { id: 'submit', label: 'Submit Report', icon: <Send className="w-4 h-4" /> },
    ...(hasRole('coordinator', 'admin')
      ? [
          { id: 'reports', label: 'Reports Intake', icon: <Radio className="w-4 h-4" /> },
          { id: 'incidents', label: 'Incidents & Map', icon: <Layers className="w-4 h-4" /> },
          { id: 'live-data', label: 'Official Alerts', icon: <Shield className="w-4 h-4" /> },
          { id: 'tasks', label: 'Tasks & Dispatch', icon: <CheckCircle className="w-4 h-4" /> },
          { id: 'audit', label: 'Audit Trail', icon: <Database className="w-4 h-4" /> },
        ]
      : []),
  ];

  const roleBadgeColor: Record<string, string> = {
    admin: 'bg-[#FF5C68]/15 text-[#FF5C68] border-[#FF5C68]/40',
    coordinator: 'bg-[#D4FF3F]/15 text-[#D4FF3F] border-[#D4FF3F]/40',
    reporter: 'bg-[#FF2DA8]/15 text-[#FF2DA8] border-[#FF2DA8]/40',
    auditor: 'bg-[#48C78E]/15 text-[#48C78E] border-[#48C78E]/40',
  };

  return (
    <header className="sticky top-0 z-50 bg-[#0B0B0B]/95 backdrop-blur border-b border-[#282828] px-4 lg:px-8 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="relative group cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FF2DA8] via-[#8B00FF] to-[#D4FF3F] p-[1.5px] shadow-[0_0_20px_rgba(255,45,168,0.45)] group-hover:shadow-[0_0_25px_rgba(212,255,63,0.6)] transition-all duration-300">
              <div className="w-full h-full bg-[#0B0B0B] rounded-[10px] flex items-center justify-center relative overflow-hidden">
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2L3 7V12C3 17.5 6.8 22.3 12 23.5C17.2 22.3 21 17.5 21 12V7L12 2Z" fill="url(#logo_grad)" fillOpacity="0.2" stroke="#FF2DA8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M12 7V12L15 15" stroke="#D4FF3F" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="12" cy="12" r="2.5" fill="#D4FF3F" />
                  <defs>
                    <linearGradient id="logo_grad" x1="3" y1="2" x2="21" y2="23.5" gradientUnits="userSpaceOnUse">
                      <stop stopColor="#FF2DA8" />
                      <stop offset="1" stopColor="#D4FF3F" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
            </div>
            <span className="absolute -bottom-1 -right-1 w-3 h-3 bg-[#48C78E] border-2 border-[#0B0B0B] rounded-full" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-extrabold text-base tracking-wider text-white font-mono" data-testid="brand-title">
                SAHAAYAK.AI
              </h1>
              <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold uppercase bg-[#D4FF3F]/15 text-[#D4FF3F] border border-[#D4FF3F]/40 shadow-[0_0_8px_rgba(212,255,63,0.25)]">
                CRISIS OPS
              </span>
            </div>
            <p className="text-[11px] text-[#A7A7A7] font-mono tracking-wide">
              URBAN CRISIS RESPONSE PLATFORM
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-[#151515] border border-[#282828] p-1 rounded-xl overflow-x-auto">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-[#FF2DA8] text-white shadow-[0_0_12px_rgba(255,45,168,0.35)]'
                    : 'text-[#A7A7A7] hover:text-white hover:bg-[#1E1E1E]'
                }`}
              >
                {item.icon}
                <span className="hidden sm:inline">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right side: user + status + actions */}
        <div className="flex items-center gap-3">
          {/* Clean minimal status pill without excessive multiline text */}
          <div
            title={`Engine: ${health?.ai_provider || 'Google Gemini'} | Mode: ${health?.is_demo_mode ? 'Deterministic Demo' : 'Live Gemini'}`}
            className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-lg bg-[#151515] border border-[#282828]"
          >
            <span className="w-2 h-2 rounded-full bg-[#D4FF3F] animate-pulse" />
            <span className="text-xs font-mono font-bold text-[#E0E0E0]">
              {health?.is_demo_mode ? 'DEMO' : 'LIVE'}
            </span>
          </div>

          {/* Seed Dataset button (coordinator/admin only) */}
          {hasRole('coordinator', 'admin') && (
            <button
              onClick={onSeedDemo}
              disabled={isSeeding}
              title="Seed the official deterministic 5-minute hackathon dataset"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[#1E1E1E] hover:bg-[#282828] text-[#D4FF3F] border border-[#D4FF3F]/30 transition-all hover:border-[#D4FF3F]"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSeeding ? 'animate-spin' : ''}`} />
              <span className="hidden lg:inline">{isSeeding ? 'SEEDING...' : 'SEED DEMO'}</span>
            </button>
          )}

          {/* User menu */}
          {user && (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#151515] border border-[#282828]">
                <UserIcon className="w-3.5 h-3.5 text-[#A7A7A7]" />
                <span className="text-xs font-mono font-semibold text-white hidden lg:inline">
                  {user.username}
                </span>
                <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase border ${roleBadgeColor[user.role] || 'text-[#A7A7A7]'}`}>
                  {user.role}
                </span>
              </div>
              <button
                onClick={logout}
                title="Sign out"
                className="p-1.5 rounded-lg text-[#A7A7A7] hover:text-[#FF5C68] hover:bg-[#351316] transition-all"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Live Clock */}
          <div className="hidden xl:block px-2.5 py-1 rounded bg-[#151515] border border-[#282828] text-xs font-mono text-[#A7A7A7]">
            {time || '00:00:00'} IST
          </div>
        </div>

      </div>
    </header>
  );
};
