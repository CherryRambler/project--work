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
        assert schema.password == "Strong1!"

    def test_password_too_short_is_rejected(self):
        with pytest.raises(ValidationError):
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="Sh1!",
                role="viewer",
            )

    def test_password_without_uppercase_is_rejected(self):
        with pytest.raises(ValidationError):
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="lowercase1!",
                role="viewer",
            )

    def test_password_without_lowercase_is_rejected(self):
        with pytest.raises(ValidationError):
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="UPPERCASE1!",
                role="viewer",
            )

    def test_password_without_digit_is_rejected(self):
        with pytest.raises(ValidationError):
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="NoDigits!",
                role="viewer",
            )

    def test_password_without_special_char_is_rejected(self):
        with pytest.raises(ValidationError):
            RegisterSchema(
                user_name="testuser",
                email="test@example.com",
                phone_no="1234567890",
                password="NoSpecial1",
                role="viewer",
            )

    def test_password_change_schema_uses_same_rules(self):
        with pytest.raises(ValidationError):
            PasswordChangeSchema(current_password="whatever", new_password="weak")


class TestRegisterSchemaDefaults:
    def test_role_defaults_to_viewer_when_omitted(self):
        schema = RegisterSchema(
            user_name="testuser",
            email="test@example.com",
            phone_no="1234567890",
            password="Strong1!",
        )
        assert schema.role == "viewer"

    def test_invalid_email_format_is_rejected(self):
        with pytest.raises(ValidationError):
            RegisterSchema(
                user_name="testuser",
                email="not-an-email",
                phone_no="1234567890",
                password="Strong1!",
            )


class TestAreaAssignSchema:
    VALID_SQUARE = [
        [72.5, 18.5],
        [73.0, 18.5],
        [73.0, 19.0],
        [72.5, 19.0],
    ]

    def test_valid_polygon_is_accepted(self):
        schema = AreaAssignSchema(coordinates=self.VALID_SQUARE)
        assert len(schema.coordinates) >= 3

    def test_ring_gets_auto_closed(self):
        """If the first and last point don't match, the validator should
        append the first point to close the polygon ring."""
        schema = AreaAssignSchema(coordinates=self.VALID_SQUARE)
        assert schema.coordinates[0] == schema.coordinates[-1]

    def test_fewer_than_three_points_is_rejected(self):
        with pytest.raises(ValidationError):
            AreaAssignSchema(coordinates=[[72.5, 18.5], [73.0, 18.5]])

    def test_longitude_out_of_range_is_rejected(self):
        with pytest.raises(ValidationError):
            AreaAssignSchema(
                coordinates=[[200.0, 18.5], [73.0, 18.5], [73.0, 19.0]]
            )

    def test_latitude_out_of_range_is_rejected(self):
        with pytest.raises(ValidationError):
            AreaAssignSchema(
                coordinates=[[72.5, 100.0], [73.0, 18.5], [73.0, 19.0]]
            )

    def test_duplicate_points_are_rejected(self):
        with pytest.raises(ValidationError):
            AreaAssignSchema(
                coordinates=[[72.5, 18.5], [72.5, 18.5], [72.5, 18.5]]
            )

    def test_point_with_wrong_length_is_rejected(self):
        """Each point must be exactly [longitude, latitude] - two values."""
        with pytest.raises(ValidationError):
            AreaAssignSchema(
                coordinates=[[72.5, 18.5, 100.0], [73.0, 18.5], [73.0, 19.0]]
            )


class TestPointCheckSchema:
    def test_valid_point_is_accepted(self):
        schema = PointCheckSchema(longitude=72.88, latitude=19.08)
        assert schema.longitude == 72.88
        assert schema.latitude == 19.08

    def test_longitude_out_of_range_is_rejected(self):
        with pytest.raises(ValidationError):
            PointCheckSchema(longitude=181.0, latitude=19.08)

    def test_latitude_out_of_range_is_rejected(self):
        with pytest.raises(ValidationError):
            PointCheckSchema(longitude=72.88, latitude=-91.0)