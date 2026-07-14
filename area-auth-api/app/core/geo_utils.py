from shapely.geometry import shape


def coords_to_polygon(coordinates: list):
    ring = coordinates[:]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return shape({"type": "Polygon", "coordinates": [ring]})
