import { useState } from "react";
import TabRow from "../components/TabRow";
import PasswordStrength from "../components/PasswordStrength";
import ErrorBox from "../components/ErrorBox";
import Logo from "../components/Logo";
import { loginApi, registerApi } from "../api/auth";
import "./AuthPage.css";

export default function AuthPage({ onLogin }) {
  const [activeTab, setActiveTab] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [userName, setUserName] = useState("");
  const [phoneNo, setPhoneNo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (activeTab === "login") {
        const response = await loginApi(email, password);
        
        if (response.access_token && response.refresh_token) {
          onLogin(response, response.access_token);
        } else {
          setError("Invalid response from server");
        }
      } else {
        if (!userName.trim()) {
          setError("Username is required");
          setLoading(false);
          return;
        }
        
        await registerApi({
          user_name: userName,
          email,
          phone_no: phoneNo || "N/A",
          password,
        });
        
        setSuccess("Account created successfully! Please sign in.");
        setUserName("");
        setEmail("");
        setPhoneNo("");
        setPassword("");
        setActiveTab("login");
      }
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const isRegister = activeTab === "register";
  const isLogin = activeTab === "login";

  return (
    <div className="auth-page">
      <div style={{ textAlign: "center", marginBottom: "24px" }}>
        <Logo />
      </div>
      
      <div className="auth-card">
        <TabRow active={activeTab} onChange={setActiveTab} />
        
        <div className="auth-header">
          <h2>{isLogin ? "Welcome Back" : "Create Account"}</h2>
          <p className="subtitle">
            {isLogin 
              ? "Sign in to manage your areas" 
              : "Get started with AuthKit"}
          </p>
        </div>

        {error && <ErrorBox message={error} />}
        {success && <div className="auth-success">✓ {success}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          {isRegister && (
            <>
              <div className="form-group">
                <label htmlFor="username">Username</label>
                <input
                  id="username"
                  type="text"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  placeholder="Choose a username"
                  required
                  disabled={loading}
                  autoComplete="username"
                />
              </div>
              <div className="form-group">
                <label htmlFor="phone">Phone Number (optional)</label>
                <input
                  id="phone"
                  type="tel"
                  value={phoneNo}
                  onChange={(e) => setPhoneNo(e.target.value)}
                  placeholder="+1 234 567 890"
                  disabled={loading}
                  autoComplete="tel"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              disabled={loading}
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isLogin ? "Enter your password" : "Create a password"}
              required
              disabled={loading}
              autoComplete={isLogin ? "current-password" : "new-password"}
              minLength={8}
            />
            {isRegister && <PasswordStrength password={password} />}
          </div>

          <button 
            type="submit" 
            className="auth-submit-btn" 
            disabled={loading}
          >
            {loading ? "Processing..." : (isLogin ? "Sign In" : "Create Account")}
          </button>
        </form>

        <div className="auth-footer">
          {isLogin ? (
            <>
              Don't have an account?{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab("register"); }}>
                Create one
              </a>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab("login"); }}>
                Sign in
              </a>
            </>
          )}
        </div>
      </div>
    </div>
  );
}