function getToken(): string | null {
  return localStorage.getItem("millicall_token");
}

function setToken(token: string) {
  localStorage.setItem("millicall_token", token);
}

function clearToken() {
  localStorage.removeItem("millicall_token");
  localStorage.removeItem("millicall_user");
}

async function apiFetch<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`/api${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API Error ${res.status}: ${body}`);
  }

  if (res.status === 204) return undefined as T;

  return res.json();
}

export const api = {
  getToken,
  setToken,
  clearToken,

  get<T = unknown>(path: string) {
    return apiFetch<T>(path);
  },

  post<T = unknown>(path: string, body?: unknown) {
    return apiFetch<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  put<T = unknown>(path: string, body?: unknown) {
    return apiFetch<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  delete<T = unknown>(path: string) {
    return apiFetch<T>(path, { method: "DELETE" });
  },
};
