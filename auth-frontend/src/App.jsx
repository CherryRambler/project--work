import { useState, useEffect } from "react";
import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import { logoutApi } from "./api/auth";
import "./App.css";

function AppContent() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const storedToken = localStorage.getItem("token");
    const storedRefreshToken = localStorage.getItem("refreshToken");

    if (storedUser && storedToken) {
      try {
        setUser(JSON.parse(storedUser));
        setToken(storedToken);
        setRefreshToken(storedRefreshToken);
      } catch {
        localStorage.removeItem("user");
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
      }
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData, authToken, authRefreshToken) => {
    setUser(userData);
    setToken(authToken);
    setRefreshToken(authRefreshToken);
    localStorage.setItem("user", JSON.stringify(userData));
    localStorage.setItem("token", authToken);
    if (authRefreshToken) {
      localStorage.setItem("refreshToken", authRefreshToken);
    }
  };

  const handleLogout = async () => {
    if (token) {
      await logoutApi(token, refreshToken);
    }
    setUser(null);
    setToken(null);
    setRefreshToken(null);
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <span className="loading-text">Loading...</span>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="app-container">
        {!user ? (
          <AuthPage onLogin={handleLogin} />
        ) : (
          <DashboardPage user={user} token={token} onLogout={handleLogout} />
        )}
      </div>
    </div>
  );
}

export default function App() {
  return <AppContent />;
}