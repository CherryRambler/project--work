import "./AreaCard.css";

export default function AreaCard({ area, onDelete }) {
  return (
    <div className="area-card">
      <div className="area-info">
        <div className="area-name">
          {area.name || `Area ${area.user_id?.slice(0, 8) || ''}`}
        </div>
        <div className="area-id">
          User ID: {area.user_id}
        </div>
        {area.area && (
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Area: {JSON.stringify(area.area)}
          </div>
        )}
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