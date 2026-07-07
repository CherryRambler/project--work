import "./ErrorBox.css";

export default function ErrorBox({ message }) {
  if (!message) return null;
  
  return (
    <div className="error-box" role="alert">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.2"/>
        <path d="M8 5v3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
        <circle cx="8" cy="11.5" r="0.8" fill="currentColor"/>
      </svg>
      <span className="error-message">{message}</span>
    </div>
  );
}