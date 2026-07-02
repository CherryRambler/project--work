import "./ErrorBox.css";

export default function ErrorBox({ message }) {
  if (!message) return null;
  return (
    <div className="error-box" role="alert">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
        <circle cx="7" cy="7" r="6.5" stroke="currentColor" strokeWidth="1.2"/>
        <path d="M7 4v3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
        <circle cx="7" cy="10" r="0.7" fill="currentColor"/>
      </svg>
      <span>{message}</span>
    </div>
  );
}