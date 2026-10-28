"""Operational Exception and Segregated Ground-Truth Model."""

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from logistics.models.base import Base, TimestampMixin


class OperationalException(Base, TimestampMixin):
    """Ground-truth repository of operational exceptions and injected anomalies."""
    __tablename__ = "operational_exceptions"

    exception_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    appointment_id: Mapped[str] = mapped_column(String(32), ForeignKey("appointments.appointment_id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    expected_outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    ground_truth_label: Mapped[str] = mapped_column(String(32), nullable=False)
    is_injected_anomaly: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "issue_type IN ('OVERLAPPING_APPOINTMENTS', 'INCOMPATIBLE_DOCK', 'PRE_DATE_CHECKIN', "
            "'LABOR_UNAVAILABLE', 'UNRECORDED_NO_SHOW', 'EARLY_ARRIVAL', 'PEAK_CONGESTION')",
            name="check_exception_issue_type",
        ),
    )
