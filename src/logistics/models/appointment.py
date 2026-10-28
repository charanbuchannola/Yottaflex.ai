"""Appointment, Appointment-Shipment Bridge, and Allocation Decision Models."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from logistics.models.carrier import Carrier, Vehicle
    from logistics.models.event import CheckInEvent
    from logistics.models.facility import Dock, Facility, YardSlot
    from logistics.models.shipment import Shipment


class Appointment(Base, TimestampMixin):
    """Core appointment aggregate and queryable projection."""
    __tablename__ = "appointments"

    appointment_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    facility_id: Mapped[str] = mapped_column(String(16), ForeignKey("facilities.facility_id", ondelete="RESTRICT"), nullable=False, index=True)
    carrier_id: Mapped[str] = mapped_column(String(16), ForeignKey("carriers.carrier_id", ondelete="RESTRICT"), nullable=False, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(16), ForeignKey("vehicles.vehicle_id", ondelete="RESTRICT"), nullable=False, index=True)
    dock_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("docks.dock_id", ondelete="SET NULL"), nullable=True, index=True)
    yard_slot_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("yard_slots.yard_slot_id", ondelete="SET NULL"), nullable=True, index=True)
    appointment_type: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="REQUESTED", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("requested_end > requested_start", name="check_requested_window"),
        CheckConstraint("duration_minutes >= 30 AND duration_minutes <= 240", name="check_duration_range"),
        CheckConstraint("appointment_type IN ('INBOUND', 'OUTBOUND')", name="check_appointment_type"),
        CheckConstraint(
            "status IN ('REQUESTED', 'ALLOCATED', 'REJECTED', 'ARRIVED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW')",
            name="check_appointment_status",
        ),
    )

    # Relationships
    facility: Mapped["Facility"] = relationship("Facility", back_populates="appointments")
    carrier: Mapped["Carrier"] = relationship("Carrier", back_populates="appointments")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="appointments")
    dock: Mapped["Dock | None"] = relationship("Dock", back_populates="appointments")
    yard_slot: Mapped["YardSlot | None"] = relationship("YardSlot", back_populates="appointments")
    shipment_associations: Mapped[list["AppointmentShipment"]] = relationship("AppointmentShipment", back_populates="appointment", cascade="all, delete-orphan")
    decisions: Mapped[list["AllocationDecision"]] = relationship("AllocationDecision", back_populates="appointment", cascade="all, delete-orphan")
    events: Mapped[list["CheckInEvent"]] = relationship("CheckInEvent", back_populates="appointment", cascade="all, delete-orphan")


class AppointmentShipment(Base):
    """Bridge table mapping appointments to contained shipments."""
    __tablename__ = "appointment_shipments"

    appointment_id: Mapped[str] = mapped_column(String(32), ForeignKey("appointments.appointment_id", ondelete="CASCADE"), primary_key=True)
    shipment_id: Mapped[str] = mapped_column(String(32), ForeignKey("shipments.shipment_id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="shipment_associations")
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="appointment_associations")


class AllocationDecision(Base):
    """Auditable log of scheduling engine allocation decisions."""
    __tablename__ = "allocation_decisions"

    decision_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    appointment_id: Mapped[str] = mapped_column(String(32), ForeignKey("appointments.appointment_id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(16), ForeignKey("facilities.facility_id", ondelete="RESTRICT"), nullable=False)
    dock_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("docks.dock_id", ondelete="SET NULL"), nullable=True)
    yard_slot_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("yard_slots.yard_slot_id", ondelete="SET NULL"), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision_status: Mapped[str] = mapped_column(String(16), nullable=False)
    rule_evaluated: Mapped[str] = mapped_column(String(32), nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context_metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    __table_args__ = (
        CheckConstraint("decision_status IN ('ALLOCATED', 'REJECTED')", name="check_decision_status"),
    )

    # Relationships
    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="decisions")
