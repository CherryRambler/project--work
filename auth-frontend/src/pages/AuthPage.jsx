// src/pages/AuthPage.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { registerApi } from '../api/auth';
import TabRow from '../components/TabRow';
import Logo from '../components/Logo';
import ErrorBox from '../components/ErrorBox';
import PasswordStrength from '../components/PasswordStrength';
import './AuthPage.css';

export default function AuthPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('login');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      navigate('/');
    }
  }, [user, navigate]);

  const [loginForm, setLoginForm] = useState({
    email: '',
    password: '',
  });

  const [registerForm, setRegisterForm] = useState({
    user_name: '',
    email: '',
    phone_no: '',
    password: '',
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      await login(loginForm.email, loginForm.password);
      // The useEffect will handle navigation when user is set
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      await registerApi(registerForm);
      // After successful registration, switch to login
      setActiveTab('login');
      setLoginForm({ email: registerForm.email, password: '' });
      setRegisterForm({
        user_name: '',
        email: '',
        phone_no: '',
        password: '',
      });
      setError('Registration successful! Please login.');
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <Logo />
        <TabRow active={activeTab} onChange={setActiveTab} />
        
        {error && <ErrorBox message={error} />}

        {activeTab === 'login' ? (
          <form onSubmit={handleLogin} className="auth-form">
            <div className="field">
              <label htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                placeholder="you@example.com"
                value={loginForm.email}
                onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                required
                disabled={loading}
              />
            </div>
            
            <div className="field">
              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                placeholder="••••••••"
                value={loginForm.password}
                onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                required
                disabled={loading}
              />
            </div>
            
            <button type="submit" className="auth-btn" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="auth-form">
            <div className="field">
              <label htmlFor="register-username">Username</label>
              <input
                id="register-username"
                type="text"
                placeholder="johndoe"
                value={registerForm.user_name}
                onChange={(e) => setRegisterForm({ ...registerForm, user_name: e.target.value })}
                required
                disabled={loading}
              />
            </div>
            
            <div className="field">
              <label htmlFor="register-email">Email</label>
              <input
                id="register-email"
                type="email"
                placeholder="you@example.com"
                value={registerForm.email}
                onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                required
                disabled={loading}
              />
            </div>
            
            <div className="field">
              <label htmlFor="register-phone">Phone Number</label>
              <input
                id="register-phone"
                type="tel"
                placeholder="+1234567890"
                value={registerForm.phone_no}
                onChange={(e) => setRegisterForm({ ...registerForm, phone_no: e.target.value })}
                required
                disabled={loading}
              />
            </div>
            
            <div className="field">
              <label htmlFor="register-password">Password</label>
              <input
                id="register-password"
                type="password"
                placeholder="••••••••"
                value={registerForm.password}
                onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                required
                disabled={loading}
              />
              <PasswordStrength password={registerForm.password} />
            </div>
            
            <button type="submit" className="auth-btn" disabled={loading}>
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}