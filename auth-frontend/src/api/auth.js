import { API_BASE_URL, AUTH_API_PREFIX, AREA_API_PREFIX, apiRequest } from "./config";


export async function registerApi({ user_name, email, phone_no, password }) {
  return apiRequest(`${AUTH_API_PREFIX}/register`, {
    method: "POST",
    body: JSON.stringify({ user_name, email, phone_no, password }),
  });
}

export async function loginApi(email, password) {
  return apiRequest(`${AUTH_API_PREFIX}/login`, {
    method: "POST",
    body: JSON.stringify({ email, password, platform: "web" }),
  });
}

export async function getMeApi(token) {
  return apiRequest(`${AUTH_API_PREFIX}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function refreshTokenApi(refresh_token) {
  return apiRequest(`${AUTH_API_PREFIX}/refresh`, {
    method: "POST",
    body: JSON.stringify({ refresh_token }),
  });
}

export async function logoutApi(token, refresh_token) {
  try {
    return await apiRequest(`${AUTH_API_PREFIX}/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ refresh_token }),
    });
  } catch (error) {
    console.warn("Logout API error:", error.message);
    return { message: "Logged out locally" };
  }
}

export async function changePasswordApi(token, current_password, new_password) {
  return apiRequest(`${AUTH_API_PREFIX}/me/password`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ current_password, new_password }),
  });
}


export async function getUserAreasApi(token, userId) {
  return apiRequest(`${AREA_API_PREFIX}/users/${userId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function createAreaApi(token, userId, coordinates) {
  return apiRequest(`${AREA_API_PREFIX}/users/${userId}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ coordinates }),
  });
}

export async function deleteAreaApi(token, userId) {
  return apiRequest(`${AREA_API_PREFIX}/users/${userId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function checkPointApi(token, longitude, latitude) {
  return apiRequest(`${AREA_API_PREFIX}/check-point`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ longitude, latitude }),
  });
}


// SURVEY API CALLS

const SURVEY_BASE = `${API_BASE_URL}/api/v1/surveys`;

export async function createSurveyApi(token, data) {
  return apiRequest(SURVEY_BASE, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

export async function getAllSurveysApi(token) {
  return apiRequest(SURVEY_BASE, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getMySurveysApi(token) {
  return apiRequest(`${SURVEY_BASE}/my`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getSurveyApi(token, id) {
  return apiRequest(`${SURVEY_BASE}/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function verifySurveyApi(token, id, verified_status) {
  return apiRequest(`${SURVEY_BASE}/${id}/verify`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ verified_status }),
  });
}

export async function adminUpdateSurveyApi(token, id, data) {
  return apiRequest(`${SURVEY_BASE}/${id}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
  });
}

export async function deleteSurveyApi(token, id) {
  return apiRequest(`${SURVEY_BASE}/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}