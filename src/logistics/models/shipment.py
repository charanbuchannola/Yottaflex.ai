"""Shipment and Handling Requirement Relational Models."""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from logistics.models.appointment import AppointmentShipment


class HandlingRequirement(Base):
    """Master catalog of handling certifications and requirements."""
    __tablename__ = "handling_requirements"

    requirement_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        CheckConstraint("code IN ('REEFER', 'HAZMAT', 'FRAGILE', 'LIFTGATE', 'OVERSIZED')", name="check_req_code"),
    )


class Shipment(Base, TimestampMixin):
    """Physical shipment lot scheduled for intake or outbound dispatch."""
    __tablename__ = "shipments"

    shipment_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tracking_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    shipment_type: Mapped[str] = mapped_column(String(16), nullable=False)
    pallet_count: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    ready_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False)

    __table_args__ = (
        CheckConstraint("pallet_count >= 1 AND pallet_count <= 60", name="check_pallet_count_range"),
        CheckConstraint("weight_kg > 0", name="check_weight_positive"),
        CheckConstraint("due_time > ready_time", name="check_shipment_time_order"),
        CheckConstraint("shipment_type IN ('INBOUND', 'OUTBOUND')", name="check_shipment_type"),
        CheckConstraint("status IN ('CREATED', 'ASSIGNED', 'IN_TRANSIT', 'DELIVERED')", name="check_shipment_status"),
    )

    # Relationships
    requirements: Mapped[list["ShipmentHandlingRequirement"]] = relationship("ShipmentHandlingRequirement", back_populates="shipment", cascade="all, delete-orphan")
    appointment_associations: Mapped[list["AppointmentShipment"]] = relationship("AppointmentShipment", back_populates="shipment")


class ShipmentHandlingRequirement(Base):
    """Bridge table mapping shipments to handling requirements."""
    __tablename__ = "shipment_handling_requirements"

    shipment_id: Mapped[str] = mapped_column(String(32), ForeignKey("shipments.shipment_id", ondelete="CASCADE"), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(String(16), ForeignKey("handling_requirements.requirement_id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="requirements")
    requirement: Mapped["HandlingRequirement"] = relationship("HandlingRequirement")
