from typing import Any, List, Optional

from pydantic import BaseModel, field_validator


class AreaAssignSchema(BaseModel):
    coordinates: List[List[float]]

    @field_validator("coordinates")
    @classmethod
    def validate_polygon_ring(cls, coordinates: List[List[float]]):
        if len(coordinates) < 3:
            raise ValueError("At least three coordinate pairs are required")

        for point in coordinates:
            if len(point) != 2:
                raise ValueError("Each coordinate must be [longitude, latitude]")

            longitude, latitude = point
            if not -180 <= longitude <= 180:
                raise ValueError("Longitude must be between -180 and 180")
            if not -90 <= latitude <= 90:
                raise ValueError("Latitude must be between -90 and 90")

        unique_points = {tuple(point) for point in coordinates}
        if len(unique_points) < 3:
            raise ValueError("Polygon must contain at least three unique points")

        # Close the ring explicitly so callers receive a well-formed polygon
        if coordinates[0] != coordinates[-1]:
            coordinates = coordinates + [coordinates[0]]

        return coordinates


class PointCheckSchema(BaseModel):
    longitude: float
    latitude: float

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, longitude: float):
        if not -180 <= longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return longitude

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, latitude: float):
        if not -90 <= latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return latitude


class UserAreaResponse(BaseModel):
    user_id: str
    has_area: bool
    area: Optional[Any] = None
