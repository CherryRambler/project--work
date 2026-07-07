import "./TabRow.css";

export default function TabRow({ active, onChange }) {
  return (
    <div className="tab-row" role="tablist">
      <button
        role="tab"
        aria-selected={active === "login"}
        className={`tab-btn ${active === "login" ? "active" : ""}`}
        onClick={() => onChange("login")}
      >
        Sign In
      </button>
      <button
        role="tab"
        aria-selected={active === "register"}
        className={`tab-btn ${active === "register" ? "active" : ""}`}
        onClick={() => onChange("register")}
      >
        Create Account
      </button>
    </div>
  );
}