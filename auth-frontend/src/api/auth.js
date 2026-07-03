// api/auth.js
import { API_BASE_URL, AUTH_API_PREFIX, AREA_API_PREFIX } from "./config";

const AUTH_BASE = `${API_BASE_URL}${AUTH_API_PREFIX}`;
const AREA_BASE = `${API_BASE_URL}${AREA_API_PREFIX}`;

// ─── AUTH API CALLS ───

export async function registerApi({ user_name, email, phone_no, password }) {
  const res = await fetch(`${AUTH_BASE}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_name, email, phone_no, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Registration failed");
  return data;
}

export async function loginApi(email, password) {
  const res = await fetch(`${AUTH_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, platform: "web" }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed");
  return data;
}

export async function getMeApi(token) {
  const res = await fetch(`${AUTH_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Unauthorized");
  return await res.json();
}

export async function refreshTokenApi(refresh_token) {
  const res = await fetch(`${AUTH_BASE}/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Token refresh failed");
  return data;
}

export async function logoutApi(token, refresh_token) {
  try {
    const res = await fetch(`${AUTH_BASE}/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ refresh_token }),
    });
    if (res.ok) return await res.json();
    return { message: "Local logout" };
  } catch {
    return { message: "Logged out locally" };
  }
}

export async function changePasswordApi(token, current_password, new_password) {
  const res = await fetch(`${AUTH_BASE}/me/password`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ current_password, new_password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Password change failed");
  return data;
}

// ─── AREA API CALLS ───

export async function getUserAreasApi(token, userId) {
  const res = await fetch(`${AREA_BASE}/users/${userId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to fetch user areas");
  return data;
}

export async function createAreaApi(token, userId, coordinates) {
  const res = await fetch(`${AREA_BASE}/users/${userId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ coordinates }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to create area");
  return data;
}

export async function deleteAreaApi(token, userId) {
  const res = await fetch(`${AREA_BASE}/users/${userId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to delete area");
  return data;
}

export async function checkPointApi(token, longitude, latitude) {
  const res = await fetch(`${AREA_BASE}/check-point`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ longitude, latitude }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Point check failed");
  return data;
}