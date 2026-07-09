import { useState, useEffect } from "react";
import AreaCard from "../components/AreaCard";
import CreateAreaForm from "../components/CreateAreaForm";
import ErrorBox from "../components/ErrorBox";
import {
  getUserAreasApi,
  createAreaApi,
  deleteAreaApi,
  getMySurveysApi,
  getAllSurveysApi,
  createSurveyApi,
  verifySurveyApi,
  adminUpdateSurveyApi,
  deleteSurveyApi,
} from "../api/auth";
import "./DashboardPage.css";

function parseSurveyCoordinates(text) {
  const lines = text.trim().split("\n").filter((line) => line.trim());
  if (lines.length < 3) {
    throw new Error("Need at least 3 coordinate pairs to form a polygon");
  }
  return lines.map((line, index) => {
    const parts = line.trim().split(/[,\s]+/).filter(Boolean);
    if (parts.length !== 2) {
      throw new Error(`Line ${index + 1}: Expected "longitude, latitude"`);
    }
    const lng = parseFloat(parts[0]);
    const lat = parseFloat(parts[1]);
    if (isNaN(lng) || isNaN(lat)) {
      throw new Error(`Line ${index + 1}: Invalid number format`);
    }
    return [lng, lat];
  });
}

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

  const isAdmin = user?.role === "admin";
  const initial = user?.email?.[0]?.toUpperCase() || "U";

  // --- Survey records: "My Survey Records" (all users) ---
  const [mySurveys, setMySurveys] = useState([]);
  const [surveysLoading, setSurveysLoading] = useState(false);
  const [surveyError, setSurveyError] = useState("");

  const fetchMySurveys = async () => {
    setSurveysLoading(true);
    setSurveyError("");
    try {
      const data = await getMySurveysApi(token);
      setMySurveys(Array.isArray(data) ? data : []);
    } catch (err) {
      setSurveyError(err.message);
    } finally {
      setSurveysLoading(false);
    }
  };

  useEffect(() => {
    fetchMySurveys();
  }, [token]);

  const handleToggleVerified = async (survey) => {
    setSurveyError("");
    try {
      await verifySurveyApi(token, survey.id, !survey.verified_status);
      await fetchMySurveys();
      if (isAdmin) await fetchAllSurveys();
    } catch (err) {
      setSurveyError(err.message);
    }
  };

  // --- Survey records: "Manage Surveys" (admin only) ---
  const [allSurveys, setAllSurveys] = useState([]);
  const [adminSurveysLoading, setAdminSurveysLoading] = useState(false);
  const [adminSurveyError, setAdminSurveyError] = useState("");
  const [creatingSurvey, setCreatingSurvey] = useState(false);
  const [newSurvey, setNewSurvey] = useState({
    user_id: "",
    village: "",
    plot: "",
    coordinatesText: "",
  });
  const [editingSurveyId, setEditingSurveyId] = useState(null);
  const [editSurvey, setEditSurvey] = useState({
    village: "",
    plot: "",
    coordinatesText: "",
  });

  const fetchAllSurveys = async () => {
    if (!isAdmin) return;
    setAdminSurveysLoading(true);
    setAdminSurveyError("");
    try {
      const data = await getAllSurveysApi(token);
      setAllSurveys(Array.isArray(data) ? data : []);
    } catch (err) {
      setAdminSurveyError(err.message);
    } finally {
      setAdminSurveysLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) fetchAllSurveys();
  }, [token, isAdmin]);

  const handleCreateSurvey = async (e) => {
    e.preventDefault();
    setAdminSurveyError("");
    try {
      const coordinates = parseSurveyCoordinates(newSurvey.coordinatesText);
      setCreatingSurvey(true);
      await createSurveyApi(token, {
        user_id: newSurvey.user_id,
        village: newSurvey.village,
        plot: newSurvey.plot,
        coordinates,
      });
      setNewSurvey({ user_id: "", village: "", plot: "", coordinatesText: "" });
      await fetchAllSurveys();
    } catch (err) {
      setAdminSurveyError(err.message);
    } finally {
      setCreatingSurvey(false);
    }
  };

  const startEditSurvey = (survey) => {
    setEditingSurveyId(survey.id);
    setEditSurvey({ village: survey.village, plot: survey.plot, coordinatesText: "" });
  };

  const cancelEditSurvey = () => {
    setEditingSurveyId(null);
  };

  const handleSaveEditSurvey = async (id) => {
    setAdminSurveyError("");
    try {
      const payload = { village: editSurvey.village, plot: editSurvey.plot };
      if (editSurvey.coordinatesText.trim()) {
        payload.coordinates = parseSurveyCoordinates(editSurvey.coordinatesText);
      }
      await adminUpdateSurveyApi(token, id, payload);
      setEditingSurveyId(null);
      await fetchAllSurveys();
    } catch (err) {
      setAdminSurveyError(err.message);
    }
  };

  const handleDeleteSurvey = async (id) => {
    if (!window.confirm("Delete this survey record?")) return;
    setAdminSurveyError("");
    try {
      await deleteSurveyApi(token, id);
      await fetchAllSurveys();
    } catch (err) {
      setAdminSurveyError(err.message);
    }
  };

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

        <section>
          <div className="section-title">
            My Survey Records
            <span className="count-badge">{mySurveys.length}</span>
          </div>
          {surveyError && <ErrorBox message={surveyError} />}

          {surveysLoading ? (
            <div style={{ textAlign: "center", padding: "40px 0" }}>
              <div className="loading-spinner" style={{ margin: "0 auto" }} />
            </div>
          ) : mySurveys.length === 0 ? (
            <div style={{
              textAlign: "center",
              padding: "32px 24px",
              background: "var(--surface)",
              border: "2px dashed var(--border)",
              borderRadius: "var(--radius)",
            }}>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
                No survey records assigned yet.
              </p>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: "8px" }}>Village</th>
                    <th style={{ textAlign: "left", padding: "8px" }}>Plot</th>
                    <th style={{ textAlign: "left", padding: "8px" }}>Timestamp</th>
                    <th style={{ textAlign: "left", padding: "8px" }}>Status</th>
                    <th style={{ textAlign: "left", padding: "8px" }}></th>
                  </tr>
                </thead>
                <tbody>
                  {mySurveys.map((survey) => (
                    <tr key={survey.id}>
                      <td style={{ padding: "8px" }}>{survey.village}</td>
                      <td style={{ padding: "8px" }}>{survey.plot}</td>
                      <td style={{ padding: "8px" }}>
                        {new Date(survey.timestamp).toLocaleString()}
                      </td>
                      <td style={{ padding: "8px" }}>
                        {survey.verified_status ? (
                          <span style={{ color: "green" }}>Verified ✓</span>
                        ) : (
                          <span style={{ color: "orange" }}>Pending</span>
                        )}
                      </td>
                      <td style={{ padding: "8px" }}>
                        <button onClick={() => handleToggleVerified(survey)}>
                          {survey.verified_status ? "Mark Unverified" : "Mark Verified"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {isAdmin && (
          <section>
            <div className="section-title">
              Manage Surveys
              <span className="count-badge">{allSurveys.length}</span>
            </div>
            {adminSurveyError && <ErrorBox message={adminSurveyError} />}

            <form onSubmit={handleCreateSurvey} style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px" }}>
              <input
                type="text"
                placeholder="Assign to User (user_id)"
                value={newSurvey.user_id}
                onChange={(e) => setNewSurvey({ ...newSurvey, user_id: e.target.value })}
                required
              />
              <input
                type="text"
                placeholder="Village"
                value={newSurvey.village}
                onChange={(e) => setNewSurvey({ ...newSurvey, village: e.target.value })}
                required
              />
              <input
                type="text"
                placeholder="Plot"
                value={newSurvey.plot}
                onChange={(e) => setNewSurvey({ ...newSurvey, plot: e.target.value })}
                required
              />
              <textarea
                rows="4"
                placeholder="72.8777, 19.0760&#10;72.8777, 19.1260&#10;72.9277, 19.1260&#10;72.9277, 19.0760"
                value={newSurvey.coordinatesText}
                onChange={(e) => setNewSurvey({ ...newSurvey, coordinatesText: e.target.value })}
                required
              />
              <button type="submit" disabled={creatingSurvey}>
                {creatingSurvey ? "Creating..." : "Create Survey Record"}
              </button>
            </form>

            {adminSurveysLoading ? (
              <div style={{ textAlign: "center", padding: "40px 0" }}>
                <div className="loading-spinner" style={{ margin: "0 auto" }} />
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: "left", padding: "8px" }}>User ID</th>
                      <th style={{ textAlign: "left", padding: "8px" }}>Village</th>
                      <th style={{ textAlign: "left", padding: "8px" }}>Plot</th>
                      <th style={{ textAlign: "left", padding: "8px" }}>Timestamp</th>
                      <th style={{ textAlign: "left", padding: "8px" }}>Status</th>
                      <th style={{ textAlign: "left", padding: "8px" }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allSurveys.map((survey) =>
                      editingSurveyId === survey.id ? (
                        <tr key={survey.id}>
                          <td style={{ padding: "8px" }}>{survey.user_id}</td>
                          <td style={{ padding: "8px" }}>
                            <input
                              type="text"
                              value={editSurvey.village}
                              onChange={(e) => setEditSurvey({ ...editSurvey, village: e.target.value })}
                            />
                          </td>
                          <td style={{ padding: "8px" }}>
                            <input
                              type="text"
                              value={editSurvey.plot}
                              onChange={(e) => setEditSurvey({ ...editSurvey, plot: e.target.value })}
                            />
                          </td>
                          <td style={{ padding: "8px" }} colSpan={2}>
                            <textarea
                              rows="3"
                              placeholder="Leave blank to keep existing coordinates"
                              value={editSurvey.coordinatesText}
                              onChange={(e) => setEditSurvey({ ...editSurvey, coordinatesText: e.target.value })}
                            />
                          </td>
                          <td style={{ padding: "8px" }}>
                            <button onClick={() => handleSaveEditSurvey(survey.id)}>Save</button>
                            <button onClick={cancelEditSurvey}>Cancel</button>
                          </td>
                        </tr>
                      ) : (
                        <tr key={survey.id}>
                          <td style={{ padding: "8px" }}>{survey.user_id}</td>
                          <td style={{ padding: "8px" }}>{survey.village}</td>
                          <td style={{ padding: "8px" }}>{survey.plot}</td>
                          <td style={{ padding: "8px" }}>
                            {new Date(survey.timestamp).toLocaleString()}
                          </td>
                          <td style={{ padding: "8px" }}>
                            {survey.verified_status ? (
                              <span style={{ color: "green" }}>Verified ✓</span>
                            ) : (
                              <span style={{ color: "orange" }}>Pending</span>
                            )}
                          </td>
                          <td style={{ padding: "8px" }}>
                            <button onClick={() => startEditSurvey(survey)}>Edit</button>
                            <button onClick={() => handleDeleteSurvey(survey.id)}>Delete</button>
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}