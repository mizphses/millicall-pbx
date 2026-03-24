import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { clearToken, fetchClient, setToken } from "./client";

interface User {
  id: number;
  username: string;
  display_name: string;
  is_admin: boolean;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem("millicall_user");
    return stored ? JSON.parse(stored) : null;
  });
  const [token, setTokenState] = useState<string | null>(() =>
    localStorage.getItem("millicall_token"),
  );

  const isAuthenticated = !!token && !!user;

  useEffect(() => {
    if (token && !user) {
      fetchClient
        .GET("/api/auth/me")
        .then(({ data }) => {
          if (data) {
            setUser(data as User);
            localStorage.setItem("millicall_user", JSON.stringify(data));
          }
        })
        .catch(() => {
          clearToken();
          setTokenState(null);
          setUser(null);
        });
    }
  }, [token, user]);

  const login = useCallback(async (username: string, password: string) => {
    const { data } = await fetchClient.POST("/api/auth/login", {
      body: { username, password },
    });
    if (!data) throw new Error("Login failed");
    const res = data as { access_token: string };
    setToken(res.access_token);
    setTokenState(res.access_token);

    const { data: me } = await fetchClient.GET("/api/auth/me");
    if (me) {
      setUser(me as User);
      localStorage.setItem("millicall_user", JSON.stringify(me));
    }
  }, []);

  const logout = useCallback(async () => {
    // Clear HttpOnly cookie via server
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // ignore network errors during logout
    }
    clearToken();
    localStorage.removeItem("millicall_user");
    window.location.reload();
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
