from pydantic import BaseModel, field_validator
from typing import Any, List, Optional
from datetime import datetime


def validate_polygon_coords(coordinates: List[List[float]]) -> List[List[float]]:
    if len(coordinates) < 3:
        raise ValueError("Polygon must have at least 3 coordinate pairs")
    for point in coordinates:
        if len(point) != 2:
            raise ValueError("Each coordinate must be [longitude, latitude]")
        lng, lat = point
        if not -180 <= lng <= 180:
            raise ValueError(f"Longitude {lng} is out of range [-180, 180]")
        if not -90 <= lat <= 90:
            raise ValueError(f"Latitude {lat} is out of range [-90, 90]")
    unique = {tuple(p) for p in coordinates}
    if len(unique) < 3:
        raise ValueError("Polygon must have at least 3 unique points")
    if coordinates[0] != coordinates[-1]:
        coordinates = coordinates + [coordinates[0]]
    return coordinates


class SurveyCreateSchema(BaseModel):
    user_id: str
    village: str
    plot: str
    coordinates: List[List[float]]

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v):
        return validate_polygon_coords(v)


class SurveyVerifySchema(BaseModel):
    verified_status: bool


class SurveyAdminUpdateSchema(BaseModel):
    village: Optional[str] = None
    plot: Optional[str] = None
    coordinates: Optional[List[List[float]]] = None
    verified_status: Optional[bool] = None
    user_id: Optional[str] = None

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v):
        if v is None:
            return v
        return validate_polygon_coords(v)


class SurveyResponse(BaseModel):
    id: str
    user_id: str
    village: str
    plot: str
    geometry: Optional[Any] = None
    timestamp: datetime
    verified_status: bool

    class Config:
        from_attributes = True
