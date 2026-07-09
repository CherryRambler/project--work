export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const AUTH_API_PREFIX = "/api/v1/auth";
export const AREA_API_PREFIX = "/api/v1/areas";

const REFRESH_ENDPOINT = `${AUTH_API_PREFIX}/refresh`;

// Coalesces concurrent 401s into a single in-flight refresh call.
let refreshPromise = null;

async function performRefresh() {
  const refreshToken = localStorage.getItem("refreshToken");
  if (!refreshToken) return null;

  const response = await fetch(`${API_BASE_URL}${REFRESH_ENDPOINT}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) return null;

  const data = await response.json();
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("refreshToken", data.refresh_token);
  return data.access_token;
}

function forceLogout() {
  localStorage.removeItem("user");
  localStorage.removeItem("token");
  localStorage.removeItem("refreshToken");
  window.dispatchEvent(new Event("auth:logout"));
}

async function doFetch(url, options) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const data = await response.json();
  return { response, data };
}

export async function apiRequest(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const isAuthedRequest = Boolean(options.headers?.Authorization);
  const isRefreshCall = endpoint.includes(REFRESH_ENDPOINT);

  try {
    let { response, data } = await doFetch(url, options);

    if (response.status === 401 && isAuthedRequest && !isRefreshCall) {
      refreshPromise = refreshPromise || performRefresh().finally(() => {
        refreshPromise = null;
      });
      const newAccessToken = await refreshPromise;

      if (!newAccessToken) {
        forceLogout();
      } else {
        ({ response, data } = await doFetch(url, {
          ...options,
          headers: { ...options.headers, Authorization: `Bearer ${newAccessToken}` },
        }));
      }
    }

    if (!response.ok) {
      const errorMessage = data.detail || data.message || data.error || "Request failed";
      throw new Error(typeof errorMessage === "string" ? errorMessage : JSON.stringify(errorMessage));
    }

    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Network error - please check your connection");
  }
}