import createClient from "openapi-fetch";
import createReactQueryHooks from "openapi-react-query";
import type { paths } from "./api-types";

function getToken(): string | null {
  return localStorage.getItem("millicall_token");
}

export function setToken(token: string) {
  localStorage.setItem("millicall_token", token);
}

export function clearToken() {
  localStorage.removeItem("millicall_token");
  localStorage.removeItem("millicall_user");
}

export const fetchClient = createClient<paths>({
  baseUrl: "/",
});

// Add auth header and handle 401 via middleware
fetchClient.use({
  async onRequest({ request }) {
    const token = getToken();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
  async onResponse({ response }) {
    if (response.status === 401) {
      clearToken();
      window.location.href = "/login";
    }
    return response;
  },
});

export const $api = createReactQueryHooks(fetchClient);
