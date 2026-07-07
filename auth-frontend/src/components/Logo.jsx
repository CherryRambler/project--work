import "./Logo.css";

export default function Logo() {
  return (
    <a href="#" className="logo" onClick={(e) => e.preventDefault()}>
      <div className="logo-mark">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <rect x="2" y="2" width="7" height="7" rx="1.5" fill="currentColor" />
          <rect x="11" y="2" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.35" />
          <rect x="2" y="11" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.35" />
          <rect x="11" y="11" width="7" height="7" rx="1.5" fill="currentColor" />
        </svg>
      </div>
      <span className="logo-text">Auth<span className="highlight">Kit</span></span>
    </a>
  );
}