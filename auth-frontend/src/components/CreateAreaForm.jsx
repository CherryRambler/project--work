import { useState } from "react";
import "./CreateAreaForm.css";

export default function CreateAreaForm({ onSubmit, isLoading }) {
  const [coordinatesText, setCoordinatesText] = useState("");
  const [error, setError] = useState("");

  const parseCoordinates = (text) => {
    const lines = text.trim().split("\n").filter(line => line.trim());
    
    if (lines.length < 3) {
      throw new Error("Need at least 3 coordinate pairs to form a polygon");
    }

    const coords = lines.map((line, index) => {
      const parts = line.trim().split(/[,\s]+/).filter(p => p);
      
      if (parts.length !== 2) {
        throw new Error(`Line ${index + 1}: Expected "longitude, latitude" but got "${line.trim()}"`);
      }
      
      const lng = parseFloat(parts[0]);
      const lat = parseFloat(parts[1]);
      
      if (isNaN(lng) || isNaN(lat)) {
        throw new Error(`Line ${index + 1}: Invalid number format`);
      }
      
      if (lng < -180 || lng > 180) {
        throw new Error(`Line ${index + 1}: Longitude must be between -180 and 180`);
      }
      
      if (lat < -90 || lat > 90) {
        throw new Error(`Line ${index + 1}: Latitude must be between -90 and 90`);
      }
      
      return [lng, lat];
    });

    return coords;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");
    
    try {
      if (!coordinatesText.trim()) {
        setError("Please enter at least 3 coordinate pairs");
        return;
      }
      
      const coords = parseCoordinates(coordinatesText);
      onSubmit(coords);
      setCoordinatesText("");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form className="create-area-form" onSubmit={handleSubmit}>
      <div className="form-header">
        <span className="form-title">
          New Area
          <span className="form-badge">Polygon</span>
        </span>
      </div>
      
      <div className="field-row">
        <div className="field">
          <label htmlFor="coordinates">Coordinates (lon, lat per line)</label>
          <textarea
            id="coordinates"
            rows="4"
            placeholder="72.8777, 19.0760&#10;72.8777, 19.1260&#10;72.9277, 19.1260&#10;72.9277, 19.0760"
            value={coordinatesText}
            onChange={(e) => setCoordinatesText(e.target.value)}
            required
          />
          <div className="field-hint">
            <span>📐</span> One pair per line · minimum 3 points
          </div>
          {error && <div className="field-error">⚠️ {error}</div>}
        </div>
        <div className="field" style={{ flex: "0 0 auto" }}>
          <button 
            type="submit" 
            className="create-area-btn" 
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="loading-spinner" style={{ width: "16px", height: "16px", borderWidth: "2px" }} />
                Creating...
              </>
            ) : (
              "Create Area"
            )}
          </button>
        </div>
      </div>
    </form>
  );
}