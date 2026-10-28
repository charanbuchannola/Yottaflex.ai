"""Facility, Dock, YardSlot, and Dock Capability Models."""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from logistics.models.appointment import Appointment
    from logistics.models.labor import LaborShift
    from logistics.models.shipment import HandlingRequirement


class Facility(Base, TimestampMixin):
    """Physical logistics facility / distribution center."""
    __tablename__ = "facilities"

    facility_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    operating_start_hour: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    operating_end_hour: Mapped[int] = mapped_column(Integer, default=22, nullable=False)
    total_yard_slots: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("operating_start_hour >= 0 AND operating_start_hour < operating_end_hour", name="check_op_hours"),
        CheckConstraint("operating_end_hour <= 24", name="check_op_end_hour"),
        CheckConstraint("total_yard_slots >= 0", name="check_yard_slots_non_negative"),
    )

    # Relationships
    docks: Mapped[list["Dock"]] = relationship("Dock", back_populates="facility", cascade="all, delete-orphan")
    yard_slots: Mapped[list["YardSlot"]] = relationship("YardSlot", back_populates="facility", cascade="all, delete-orphan")
    labor_shifts: Mapped[list["LaborShift"]] = relationship("LaborShift", back_populates="facility", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="facility")


class Dock(Base, TimestampMixin):
    """Physical dock door for trailer loading and unloading."""
    __tablename__ = "docks"

    dock_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    facility_id: Mapped[str] = mapped_column(String(16), ForeignKey("facilities.facility_id", ondelete="CASCADE"), nullable=False, index=True)
    dock_number: Mapped[str] = mapped_column(String(16), nullable=False)
    dock_type: Mapped[str] = mapped_column(String(32), default="CROSS_DOCK", nullable=False)
    has_dock_leveler: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    has_cold_chain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_hazmat_permit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("facility_id", "dock_number", name="uq_facility_dock_number"),
        CheckConstraint("dock_type IN ('INBOUND', 'OUTBOUND', 'CROSS_DOCK')", name="check_dock_type"),
    )

    # Relationships
    facility: Mapped["Facility"] = relationship("Facility", back_populates="docks")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="dock")
    capabilities: Mapped[list["DockHandlingCapability"]] = relationship("DockHandlingCapability", back_populates="dock", cascade="all, delete-orphan")


class YardSlot(Base, TimestampMixin):
    """Designated yard trailer staging and parking spot."""
    __tablename__ = "yard_slots"

    yard_slot_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    facility_id: Mapped[str] = mapped_column(String(16), ForeignKey("facilities.facility_id", ondelete="CASCADE"), nullable=False, index=True)
    slot_number: Mapped[str] = mapped_column(String(16), nullable=False)
    slot_type: Mapped[str] = mapped_column(String(32), default="STANDARD", nullable=False)
    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("facility_id", "slot_number", name="uq_facility_yard_slot"),
        CheckConstraint("slot_type IN ('STANDARD', 'REEFER_PLUG', 'STAGING')", name="check_slot_type"),
    )

    # Relationships
    facility: Mapped["Facility"] = relationship("Facility", back_populates="yard_slots")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="yard_slot")


class DockHandlingCapability(Base):
    """Bridge table mapping docks to specialized handling capabilities."""
    __tablename__ = "dock_handling_capabilities"

    dock_id: Mapped[str] = mapped_column(String(32), ForeignKey("docks.dock_id", ondelete="CASCADE"), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(String(16), ForeignKey("handling_requirements.requirement_id", ondelete="CASCADE"), primary_key=True)

    # Relationships
    dock: Mapped["Dock"] = relationship("Dock", back_populates="capabilities")
    requirement: Mapped["HandlingRequirement"] = relationship("HandlingRequirement")
