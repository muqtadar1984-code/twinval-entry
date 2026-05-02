import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";

import { auth as authApi } from "../lib/api";
import type { MeResponse } from "../types/api";

interface AuthContextValue {
  user: MeResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  // If any API call comes back 401, drop the local user — the next protected
  // route render will redirect to /login.
  useEffect(() => {
    function handle() {
      setUser(null);
    }
    window.addEventListener("twinval:unauthorized", handle);
    return () => window.removeEventListener("twinval:unauthorized", handle);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await authApi.login({ email, password });
    await refreshMe();
  }, [refreshMe]);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore — clearing local state is what matters
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
