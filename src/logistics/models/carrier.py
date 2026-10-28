"""Carrier and Vehicle Relational Models."""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from logistics.models.appointment import Appointment


class Carrier(Base, TimestampMixin):
    """Freight transportation service provider."""
    __tablename__ = "carriers"

    carrier_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    scac_code: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    vehicles: Mapped[list["Vehicle"]] = relationship("Vehicle", back_populates="carrier", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="carrier")


class Vehicle(Base, TimestampMixin):
    """Tractor, trailer, or box truck dispatched by carrier."""
    __tablename__ = "vehicles"

    vehicle_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    carrier_id: Mapped[str] = mapped_column(String(16), ForeignKey("carriers.carrier_id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(32), default="DRY_VAN", nullable=False)
    license_plate: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    has_liftgate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint("vehicle_type IN ('DRY_VAN', 'REEFER', 'FLATBED', 'BOX_TRUCK')", name="check_vehicle_type"),
    )

    # Relationships
    carrier: Mapped["Carrier"] = relationship("Carrier", back_populates="vehicles")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="vehicle")
