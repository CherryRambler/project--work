import { useState, useEffect } from "react";
import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import { AuthProvider } from "./context/AuthContext";
import "./App.css";

function AppContent() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const storedToken = localStorage.getItem("token");
    
    if (storedUser && storedToken) {
      try {
        setUser(JSON.parse(storedUser));
        setToken(storedToken);
      } catch {
        localStorage.removeItem("user");
        localStorage.removeItem("token");
      }
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
    localStorage.setItem("user", JSON.stringify(userData));
    localStorage.setItem("token", authToken);
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("user");
    localStorage.removeItem("token");
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
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}