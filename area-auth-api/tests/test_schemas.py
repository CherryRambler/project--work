"""
Tests for app/schemas/auth.py and app/schemas/area.py

Pydantic validators are also "pure" in testing terms: you build the
schema with some input and check whether it accepts or rejects it.
No database involved.
"""
import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterSchema, PasswordChangeSchema
from app.schemas.area import AreaAssignSchema, PointCheckSchema


class TestPasswordStrengthValidation:
    """These rules are shared by RegisterSchema and PasswordChangeSchema,
    so testing them through RegisterSchema covers both."""

    def test_valid_strong_password_is_accepted(self):
        schema = RegisterSchema(
            user_name="testuser",
            email="test@example.com",
            phone_no="1234567890",
            password="Strong1!",
            role="viewer",
        )
        print(f"\n[DEBUG] RegisterSchema created successfully")
        print(f"[DEBUG] schema.password : {schema.password!r}")
        assert schema.password == "Strong1!"

    def test_password_too_short_is_rejected(self):
        print(f"\n[DEBUG] attempting RegisterSchema with password='Sh1!' (too short)")
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="Sh1!",
                role="viewer",
            )
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_password_without_uppercase_is_rejected(self):
        print(f"\n[DEBUG] attempting RegisterSchema with password='lowercase1!' (no uppercase)")
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="lowercase1!",
                role="viewer",
            )
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_password_without_lowercase_is_rejected(self):
        print(f"\n[DEBUG] attempting RegisterSchema with password='UPPERCASE1!' (no lowercase)")
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="UPPERCASE1!",
                role="viewer",
            )
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_password_without_digit_is_rejected(self):
        print(f"\n[DEBUG] attempting RegisterSchema with password='NoDigits!' (no digit)")
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="NoDigits!",
                role="viewer",
            )
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_password_without_special_char_is_rejected(self):
        print(f"\n[DEBUG] attempting RegisterSchema with password='NoSpecial1' (no special char)")
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="NoSpecial1",
                role="viewer",
            )
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_password_change_schema_uses_same_rules(self):
        print(f"\n[DEBUG] attempting PasswordChangeSchema with new_password='weak'")
        with pytest.raises(ValidationError) as exc_info:
            PasswordChangeSchema(current_password="whatever", new_password="weak")
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")


class TestRegisterSchemaDefaults:
    def test_role_defaults_to_viewer_when_omitted(self):
        schema = RegisterSchema(
            user_name="testuser",
            email="test@example.com",
            phone_no="1234567890",
            password="Strong1!",
        )
        print(f"\n[DEBUG] RegisterSchema created (no role specified)")
        print(f"[DEBUG] schema.role : {schema.role!r}")
        assert schema.role == "viewer"

    def test_invalid_email_format_is_rejected(self):
        print(f"\n[DEBUG] attempting RegisterSchema with email='not-an-email'")
        with pytest.raises(ValidationError) as exc_info:
            RegisterSchema(
                user_name="testuser",
                email="not-an-email",
                phone_no="1234567890",
                password="Strong1!",
            )
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")


class TestAreaAssignSchema:
    VALID_SQUARE = [
        [72.5, 18.5],
        [73.0, 18.5],
        [73.0, 19.0],
        [72.5, 19.0],
    ]

    def test_valid_polygon_is_accepted(self):
        schema = AreaAssignSchema(coordinates=self.VALID_SQUARE)
        print(f"\n[DEBUG] input coordinates  : {self.VALID_SQUARE}")
        print(f"[DEBUG] schema.coordinates : {schema.coordinates}")
        print(f"[DEBUG] coordinate count   : {len(schema.coordinates)}")
        assert len(schema.coordinates) >= 3

    def test_ring_gets_auto_closed(self):
        """If the first and last point don't match, the validator should
        append the first point to close the polygon ring."""
        schema = AreaAssignSchema(coordinates=self.VALID_SQUARE)
        print(f"\n[DEBUG] input coordinates  : {self.VALID_SQUARE}")
        print(f"[DEBUG] schema.coordinates : {schema.coordinates}")
        print(f"[DEBUG] first point : {schema.coordinates[0]}")
        print(f"[DEBUG] last point  : {schema.coordinates[-1]}")
        print(f"[DEBUG] ring closed : {schema.coordinates[0] == schema.coordinates[-1]}")
        assert schema.coordinates[0] == schema.coordinates[-1]

    def test_fewer_than_three_points_is_rejected(self):
        coords = [[72.5, 18.5], [73.0, 18.5]]
        print(f"\n[DEBUG] attempting AreaAssignSchema with only 2 points: {coords}")
        with pytest.raises(ValidationError) as exc_info:
            AreaAssignSchema(coordinates=coords)
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_longitude_out_of_range_is_rejected(self):
        coords = [[200.0, 18.5], [73.0, 18.5], [73.0, 19.0]]
        print(f"\n[DEBUG] attempting AreaAssignSchema with longitude=200.0 (out of range): {coords}")
        with pytest.raises(ValidationError) as exc_info:
            AreaAssignSchema(coordinates=coords)
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_latitude_out_of_range_is_rejected(self):
        coords = [[72.5, 100.0], [73.0, 18.5], [73.0, 19.0]]
        print(f"\n[DEBUG] attempting AreaAssignSchema with latitude=100.0 (out of range): {coords}")
        with pytest.raises(ValidationError) as exc_info:
            AreaAssignSchema(coordinates=coords)
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_duplicate_points_are_rejected(self):
        coords = [[72.5, 18.5], [72.5, 18.5], [72.5, 18.5]]
        print(f"\n[DEBUG] attempting AreaAssignSchema with all-duplicate points: {coords}")
        with pytest.raises(ValidationError) as exc_info:
            AreaAssignSchema(coordinates=coords)
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_point_with_wrong_length_is_rejected(self):
        """Each point must be exactly [longitude, latitude] - two values."""
        coords = [[72.5, 18.5, 100.0], [73.0, 18.5], [73.0, 19.0]]
        print(f"\n[DEBUG] attempting AreaAssignSchema with 3-element point: {coords}")
        with pytest.raises(ValidationError) as exc_info:
            AreaAssignSchema(coordinates=coords)
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")


class TestPointCheckSchema:
    def test_valid_point_is_accepted(self):
        schema = PointCheckSchema(longitude=72.88, latitude=19.08)
        print(f"\n[DEBUG] PointCheckSchema created: longitude={schema.longitude}, latitude={schema.latitude}")
        assert schema.longitude == 72.88
        assert schema.latitude == 19.08

    def test_longitude_out_of_range_is_rejected(self):
        print(f"\n[DEBUG] attempting PointCheckSchema with longitude=181.0 (out of range)")
        with pytest.raises(ValidationError) as exc_info:
            PointCheckSchema(longitude=181.0, latitude=19.08)
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")

    def test_latitude_out_of_range_is_rejected(self):
        print(f"\n[DEBUG] attempting PointCheckSchema with latitude=-91.0 (out of range)")
        with pytest.raises(ValidationError) as exc_info:
            PointCheckSchema(longitude=72.88, latitude=-91.0)
        print(f"[DEBUG] ValidationError raised: {exc_info.value.errors()}")
