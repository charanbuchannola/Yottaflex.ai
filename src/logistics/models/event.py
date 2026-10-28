"""Append-Only Event Store Model."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics.models.base import Base

if TYPE_CHECKING:
    from logistics.models.appointment import Appointment


class CheckInEvent(Base):
    """Immutable, append-only domain event in the logistics lifecycle ledger."""
    __tablename__ = "check_in_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    appointment_id: Mapped[str] = mapped_column(String(32), ForeignKey("appointments.appointment_id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    occurrence_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    recorded_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    __table_args__ = (
        UniqueConstraint("appointment_id", "sequence_number", name="uq_appointment_event_sequence"),
        CheckConstraint("sequence_number >= 1", name="check_positive_event_sequence"),
        CheckConstraint(
            "event_type IN ('REQUESTED', 'APPROVED', 'ALLOCATED', 'ARRIVED', 'CHECKED_IN', "
            "'LOADING_STARTED', 'UNLOADING_STARTED', 'LOADING_COMPLETED', 'UNLOADING_COMPLETED', "
            "'DEPARTED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'NO_SHOW')",
            name="check_event_type",
        ),
    )

    # Relationships
    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="events")
