import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User } from '../types';
import { loginUser, registerUser, logoutUser, getMe } from '../services/api';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
  hasRole: (...roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  // Restore session on mount via /auth/me
  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((user) => {
        if (!cancelled) {
          setState({ user, isLoading: false, isAuthenticated: true, error: null });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
        }
      });
    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const result = await loginUser(email, password);
      setState({ user: result.user, isLoading: false, isAuthenticated: true, error: null });
    } catch (err: any) {
      setState((s) => ({
        ...s,
        isLoading: false,
        error: err.message || 'Login failed. Please check your credentials.',
      }));
      throw err;
    }
  }, []);

  const register = useCallback(async (email: string, username: string, password: string, fullName?: string) => {
    setState((s) => ({ ...s, isLoading: true, error: null }));
    try {
      const result = await registerUser(email, username, password, fullName);
      setState({ user: result.user, isLoading: false, isAuthenticated: true, error: null });
    } catch (err: any) {
      setState((s) => ({
        ...s,
        isLoading: false,
        error: err.message || 'Registration failed.',
      }));
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } finally {
      setState({ user: null, isLoading: false, isAuthenticated: false, error: null });
    }
  }, []);

  const clearError = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
  }, []);

  const hasRole = useCallback((...roles: string[]) => {
    return state.user != null && roles.includes(state.user.role);
  }, [state.user]);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, clearError, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
