"""Pydantic Schemas for Event Ledger and Timeline History."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from logistics.schemas.appointment import AppointmentResponse


class EventResponse(BaseModel):
    """Schema representing an immutable event row."""
    event_id: str
    appointment_id: str
    sequence_number: int
    event_type: str
    occurrence_time: datetime
    recorded_time: datetime
    actor: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AppointmentTimelineResponse(BaseModel):
    """Combined appointment projection along with chronological event history."""
    appointment: AppointmentResponse
    timeline: list[EventResponse]
