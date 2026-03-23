import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";

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
  const [token, setToken] = useState<string | null>(() => api.getToken());

  const isAuthenticated = !!token && !!user;

  useEffect(() => {
    if (token && !user) {
      api
        .get<User>("/auth/me")
        .then((u) => {
          setUser(u);
          localStorage.setItem("millicall_user", JSON.stringify(u));
        })
        .catch(() => {
          api.clearToken();
          setToken(null);
          setUser(null);
        });
    }
  }, [token, user]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.post<{ access_token: string }>("/auth/login", {
      username,
      password,
    });
    api.setToken(res.access_token);
    setToken(res.access_token);

    const me = await api.get<User>("/auth/me");
    setUser(me);
    localStorage.setItem("millicall_user", JSON.stringify(me));
  }, []);

  const logout = useCallback(() => {
    api.clearToken();
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
