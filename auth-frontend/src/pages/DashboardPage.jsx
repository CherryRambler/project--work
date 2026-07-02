// pages/DashboardPage.jsx
import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import Logo from "../components/Logo";
import AreaMap from "../components/AreaMap";
import "./DashboardPage.css";

function StatCard({ label, value, variant }) {
  return (
    <div className="stat-card">
      <p className="stat-label">{label}</p>
      <p className={`stat-value ${variant || ""}`}>{value}</p>
    </div>
  );
}

function RolePill({ role }) {
  const map = { admin: "role-admin", viewer: "role-viewer" };
  return <span className={`role-pill ${map[role] || "role-viewer"}`}>{role}</span>;
}

function AreaCard({ area, onDelete, deleting, isAdmin }) {
  return (
    <div className="area-card" style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius)",
      padding: "14px 18px",
      marginBottom: "10px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }}>
      <div>
        <div style={{ fontWeight: 500 }}>{area.name}</div>
        <div style={{ fontFamily: "var(--mono)", fontSize: "11px", color: "var(--text-hint)" }}>
          ID: {area.id}
        </div>
      </div>
      {isAdmin && (
        <button 
          onClick={() => onDelete(area.id)}
          disabled={deleting}
          style={{
            padding: "4px 10px",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            background: "transparent",
            color: "var(--danger)",
            cursor: "pointer",
            fontSize: "11.5px"
          }}
        >
          Delete
        </button>
      )}
    </div>
  );
}

function CreateAreaForm({ onCreateArea, loading }) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  const DEFAULT_COORDINATES = [
    [72.5, 18.5],
    [73.0, 18.5],
    [73.0, 19.0],
    [72.5, 19.0]
  ];

  async function handleSubmit(e) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Please enter an area name");
      return;
    }
    setError("");
    try {
      await onCreateArea(name.trim(), DEFAULT_COORDINATES);
      setName("");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius)",
      padding: "16px 18px",
      marginBottom: "16px"
    }}>
      <div style={{ display: "flex", gap: "10px", alignItems: "flex-end", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: "120px" }}>
          <label style={{ fontSize: "11.5px", fontWeight: 500, color: "var(--text-muted)" }}>
            Area Name
          </label>
          <input
            type="text"
            placeholder="e.g., Restricted Zone A"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={loading}
            style={{
              width: "100%",
              padding: "7px 10px",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)",
              fontSize: "13px",
              outline: "none"
            }}
          />
        </div>
        <button 
          type="submit" 
          disabled={loading}
          style={{
            padding: "7px 16px",
            background: "var(--accent)",
            border: "1px solid var(--accent)",
            borderRadius: "var(--radius-sm)",
            color: "#fff",
            fontSize: "13px",
            fontWeight: 500,
            cursor: "pointer",
            whiteSpace: "nowrap"
          }}
        >
          {loading ? "Creating..." : "Create Area"}
        </button>
      </div>
      {error && <p style={{ fontSize: "12px", color: "var(--danger)", marginTop: "8px" }}>{error}</p>}
      <p style={{ fontSize: "11px", color: "var(--text-hint)", marginTop: "8px" }}>
        Creates a polygon area around Mumbai (72.5°E, 18.5°N to 73.0°E, 19.0°N)
      </p>
    </form>
  );
}

export default function DashboardPage() {
  const { user, areas, logout, loggingOut, createArea, deleteArea } = useAuth();
  const [creatingArea, setCreatingArea] = useState(false);
  const [deletingArea, setDeletingArea] = useState(false);

  const joinedDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "-";

  const canManageAreas = user?.role === "admin";

  async function handleCreateArea(name, coordinates) {
    setCreatingArea(true);
    try {
      await createArea(name, coordinates);
    } finally {
      setCreatingArea(false);
    }
  }

  async function handleDeleteArea(areaId) {
    if (!window.confirm("Are you sure you want to delete this area?")) return;
    setDeletingArea(true);
    try {
      await deleteArea(areaId);
    } catch (error) {
      alert("Failed to delete area: " + error.message);
    } finally {
      setDeletingArea(false);
    }
  }

  // Log the areas data to debug
  console.log("Areas in Dashboard:", areas);

  return (
    <div className="dashboard">
      <header className="dash-header">
        <Logo />
        <nav className="dash-nav">
          <span className="dash-user">{user?.email}</span>
          <button className="logout-btn" onClick={logout} disabled={loggingOut}>
            {loggingOut ? "Signing out..." : "Sign out"}
          </button>
        </nav>
      </header>

      <div className="dash-hero">
        <h1 className="dash-title">Dashboard</h1>
        <p className="dash-subtitle">
          Signed in as <strong>{user?.user_name}</strong>
        </p>
      </div>

      {/* Account Overview */}
      <section className="section">
        <h2 className="section-label">Account overview</h2>
        <div className="stats-grid">
          <StatCard
            label="Status"
            value={user?.is_active ? "Active" : "Disabled"}
            variant={user?.is_active ? "success" : "danger"}
          />
          <StatCard label="Joined" value={joinedDate} />
          <StatCard label="Phone" value={user?.phone_no || "Not set"} />
          <StatCard
            label="Areas"
            value={areas?.length || 0}
            variant="mono"
          />
        </div>
      </section>

      {/* Role & Permissions */}
      <section className="section">
        <h2 className="section-label">Role & permissions</h2>
        <div className="role-card">
          <div className="role-card-left">
            <p className="role-card-name">
              <RolePill role={user?.role} />
            </p>
          <p className="role-card-desc">
  {user?.role === "admin"
    ? "Full access to all resources and settings."
    : "Read-only access to assigned areas."}
</p>
          </div>
          <div className="role-card-right">
            <p className="area-label">Authorized areas</p>
            <p className={`area-value ${areas?.length > 0 ? "assigned" : "unset"}`}>
              {areas?.length > 0 ? `${areas.length} area(s)` : "None assigned"}
            </p>
          </div>
        </div>
      </section>

      {/* Authorized Areas */}
      <section className="section">
        <h2 className="section-label">Authorized Areas</h2>
        
        {canManageAreas && (
          <CreateAreaForm 
            onCreateArea={handleCreateArea} 
            loading={creatingArea}
          />
        )}

        {areas?.length > 0 ? (
          <>
            {areas.map((area) => (
              <AreaCard 
                key={area.id} 
                area={area} 
                onDelete={handleDeleteArea}
                deleting={deletingArea}
                isAdmin={user?.role === "admin"}
              />
            ))}
            
            {/* Area Map - shows the first area */}
            <div style={{ marginTop: "16px" }}>
              <h3 style={{ 
                fontSize: "13px", 
                fontWeight: 500, 
                marginBottom: "10px",
                color: "var(--text-muted)"
              }}>
                Map View: {areas[0].name}
              </h3>
              <AreaMap area={areas[0]} />
            </div>
          </>
        ) : (
          <div className="role-card" style={{ padding: "20px", textAlign: "center" }}>
            <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
              No authorized areas assigned yet.
              {canManageAreas && " Click 'Create Area' to add one."}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}