import { useState, useEffect } from "react";
import "./PasswordStrength.css";

export default function PasswordStrength({ password }) {
  const [checks, setChecks] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    digit: false,
    special: false,
  });

  useEffect(() => {
    setChecks({
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      digit: /\d/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    });
  }, [password]);

  const passedCount = Object.values(checks).filter(Boolean).length;
  const allPassed = passedCount === 5;
  
  let status = "weak";
  let statusLabel = "Weak";
  if (passedCount >= 4) { status = "strong"; statusLabel = "Strong"; }
  else if (passedCount >= 3) { status = "medium"; statusLabel = "Medium"; }

  if (password.length === 0) return null;

  return (
    <div className="password-strength">
      <div className="strength-checklist">
        <div className={`check-item ${checks.length ? "passed" : ""}`}>
          <span className="check-icon">{checks.length ? "✓" : "○"}</span>
          At least 8 characters
        </div>
        <div className={`check-item ${checks.uppercase ? "passed" : ""}`}>
          <span className="check-icon">{checks.uppercase ? "✓" : "○"}</span>
          One uppercase letter
        </div>
        <div className={`check-item ${checks.lowercase ? "passed" : ""}`}>
          <span className="check-icon">{checks.lowercase ? "✓" : "○"}</span>
          One lowercase letter
        </div>
        <div className={`check-item ${checks.digit ? "passed" : ""}`}>
          <span className="check-icon">{checks.digit ? "✓" : "○"}</span>
          One digit
        </div>
        <div className={`check-item ${checks.special ? "passed" : ""}`}>
          <span className="check-icon">{checks.special ? "✓" : "○"}</span>
          One special character
        </div>
      </div>
      <div className={`strength-status ${status}`}>
        {allPassed ? "✓" : "○"} {statusLabel} password
        {!allPassed && ` (${passedCount}/5)`}
      </div>
    </div>
  );
}