# app/models/audit_log.py
from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from uuid import uuid4
from app.db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    user_email = Column(String, nullable=True)

    action = Column(String(100), nullable=False)          # e.g. SURVEY_VERIFIED
    change_type = Column(String(50), nullable=True)       # e.g. VERIFY, UPDATE, CREATE

    resource = Column(String(200), nullable=True)         # e.g. "survey:uuid"
    survey_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("survey_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    changes = Column(JSONB, nullable=True)                # {"field": ..., "old": ..., "new": ...}

    detail = Column(Text, nullable=True)

    ip_address = Column(String(50), nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    survey_record = relationship(
        "SurveyRecord",
        back_populates="audit_logs",
        foreign_keys=[survey_record_id],
    )

    def __repr__(self):
        return f"<AuditLog action={self.action} change_type={self.change_type} user={self.user_email}>"