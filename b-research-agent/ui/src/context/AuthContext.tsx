import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import * as api from '../api/client';
import type { AuthSession, UserProfile } from '../types';

const TOKEN_KEY = 'nexus_auth_token';
const USER_KEY = 'nexus_auth_user';

interface AuthContextValue {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<AuthSession>;
  register: (email: string, password: string, fullName?: string) => Promise<AuthSession>;
  googleAuth: (email: string, fullName?: string, avatarUrl?: string) => Promise<AuthSession>;
  forgotPassword: (email: string) => Promise<{ ok: boolean; message: string; demo_reset_token?: string }>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<UserProfile | null>(() => {
    try {
      const saved = localStorage.getItem(USER_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const apiBase = import.meta.env.VITE_API_BASE ?? '';

  // Synchronize and validate session on initial mount
  useEffect(() => {
    let mounted = true;
    async function checkSession() {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      if (!storedToken) {
        if (mounted) setIsLoading(false);
        return;
      }
      try {
        const session = await api.getMeApi(apiBase, storedToken);
        if (mounted) {
          setUser(session.user);
          setToken(session.access_token);
          localStorage.setItem(USER_KEY, JSON.stringify(session.user));
          // Also sync workspace into config storage
          const cfg = {
            apiBase,
            workspaceId: session.workspace.id,
            apiKey: session.workspace.api_key,
          };
          localStorage.setItem('research_assistant_config', JSON.stringify(cfg));
        }
      } catch {
        if (mounted) {
          setToken(null);
          setUser(null);
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    }
    checkSession();
    return () => {
      mounted = false;
    };
  }, [apiBase]);

  const handleSessionSuccess = useCallback((session: AuthSession) => {
    setToken(session.access_token);
    setUser(session.user);
    setError(null);
    localStorage.setItem(TOKEN_KEY, session.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(session.user));

    // Automatically set active workspace
    const cfg = {
      apiBase,
      workspaceId: session.workspace.id,
      apiKey: session.workspace.api_key,
    };
    localStorage.setItem('research_assistant_config', JSON.stringify(cfg));
  }, [apiBase]);

  const login = useCallback(
    async (email: string, password: string): Promise<AuthSession> => {
      setError(null);
      try {
        const session = await api.loginApi(apiBase, { email, password });
        handleSessionSuccess(session);
        return session;
      } catch (err: any) {
        const msg = err.message || 'Login failed. Please check your credentials.';
        setError(msg);
        throw err;
      }
    },
    [apiBase, handleSessionSuccess],
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string): Promise<AuthSession> => {
      setError(null);
      try {
        const session = await api.registerApi(apiBase, { email, password, full_name: fullName });
        handleSessionSuccess(session);
        return session;
      } catch (err: any) {
        const msg = err.message || 'Registration failed.';
        setError(msg);
        throw err;
      }
    },
    [apiBase, handleSessionSuccess],
  );

  const googleAuth = useCallback(
    async (email: string, fullName?: string, avatarUrl?: string): Promise<AuthSession> => {
      setError(null);
      try {
        const session = await api.googleAuthApi(apiBase, { email, full_name: fullName, avatar_url: avatarUrl });
        handleSessionSuccess(session);
        return session;
      } catch (err: any) {
        const msg = err.message || 'Google authentication failed.';
        setError(msg);
        throw err;
      }
    },
    [apiBase, handleSessionSuccess],
  );

  const forgotPassword = useCallback(
    async (email: string) => {
      setError(null);
      return api.forgotPasswordApi(apiBase, email);
    },
    [apiBase],
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        error,
        login,
        register,
        googleAuth,
        forgotPassword,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
};
