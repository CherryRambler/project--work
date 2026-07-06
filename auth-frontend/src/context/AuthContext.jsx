// src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { loginApi, logoutApi, getMeApi, refreshTokenApi } from '../api/auth';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem('refresh_token'));
  const [loading, setLoading] = useState(true);

  const fetchUser = async (accessToken) => {
    try {
      const userData = await getMeApi(accessToken);
      setUser(userData);
      return userData;
    } catch (error) {
      console.error('Failed to fetch user:', error);
      throw error;
    }
  };

  const login = async (email, password) => {
    try {
      const data = await loginApi(email, password);
      const { access_token, refresh_token } = data;

      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      setToken(access_token);
      setRefreshToken(refresh_token);

      const userData = await fetchUser(access_token);
      return userData;
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      const currentToken = localStorage.getItem('access_token');
      const currentRefresh = localStorage.getItem('refresh_token');

      if (currentToken && currentRefresh) {
        await logoutApi(currentToken, currentRefresh);
      }
    } catch (error) {
      console.error('Logout API error:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setToken(null);
      setRefreshToken(null);
      setUser(null);
    }
  };

  // Initialize auth on mount
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('access_token');
      const storedRefresh = localStorage.getItem('refresh_token');

      if (storedToken && storedRefresh) {
        try {
          await fetchUser(storedToken);
        } catch (error) {
          // Access token likely expired — try the refresh token before giving up.
          try {
            const { access_token, refresh_token } = await refreshTokenApi(storedRefresh);
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('refresh_token', refresh_token);
            setToken(access_token);
            setRefreshToken(refresh_token);
            await fetchUser(access_token);
          } catch (refreshError) {
            console.error('Auth initialization failed:', refreshError);
            logout();
          }
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const value = {
    user,
    token,
    refreshToken,
    loading,
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};