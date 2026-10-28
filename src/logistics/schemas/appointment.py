"""Pydantic V2 Schemas for Appointment Requests and Allocation Responses."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class AppointmentCreateRequest(BaseModel):
    """Schema for submitting an appointment request."""
    facility_id: str = Field(..., description="Target facility business ID (e.g. FAC-001)")
    carrier_id: str = Field(..., description="Contracted carrier business ID (e.g. CARR-001)")
    vehicle_id: str = Field(..., description="Operating vehicle ID (e.g. VEH-0001)")
    appointment_type: str = Field(..., description="Direction: INBOUND or OUTBOUND")
    pallet_count: int = Field(default=20, ge=1, le=60, description="Total pallet count")
    requested_start: datetime = Field(..., description="Requested delivery window start in UTC")
    requested_end: datetime = Field(..., description="Requested delivery window end in UTC")
    handling_codes: list[str] = Field(default_factory=list, description="Handling requirements (REEFER, HAZMAT, etc.)")


class AppointmentResponse(BaseModel):
    """Schema representing current appointment state projection."""
    appointment_id: str
    facility_id: str
    carrier_id: str
    vehicle_id: str
    dock_id: str | None = None
    yard_slot_id: str | None = None
    appointment_type: str
    requested_start: datetime
    requested_end: datetime
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    duration_minutes: int
    status: str
    version: int


class AllocationDecisionResponse(BaseModel):
    """Auditable response returned by allocation engine."""
    decision_id: str
    appointment_id: str
    facility_id: str
    dock_id: str | None = None
    yard_slot_id: str | None = None
    decision_status: str
    rule_evaluated: str
    rejection_reason: str | None = None
    evaluated_at: datetime
    context_metadata: dict[str, Any] = Field(default_factory=dict)
