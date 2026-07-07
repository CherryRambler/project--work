import { useState, useEffect } from "react";
import AreaCard from "../components/AreaCard";
import CreateAreaForm from "../components/CreateAreaForm";
import ErrorBox from "../components/ErrorBox";
import { getUserAreasApi, createAreaApi, deleteAreaApi } from "../api/auth";
import "./DashboardPage.css";

export default function DashboardPage({ user, token, onLogout }) {
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchAreas = async () => {
    if (!user?.user_id) return;
    
    setLoading(true);
    setError("");
    try {
      const data = await getUserAreasApi(token, user.user_id);
      setAreas(
        data?.has_area && data.area
          ? [{ user_id: data.user_id, geometry: data.area }]
          : []
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAreas();
  }, [token, user?.user_id]);

  const handleCreateArea = async (coords) => {
    if (!user?.user_id) {
      setError("User ID not available");
      return;
    }
    
    setCreating(true);
    setError("");
    try {
      await createAreaApi(token, user.user_id, coords);
      await fetchAreas();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteArea = async (areaId) => {
    if (!user?.user_id) {
      setError("User ID not available");
      return;
    }
    
    setError("");
    try {
      await deleteAreaApi(token, user.user_id);
      await fetchAreas();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteSpecificArea = async (areaId) => {
    if (window.confirm("This will delete all your areas. Continue?")) {
      await handleDeleteArea(areaId);
    }
  };

  const initial = user?.email?.[0]?.toUpperCase() || "U";

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <div className="dashboard-title">
          Dashboard
          <small>Manage your geographical areas</small>
        </div>
        <div className="user-actions">
          <div className="user-badge">
            <span className="user-avatar">{initial}</span>
            <span>{user?.email || "User"}</span>
          </div>
          <button className="logout-btn" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </div>

      <div className="dashboard-grid">
        {error && <ErrorBox message={error} />}
        
        <section>
          <div className="section-title">
            Your Areas
            <span className="count-badge">{areas.length}</span>
          </div>
          <CreateAreaForm onSubmit={handleCreateArea} isLoading={creating} />
          
          {loading ? (
            <div style={{ textAlign: "center", padding: "40px 0" }}>
              <div className="loading-spinner" style={{ margin: "0 auto" }} />
              <p style={{ marginTop: "12px", color: "var(--text-muted)", fontSize: "14px" }}>
                Loading your areas...
              </p>
            </div>
          ) : areas.length === 0 ? (
            <div style={{ 
              textAlign: "center", 
              padding: "48px 24px",
              background: "var(--surface)",
              border: "2px dashed var(--border)",
              borderRadius: "var(--radius)",
            }}>
              <div style={{ fontSize: "40px", marginBottom: "12px" }}>📍</div>
              <h3 style={{ fontSize: "18px", fontWeight: "600", color: "var(--text)" }}>
                No areas created yet
              </h3>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginTop: "4px" }}>
                Create your first area by entering polygon coordinates above
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {areas.map((area, index) => (
                <AreaCard
                  key={area.id || area._id || index}
                  area={area}
                  onDelete={() => handleDeleteSpecificArea(area.id || area._id)}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}