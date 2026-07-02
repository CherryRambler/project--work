import { useState } from "react";
import "./TokenCard.css";

export default function TokenCard({ token }) {
  const [copied, setCopied] = useState(false);

  async function copyToken() {
    if (!token) return;
    try {
      await navigator.clipboard.writeText(token);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // clipboard access denied — do nothing
    }
  }

  const shortToken = token
    ? `${token.slice(0, 48)}...${token.slice(-16)}`
    : "";

  return (
    <div className="token-card">
      <div className="token-header">
        <div className="token-title-group">
          <p className="token-label">Access token</p>
          <span className="token-status">Active</span>
        </div>
        <button
          className={`copy-btn ${copied ? "copied" : ""}`}
          onClick={copyToken}
          aria-label="Copy token"
          disabled={!token}
        >
          {copied ? (
            <>
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                <path d="M2 6.5L5 9.5L11 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Copied
            </>
          ) : (
            <>
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                <rect x="4.5" y="1" width="7.5" height="8.5" rx="1.5" stroke="currentColor" strokeWidth="1.1"/>
                <path d="M1 4.5H3.5V12H9.5V10" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Copy
            </>
          )}
        </button>
      </div>
      <div className="token-value" onClick={token ? copyToken : undefined} title={token ? "Click to copy" : undefined}>
        {shortToken}
      </div>
      <p className="token-hint">
        Attach to requests as <code>Authorization: Bearer &lt;token&gt;</code>
      </p>
    </div>
  );
}