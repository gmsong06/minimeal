import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { API_BASE_URL } from '@/constants/api';

type SeededAccount = {
  username: string;
  password: string;
  display_name: string;
};

type AuthSession = {
  username: string;
  display_name: string;
};

type AuthContextValue = {
  session: AuthSession | null;
  seededAccounts: SeededAccount[];
  isLoadingAccounts: boolean;
  authError: string | null;
  refreshAccounts: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  authHeaders: Record<string, string>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [seededAccounts, setSeededAccounts] = useState<SeededAccount[]>([]);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);

  const refreshAccounts = useCallback(async () => {
    setIsLoadingAccounts(true);
    setAuthError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/auth/accounts`);
      if (!response.ok) {
        throw new Error(`Failed to load demo accounts (${response.status}).`);
      }
      const accounts: SeededAccount[] = await response.json();
      setSeededAccounts(accounts);
    } catch (error) {
      setAuthError(
        error instanceof Error
          ? error.message
          : 'Unable to load accounts.'
      );
      setSeededAccounts([]);
    } finally {
      setIsLoadingAccounts(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setAuthError(null);
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `Login failed (${response.status}).`);
    }

    const user: AuthSession = await response.json();
    setSession(user);
  }, []);

  const logout = useCallback(() => {
    setSession(null);
  }, []);

  useEffect(() => {
    void refreshAccounts();
  }, [refreshAccounts]);

  const authHeaders = useMemo<Record<string, string>>(() => {
    const headers: Record<string, string> = {};
    if (session) {
      headers['X-Minimeal-Username'] = session.username;
    }
    return headers;
  }, [session]);

  const value: AuthContextValue = {
    session,
    seededAccounts,
    isLoadingAccounts,
    authError,
    refreshAccounts,
    login,
    logout,
    authHeaders,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider.');
  }
  return context;
}
