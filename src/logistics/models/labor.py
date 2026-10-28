"""Labor Shift Relational Model."""

from datetime import date, datetime
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from logistics.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from logistics.models.facility import Facility


class LaborShift(Base, TimestampMixin):
    """Scheduled warehouse labor shift providing handling and forklift capacity."""
    __tablename__ = "labor_shifts"

    shift_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    facility_id: Mapped[str] = mapped_column(String(16), ForeignKey("facilities.facility_id", ondelete="CASCADE"), nullable=False, index=True)
    shift_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_workers: Mapped[int] = mapped_column(Integer, nullable=False)
    forklift_certified_workers: Mapped[int] = mapped_column(Integer, nullable=False)
    hazmat_certified_workers: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_shift_time_order"),
        CheckConstraint("total_workers > 0", name="check_total_workers_positive"),
        CheckConstraint("forklift_certified_workers >= 0 AND forklift_certified_workers <= total_workers", name="check_forklift_workers_range"),
        CheckConstraint("hazmat_certified_workers >= 0 AND hazmat_certified_workers <= total_workers", name="check_hazmat_workers_range"),
    )

    # Relationships
    facility: Mapped["Facility"] = relationship("Facility", back_populates="labor_shifts")
