import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Shield, Eye, EyeOff, UserPlus, LogIn, AlertCircle, Loader2 } from 'lucide-react';

export const LoginView: React.FC = () => {
  const { login, register, error, clearError, isLoading } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const switchMode = (m: 'login' | 'register') => {
    setMode(m);
    setLocalError(null);
    clearError();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    // Client-side validation
    if (!email.trim() || !password.trim()) {
      setLocalError('Email and password are required.');
      return;
    }
    if (mode === 'register') {
      if (!username.trim()) {
        setLocalError('Username is required.');
        return;
      }
      if (password.length < 10) {
        setLocalError('Password must be at least 10 characters.');
        return;
      }
    }

    try {
      if (mode === 'login') {
        await login(email.trim(), password);
      } else {
        await register(email.trim(), username.trim(), password, fullName.trim() || undefined);
      }
    } catch {
      // Error is handled by AuthContext
    }
  };

  const displayError = localError || error;

  return (
    <div className="min-h-screen bg-[#0B0B0B] text-white flex items-center justify-center p-4 bg-grid-cyber">
      {/* Background decorative elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-[#FF2DA8]/8 rounded-full blur-[120px]" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-[#D4FF3F]/6 rounded-full blur-[120px]" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Brand header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-[#FF2DA8] to-[#151515] p-0.5 shadow-[0_0_30px_rgba(255,45,168,0.4)] mb-4">
            <div className="w-full h-full bg-[#0B0B0B] rounded-[14px] flex items-center justify-center">
              <span className="font-mono font-black text-xl text-[#FF2DA8]">SA</span>
            </div>
          </div>
          <h1 className="font-mono font-extrabold text-2xl tracking-wider mb-1">SAHAAYAK.AI</h1>
          <p className="text-xs font-mono text-[#A7A7A7] tracking-wide">
            URBAN CRISIS INTELLIGENCE PLATFORM
          </p>
        </div>

        {/* Card */}
        <div className="bg-[#151515] border border-[#282828] rounded-2xl p-8 shadow-2xl">
          {/* Tab switcher */}
          <div className="flex mb-6 bg-[#0B0B0B] rounded-xl p-1 border border-[#282828]">
            <button
              onClick={() => switchMode('login')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold font-mono transition-all ${
                mode === 'login'
                  ? 'bg-[#FF2DA8] text-white shadow-[0_0_12px_rgba(255,45,168,0.35)]'
                  : 'text-[#A7A7A7] hover:text-white'
              }`}
            >
              <LogIn className="w-3.5 h-3.5" /> SIGN IN
            </button>
            <button
              onClick={() => switchMode('register')}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold font-mono transition-all ${
                mode === 'register'
                  ? 'bg-[#FF2DA8] text-white shadow-[0_0_12px_rgba(255,45,168,0.35)]'
                  : 'text-[#A7A7A7] hover:text-white'
              }`}
            >
              <UserPlus className="w-3.5 h-3.5" /> REGISTER
            </button>
          </div>

          {/* Error display */}
          {displayError && (
            <div className="mb-4 p-3 rounded-lg bg-[#351316] border border-[#FF5C68]/50 text-xs font-mono text-[#FF5C68] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{displayError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label htmlFor="auth-email" className="block text-[10px] font-mono font-bold text-[#A7A7A7] uppercase tracking-wider mb-1.5">
                Email Address
              </label>
              <input
                id="auth-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg px-4 py-2.5 text-sm font-mono text-white placeholder-[#555] focus:outline-none focus:border-[#FF2DA8] focus:shadow-[0_0_10px_rgba(255,45,168,0.15)] transition-all"
                placeholder="name@email.com"
                required
                autoComplete="email"
              />
            </div>

            {/* Username (register only) */}
            {mode === 'register' && (
              <div>
                <label htmlFor="auth-username" className="block text-[10px] font-mono font-bold text-[#A7A7A7] uppercase tracking-wider mb-1.5">
                  Username
                </label>
                <input
                  id="auth-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg px-4 py-2.5 text-sm font-mono text-white placeholder-[#555] focus:outline-none focus:border-[#FF2DA8] focus:shadow-[0_0_10px_rgba(255,45,168,0.15)] transition-all"
                  placeholder="your_username"
                  required
                  autoComplete="username"
                />
              </div>
            )}

            {/* Full name (register only) */}
            {mode === 'register' && (
              <div>
                <label htmlFor="auth-fullname" className="block text-[10px] font-mono font-bold text-[#A7A7A7] uppercase tracking-wider mb-1.5">
                  Full Name <span className="text-[#555]">(optional)</span>
                </label>
                <input
                  id="auth-fullname"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg px-4 py-2.5 text-sm font-mono text-white placeholder-[#555] focus:outline-none focus:border-[#FF2DA8] focus:shadow-[0_0_10px_rgba(255,45,168,0.15)] transition-all"
                  placeholder="Your Full Name"
                  autoComplete="name"
                />
              </div>
            )}

            {/* Password */}
            <div>
              <label htmlFor="auth-password" className="block text-[10px] font-mono font-bold text-[#A7A7A7] uppercase tracking-wider mb-1.5">
                Password {mode === 'register' && <span className="text-[#555]">(min 10 chars)</span>}
              </label>
              <div className="relative">
                <input
                  id="auth-password"
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#0B0B0B] border border-[#282828] rounded-lg px-4 py-2.5 pr-10 text-sm font-mono text-white placeholder-[#555] focus:outline-none focus:border-[#FF2DA8] focus:shadow-[0_0_10px_rgba(255,45,168,0.15)] transition-all"
                  placeholder="••••••••••"
                  required
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  minLength={mode === 'register' ? 10 : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#555] hover:text-[#A7A7A7] transition-colors"
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-mono font-bold bg-gradient-to-r from-[#FF2DA8] to-[#E91E93] text-white hover:from-[#E91E93] hover:to-[#D01A82] disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-[0_0_20px_rgba(255,45,168,0.25)] hover:shadow-[0_0_30px_rgba(255,45,168,0.4)]"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Shield className="w-4 h-4" />
              )}
              {isLoading
                ? 'AUTHENTICATING...'
                : mode === 'login'
                ? 'SIGN IN'
                : 'CREATE ACCOUNT'}
            </button>
          </form>

          {/* Demo credentials hint */}
          {mode === 'login' && (
            <div className="mt-6 p-3 rounded-lg bg-[#0B0B0B] border border-[#282828]">
              <p className="text-[10px] font-mono font-bold text-[#D4FF3F] uppercase tracking-wider mb-2">
                Demo Credentials (Click to autofill)
              </p>
              <div className="space-y-1.5 text-[11px] font-mono">
                <button
                  type="button"
                  onClick={() => { setEmail('admin@sahaayak.ai'); setPassword('AdminPass@2026'); clearError(); }}
                  className="w-full text-left p-1.5 rounded hover:bg-[#1A1A1A] transition-colors flex items-center justify-between"
                >
                  <span><span className="text-[#FF2DA8] font-bold">Admin:</span> admin@sahaayak.ai</span>
                  <span className="text-gray-500 text-[10px]">Autofill</span>
                </button>
                <button
                  type="button"
                  onClick={() => { setEmail('coordinator@sahaayak.ai'); setPassword('CoordPass@2026'); clearError(); }}
                  className="w-full text-left p-1.5 rounded hover:bg-[#1A1A1A] transition-colors flex items-center justify-between"
                >
                  <span><span className="text-[#D4FF3F] font-bold">Coordinator:</span> coordinator@sahaayak.ai</span>
                  <span className="text-gray-500 text-[10px]">Autofill</span>
                </button>
                <button
                  type="button"
                  onClick={() => { setEmail('reporter@sahaayak.ai'); setPassword('ReporterPass@2026'); clearError(); }}
                  className="w-full text-left p-1.5 rounded hover:bg-[#1A1A1A] transition-colors flex items-center justify-between"
                >
                  <span><span className="text-[#60A5FA] font-bold">Reporter:</span> reporter@sahaayak.ai</span>
                  <span className="text-gray-500 text-[10px]">Autofill</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Security badge */}
        <div className="mt-6 text-center">
          <p className="text-[10px] font-mono text-[#555] flex items-center justify-center gap-1.5">
            <Shield className="w-3 h-3" />
            ARGON2 • JWT • CSRF • ROLE-BASED ACCESS
          </p>
        </div>
      </div>
    </div>
  );
};
