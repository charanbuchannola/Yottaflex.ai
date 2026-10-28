"""Append-Only Event Store and Projection Replay Engine."""

from datetime import datetime, timezone
import json
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics.events.lifecycle import get_next_status
from logistics.generators.identifiers import generate_check_in_event_id
from logistics.models.appointment import Appointment
from logistics.models.event import CheckInEvent


class EventStore:
    """Manages append-only event log persistence and rebuildable projections."""

    @staticmethod
    def append_event(
        session: Session,
        appointment: Appointment,
        event_type: str,
        occurrence_time: datetime,
        actor: str = "SYSTEM",
        payload: dict | None = None,
    ) -> CheckInEvent:
        """Append an immutable event and transition the materialized appointment projection."""
        # Determine monotonic sequence number
        stmt = (
            select(CheckInEvent.sequence_number)
            .where(CheckInEvent.appointment_id == appointment.appointment_id)
            .order_by(CheckInEvent.sequence_number.desc())
            .limit(1)
        )
        max_seq = session.scalars(stmt).first() or 0
        next_seq = max_seq + 1

        # Check FSM transition legality (except initial REQUESTED event which sets baseline)
        if next_seq > 1 or event_type != "REQUESTED":
            next_status = get_next_status(appointment.status, event_type)
            appointment.status = next_status.value

        event_id = generate_check_in_event_id(appointment.appointment_id, next_seq)
        event = CheckInEvent(
            event_id=event_id,
            appointment_id=appointment.appointment_id,
            sequence_number=next_seq,
            event_type=event_type,
            occurrence_time=occurrence_time,
            recorded_time=datetime.now(timezone.utc),
            actor=actor,
            payload_json=json.dumps(payload or {}),
        )
        session.add(event)
        return event

    @staticmethod
    def replay_projection(events: Sequence[CheckInEvent]) -> str:
        """Replay an event stream and return the final reconstructed projection status."""
        if not events:
            return "REQUESTED"

        # Deterministic event ordering comparator
        sorted_events = sorted(
            events,
            key=lambda e: (e.occurrence_time, e.sequence_number, e.event_id),
        )

        current_status = "REQUESTED"
        for evt in sorted_events:
            if evt.event_type == "REQUESTED":
                current_status = "REQUESTED"
            else:
                current_status = get_next_status(current_status, evt.event_type).value

        return current_status
