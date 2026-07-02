function extractCoords(geometry) {
  if (!geometry) return [];

  if (geometry.type === "Polygon" && geometry.coordinates?.[0]) {
    return geometry.coordinates[0];
  }
  if (Array.isArray(geometry) && geometry.length > 0 && Array.isArray(geometry[0])) {
    return geometry;
  }
  if (geometry.coordinates && Array.isArray(geometry.coordinates)) {
    if (geometry.coordinates.length > 0 && Array.isArray(geometry.coordinates[0])) {
      if (Array.isArray(geometry.coordinates[0][0])) {
        return geometry.coordinates[0];
      }
      return geometry.coordinates;
    }
  }
  return [];
}

export default function AreaMap({ area }) {
  if (!area) {
    return <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>No area data available.</p>;
  }

  let geometry = area.geometry || area.area || area;
  if (typeof geometry === "string") {
    try { geometry = JSON.parse(geometry); } catch { /* ignore */ }
  }

  const coords = extractCoords(geometry);
  if (!coords || coords.length === 0) {
    return <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>No boundary data available.</p>;
  }

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "14px 18px",
      }}
    >
      <p style={{ fontSize: "12px", fontWeight: 500, color: "var(--text-muted)", marginBottom: "10px" }}>
        Boundary coordinates
      </p>
      <table style={{ width: "100%", fontSize: "13px", fontFamily: "var(--mono)", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ textAlign: "left", color: "var(--text-hint)", fontSize: "11px" }}>
            <th style={{ paddingBottom: "6px" }}>#</th>
            <th style={{ paddingBottom: "6px" }}>Latitude</th>
            <th style={{ paddingBottom: "6px" }}>Longitude</th>
          </tr>
        </thead>
        <tbody>
          {coords.map(([lng, lat], i) => (
            <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
              <td style={{ padding: "5px 0", color: "var(--text-hint)" }}>{i + 1}</td>
              <td style={{ padding: "5px 0" }}>{lat.toFixed(5)}°</td>
              <td style={{ padding: "5px 0" }}>{lng.toFixed(5)}°</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}