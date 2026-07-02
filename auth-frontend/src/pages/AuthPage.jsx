// pages/AuthPage.jsx
import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import Logo from "../components/Logo";
import TabRow from "../components/TabRow";
import ErrorBox from "../components/ErrorBox";
import "./AuthPage.css";

// NEW: Password validation helper
function validatePassword(password) {
  const errors = [];
  
  if (password.length < 8) {
    errors.push("At least 8 characters");
  }
  if (!/[A-Z]/.test(password)) {
    errors.push("One uppercase letter");
  }
  if (!/[a-z]/.test(password)) {
    errors.push("One lowercase letter");
  }
  if (!/\d/.test(password)) {
    errors.push("One number");
  }
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push("One special character");
  }
  
  return errors;
}

// NEW: Password Strength Indicator Component
function PasswordStrengthIndicator({ password }) {
  if (!password) return null;
  
  const errors = validatePassword(password);
  const strength = errors.length === 0 ? "strong" : errors.length <= 2 ? "medium" : "weak";
  
  const getStrengthText = () => {
    if (strength === "strong") return "Strong password";
    if (strength === "medium") return "Medium password";
    return "Weak password";
  };
  
  const getStrengthColor = () => {
    if (strength === "strong") return "var(--success)";
    if (strength === "medium") return "#f59e0b";
    return "var(--danger)";
  };
  
  const getRequirements = () => {
    const reqs = [
      { text: "8+ characters", met: password.length >= 8 },
      { text: "Uppercase letter", met: /[A-Z]/.test(password) },
      { text: "Lowercase letter", met: /[a-z]/.test(password) },
      { text: "Number", met: /\d/.test(password) },
      { text: "Special character", met: /[!@#$%^&*(),.?":{}|<>]/.test(password) },
    ];
    return reqs;
  };

  return (
    <div style={{ marginTop: "8px" }}>
      <div style={{ 
        display: "flex", 
        alignItems: "center", 
        gap: "8px",
        marginBottom: "6px"
      }}>
        <div style={{
          height: "3px",
          flex: 1,
          background: "#e2e0d8",
          borderRadius: "2px",
          overflow: "hidden",
          display: "flex",
          gap: "2px"
        }}>
          {[1, 2, 3].map((i) => (
            <div key={i} style={{
              flex: 1,
              background: errors.length < i * 2 ? "#e2e0d8" : getStrengthColor(),
              transition: "background 0.3s"
            }} />
          ))}
        </div>
        <span style={{
          fontSize: "11px",
          fontWeight: "500",
          color: getStrengthColor(),
          whiteSpace: "nowrap"
        }}>
          {getStrengthText()}
        </span>
      </div>
      
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "3px 16px",
        fontSize: "11px",
        color: "var(--text-hint)"
      }}>
        {getRequirements().map((req, i) => (
          <div key={i} style={{
            display: "flex",
            alignItems: "center",
            gap: "4px",
            color: req.met ? "var(--success)" : "var(--text-hint)"
          }}>
            <span>{req.met ? "✓" : "○"}</span>
            <span>{req.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { login, loading, error } = useAuth();

  async function handleSubmit(e) {
    e.preventDefault();
    await login(email, password);
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <ErrorBox message={error} />

      <div className="field">
        <label htmlFor="login-email">Email address</label>
        <input
          id="login-email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
        />
      </div>

      <div className="field">
        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </div>

      <button className="submit-btn" type="submit" disabled={loading}>
        {loading
          ? <><span className="spinner" aria-hidden="true" /> Signing in...</>
          : "Sign in"
        }
      </button>
    </form>
  );
}

function RegisterForm() {
  const [form, setForm] = useState({
    user_name: "",
    email: "",
    phone_no: "",
    password: "",
  });
  const [passwordErrors, setPasswordErrors] = useState([]);
  const { register, loading, error } = useAuth();

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    
    if (name === "password") {
      const errors = validatePassword(value);
      setPasswordErrors(errors);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    
    const errors = validatePassword(form.password);
    if (errors.length > 0) {
      alert("Please fix password requirements:\n- " + errors.join("\n- "));
      return;
    }
    
    await register(form);
  }

  const isPasswordValid = passwordErrors.length === 0 && form.password.length > 0;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <ErrorBox message={error} />

      <div className="field">
        <label htmlFor="reg-username">Username</label>
        <input
          id="reg-username"
          name="user_name"
          type="text"
          placeholder="user name"
          value={form.user_name}
          onChange={handleChange}
          autoComplete="username"
          required
        />
      </div>

      <div className="field">
        <label htmlFor="reg-email">Email address</label>
        <input
          id="reg-email"
          name="email"
          type="email"
          placeholder="you@example.com"
          value={form.email}
          onChange={handleChange}
          autoComplete="email"
          required
        />
      </div>

      <div className="field">
        <label htmlFor="reg-phone">Phone number</label>
        <input
          id="reg-phone"
          name="phone_no"
          type="tel"
          placeholder="+91 98765 43210"
          value={form.phone_no}
          onChange={handleChange}
          autoComplete="tel"
          required
        />
      </div>

      <div className="field">
        <label htmlFor="reg-password">Password</label>
        <input
          id="reg-password"
          name="password"
          type="password"
          placeholder="Choose a strong password"
          value={form.password}
          onChange={handleChange}
          autoComplete="new-password"
          required
        />
        <PasswordStrengthIndicator password={form.password} />
      </div>

      <button 
        className="submit-btn" 
        type="submit" 
        disabled={loading || (form.password.length > 0 && !isPasswordValid)}
      >
        {loading
          ? <><span className="spinner" aria-hidden="true" /> Creating account...</>
          : "Create account"
        }
      </button>
    </form>
  );
}

export default function AuthPage() {
  const [tab, setTab] = useState("login");
  const { setError } = useAuth();

  function switchTab(t) {
    setTab(t);
    setError("");
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-card-header">
          <Logo />
          <div className="auth-divider" />
          <h1 className="auth-title">
            {tab === "login" ? "Welcome back" : "Create your account"}
          </h1>
          <p className="auth-subtitle">
            {tab === "login"
              ? "Enter your credentials to continue"
              : "Fill in your details to get started"}
          </p>
        </div>

        <TabRow active={tab} onChange={switchTab} />
        {tab === "login" ? <LoginForm /> : <RegisterForm />}
      </div>

      <p className="auth-footer">
        Secured with JWT authentication
      </p>
    </div>
  );
}