import "./Logo.css";

export default function Logo() {
  return (
    <div className="logo">
      <div className="logo-mark">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <rect x="1" y="1" width="7" height="7" rx="2" fill="currentColor" />
          <rect x="10" y="1" width="7" height="7" rx="2" fill="currentColor" opacity="0.4" />
          <rect x="1" y="10" width="7" height="7" rx="2" fill="currentColor" opacity="0.4" />
          <rect x="10" y="10" width="7" height="7" rx="2" fill="currentColor" />
        </svg>
      </div>
      <span className="logo-text">Authkit</span>
    </div>
  );
}