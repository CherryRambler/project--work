// context/AuthContext.jsx
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import {
  loginApi, registerApi, getMeApi, logoutApi, refreshTokenApi,
  getUserAreasApi, createAreaApi, deleteAreaApi, checkPointApi
} from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [areas, setAreas] = useState([]);
  const [token, setToken] = useState(() => localStorage.getItem("access_token"));
  const skipNextFetch = useRef(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loggingOut, setLoggingOut] = useState(false);

  const clearSession = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setToken(null);
    setUser(null);
    setAreas([]);
  }, []);

  const fetchUserAreas = useCallback(async (accessToken, userId) => {
    if (!accessToken || !userId) return;
    try {
      const areaData = await getUserAreasApi(accessToken, userId);
      // Backend returns a single { user_id, has_area, area } object
      // (one area per user). Normalize into an array for list rendering.
      if (areaData?.has_area && areaData.area) {
        setAreas([
          {
            id: areaData.user_id,
            name: "Assigned Area",
            geometry: areaData.area,
          },
        ]);
      } else {
        setAreas([]);
      }
    } catch (error) {
      console.error("Failed to fetch areas:", error);
      setAreas([]);
    }
  }, []);

  useEffect(() => {
    if (!token) return undefined;

    if (skipNextFetch.current) {
      skipNextFetch.current = false;
      return undefined;
    }

    let cancelled = false;

    async function loadUser() {
      try {
        const me = await getMeApi(token);
        if (!cancelled) {
          setUser(me);
          await fetchUserAreas(token, me.user_id);
        }
      } catch {
        const refresh = localStorage.getItem("refresh_token");
        if (!refresh) {
          if (!cancelled) clearSession();
          return;
        }

        try {
          const { access_token } = await refreshTokenApi(refresh);
          if (cancelled) return;

          localStorage.setItem("access_token", access_token);
          setToken(access_token);

          const me = await getMeApi(access_token);
          if (!cancelled) {
            setUser(me);
            await fetchUserAreas(access_token, me.user_id);
          }
        } catch {
          if (!cancelled) clearSession();
        }
      }
    }

    loadUser();

    return () => {
      cancelled = true;
    };
  }, [clearSession, token, fetchUserAreas]);

  const refreshAreas = useCallback(async () => {
    if (!token || !user) return;
    await fetchUserAreas(token, user.user_id);
  }, [token, user, fetchUserAreas]);

  async function login(email, password) {
    setLoading(true);
    setError("");
    try {
      const { access_token, refresh_token } = await loginApi(email, password);
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);
      const me = await getMeApi(access_token);
      skipNextFetch.current = true;
      setToken(access_token);
      setUser(me);
      await fetchUserAreas(access_token, me.user_id);
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setLoading(false);
    }
  }

  async function register({ user_name, email, phone_no, password }) {
    setLoading(true);
    setError("");
    try {
      await registerApi({ user_name, email, phone_no, password });
      const { access_token, refresh_token } = await loginApi(email, password);
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);
      const me = await getMeApi(access_token);
      skipNextFetch.current = true;
      setToken(access_token);
      setUser(me);
      await fetchUserAreas(access_token, me.user_id);
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      setLoading(false);
    }
  }

  async function logout() {
    setLoggingOut(true);
    const refreshToken = localStorage.getItem("refresh_token");

    try {
      if (token && refreshToken) {
        await logoutApi(token, refreshToken);
      }
    } catch {
      // Local logout should still complete if the server session is already gone.
    } finally {
      clearSession();
      setLoggingOut(false);
    }
  }

  async function createArea(name, coordinates, targetUserId) {
    try {
      // targetUserId lets an admin assign an area to another user;
      // defaults to the logged-in user's own id otherwise.
      const userId = targetUserId || user.user_id;
      const result = await createAreaApi(token, userId, coordinates);
      await refreshAreas();
      return result;
    } catch (error) {
      setError(error.message);
      throw error;
    }
  }

  async function deleteArea(targetUserId) {
    try {
      const userId = targetUserId || user.user_id;
      await deleteAreaApi(token, userId);
      await refreshAreas();
    } catch (error) {
      setError(error.message);
      throw error;
    }
  }

  async function checkPoint(longitude, latitude) {
    try {
      return await checkPointApi(token, longitude, latitude);
    } catch (error) {
      setError(error.message);
      throw error;
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        areas,
        token,
        loading,
        loggingOut,
        error,
        setError,
        login,
        register,
        logout,
        refreshAreas,
        createArea,
        deleteArea,
        checkPoint,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}