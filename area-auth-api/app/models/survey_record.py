from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime, timezone
from uuid import uuid4
from app.db.session import Base


class SurveyRecord(Base):
    __tablename__ = "survey_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    geometry = Column(Geometry(geometry_type="POLYGON", srid=4326), nullable=False)
    village = Column(String(200), nullable=False)
    plot = Column(String(100), nullable=False)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    verified_status = Column(Boolean, default=False, nullable=False)

    audit_logs = relationship(
        "AuditLog",
        back_populates="survey_record",
        foreign_keys="AuditLog.survey_record_id",
        order_by="AuditLog.created_at.desc()",
        lazy="select",
    )

    def __repr__(self):
        return (
            f"<SurveyRecord id={self.id} user={self.user_id} "
            f"village={self.village} verified={self.verified_status}>"
        )