// src/components/AreaCard.jsx
import "./AreaCard.css";

export default function AreaCard({ area, onDelete }) {
  const coords = area.geometry?.coordinates?.[0] || area.area?.coordinates?.[0] || [];
  const coordDisplay = coords.length > 0 
    ? `${coords.length} points` 
    : "No coordinates";

  return (
    <div className="area-card">
      <div className="area-icon">📍</div>
      <div className="area-info">
        <div className="area-name">
          {area.name || `Area ${area.user_id?.slice(0, 8) || "Unnamed"}`}
          <span className="area-id-display">#{area.id?.slice(0, 6) || area._id?.slice(0, 6)}</span>
        </div>
        <div className="area-id">User: {area.user_id}</div>
        <div className="area-coords">
          <span>● {coordDisplay}</span>
        </div>
      </div>
      {onDelete && (
        <div className="area-actions">
          <button 
            className="area-btn danger" 
            onClick={onDelete}
            aria-label="Delete area"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}