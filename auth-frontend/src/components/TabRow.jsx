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
        Sign in
      </button>
      <button
        role="tab"
        aria-selected={active === "register"}
        className={`tab-btn ${active === "register" ? "active" : ""}`}
        onClick={() => onChange("register")}
      >
        Create account
      </button>
    </div>
  );
}