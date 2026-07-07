export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const AUTH_API_PREFIX = "/api/v1/auth";
export const AREA_API_PREFIX = "/api/v1/areas";

export async function apiRequest(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    const data = await response.json();
    
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