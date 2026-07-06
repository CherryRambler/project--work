import { MapContainer, TileLayer, Polygon, Popup, useMap } from "react-leaflet";
import { useEffect } from "react";

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

// react-leaflet's Polygon/Marker expect [lat, lng]; GeoJSON stores [lng, lat].
function toLatLngs(coords) {
  return coords.map(([lng, lat]) => [lat, lng]);
}

function centroidOf(latLngs) {
  const [sumLat, sumLng] = latLngs.reduce(
    ([lat, lng], [pLat, pLng]) => [lat + pLat, lng + pLng],
    [0, 0]
  );
  return [sumLat / latLngs.length, sumLng / latLngs.length];
}

function FitToBounds({ latLngs }) {
  const map = useMap();

  useEffect(() => {
    if (latLngs.length > 0) {
      map.fitBounds(latLngs, { padding: [24, 24] });
    }
  }, [map, latLngs]);

  return null;
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

  const latLngs = toLatLngs(coords);
  const center = centroidOf(latLngs);
  const name = area.name || "Assigned Area";

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        overflow: "hidden",
        height: "360px",
      }}
    >
      <MapContainer center={center} zoom={13} style={{ width: "100%", height: "100%" }}>
        <TileLayer
          attribution='Tiles &copy; Esri'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
        />
        <Polygon positions={latLngs} pathOptions={{ color: "#2563eb", fillColor: "#3b82f6", fillOpacity: 0.35 }}>
          <Popup>{name}</Popup>
        </Polygon>
        <FitToBounds latLngs={latLngs} />
      </MapContainer>
    </div>
  );
}
