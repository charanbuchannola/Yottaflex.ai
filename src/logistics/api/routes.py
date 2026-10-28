"""FastAPI Route Handlers for Appointments, Allocations, Events, and Operational Metrics."""

from datetime import datetime, timezone
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics.generators.identifiers import generate_appointment_id, generate_shipment_id
from logistics.models.appointment import AllocationDecision, Appointment, AppointmentShipment
from logistics.models.database import get_db
from logistics.models.event import CheckInEvent
from logistics.models.exception import OperationalException
from logistics.models.facility import Dock, Facility, YardSlot
from logistics.models.labor import LaborShift
from logistics.models.shipment import Shipment
from logistics.scheduler.engine import SchedulingEngine
from logistics.scheduler.service_duration import calculate_service_duration
from logistics.schemas.appointment import (
    AllocationDecisionResponse,
    AppointmentCreateRequest,
    AppointmentResponse,
)
from logistics.schemas.event import AppointmentTimelineResponse, EventResponse

router = APIRouter()


@router.get("/health", tags=["System"])
def health_check() -> dict[str, Any]:
    """Basic health check and system metadata."""
    return {
        "status": "HEALTHY",
        "service": "yottaflex-logistics-scheduling",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED, tags=["Appointments"])
def create_appointment(
    payload: AppointmentCreateRequest,
    db: Session = Depends(get_db),
) -> AppointmentResponse:
    """Submit a new appointment request."""
    # Verify facility exists
    facility = db.get(Facility, payload.facility_id)
    if not facility:
        raise HTTPException(status_code=404, detail=f"Facility {payload.facility_id} not found")

    sim_year = payload.requested_start.year
    # Count existing appointments for sequence
    count = db.query(Appointment).count() + 1
    appt_id = generate_appointment_id(sim_year, count)

    duration = calculate_service_duration(
        pallet_count=payload.pallet_count,
        shipment_type=payload.appointment_type,
        handling_codes=payload.handling_codes,
    )

    appointment = Appointment(
        appointment_id=appt_id,
        facility_id=payload.facility_id,
        carrier_id=payload.carrier_id,
        vehicle_id=payload.vehicle_id,
        dock_id=None,
        yard_slot_id=None,
        appointment_type=payload.appointment_type,
        requested_start=payload.requested_start,
        requested_end=payload.requested_end,
        scheduled_start=None,
        scheduled_end=None,
        duration_minutes=duration,
        status="REQUESTED",
    )
    db.add(appointment)

    # Create associated initial event
    event = CheckInEvent(
        event_id=f"CHECK-{appt_id}-01",
        appointment_id=appt_id,
        sequence_number=1,
        event_type="REQUESTED",
        occurrence_time=payload.requested_start,
        recorded_time=datetime.now(timezone.utc),
        actor="CARRIER",
        payload_json=json.dumps({"pallet_count": payload.pallet_count}),
    )
    db.add(event)
    db.commit()
    db.refresh(appointment)

    return AppointmentResponse(
        appointment_id=appointment.appointment_id,
        facility_id=appointment.facility_id,
        carrier_id=appointment.carrier_id,
        vehicle_id=appointment.vehicle_id,
        dock_id=appointment.dock_id,
        yard_slot_id=appointment.yard_slot_id,
        appointment_type=appointment.appointment_type,
        requested_start=appointment.requested_start,
        requested_end=appointment.requested_end,
        scheduled_start=appointment.scheduled_start,
        scheduled_end=appointment.scheduled_end,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status,
        version=appointment.version,
    )


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse, tags=["Appointments"])
def get_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
) -> AppointmentResponse:
    """Retrieve current appointment state projection."""
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail=f"Appointment {appointment_id} not found")

    return AppointmentResponse(
        appointment_id=appt.appointment_id,
        facility_id=appt.facility_id,
        carrier_id=appt.carrier_id,
        vehicle_id=appt.vehicle_id,
        dock_id=appt.dock_id,
        yard_slot_id=appt.yard_slot_id,
        appointment_type=appt.appointment_type,
        requested_start=appt.requested_start,
        requested_end=appt.requested_end,
        scheduled_start=appt.scheduled_start,
        scheduled_end=appt.scheduled_end,
        duration_minutes=appt.duration_minutes,
        status=appt.status,
        version=appt.version,
    )


@router.post("/appointments/{appointment_id}/allocate", response_model=AllocationDecisionResponse, tags=["Appointments"])
def allocate_appointment_endpoint(
    appointment_id: str,
    db: Session = Depends(get_db),
) -> AllocationDecisionResponse:
    """Evaluate and execute allocation against facility dock, yard, and labor constraints."""
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail=f"Appointment {appointment_id} not found")

    facility = db.get(Facility, appt.facility_id)
    docks = list(db.scalars(select(Dock).where(Dock.facility_id == appt.facility_id)).all())
    yard_slots = list(db.scalars(select(YardSlot).where(YardSlot.facility_id == appt.facility_id)).all())
    shifts = list(db.scalars(select(LaborShift).where(LaborShift.facility_id == appt.facility_id)).all())

    # Build existing reservations into scheduler state
    existing_allocations = list(
        db.scalars(select(Appointment).where(Appointment.facility_id == appt.facility_id, Appointment.dock_id.is_not(None))).all()
    )

    engine_sched = SchedulingEngine()
    for existing in existing_allocations:
        if existing.dock_id and existing.scheduled_start and existing.scheduled_end:
            engine_sched.state.dock_reservations[existing.dock_id].append(
                (existing.scheduled_start, existing.scheduled_end, existing.appointment_id)
            )

    decision = engine_sched.allocate_appointment(
        appointment=appt,
        shipments=[],
        facility=facility,
        docks=docks,
        yard_slots=yard_slots,
        shifts=shifts,
        handling_codes=[],
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    metadata = json.loads(decision.context_metadata_json) if decision.context_metadata_json else {}

    return AllocationDecisionResponse(
        decision_id=decision.decision_id,
        appointment_id=decision.appointment_id,
        facility_id=decision.facility_id,
        dock_id=decision.dock_id,
        yard_slot_id=decision.yard_slot_id,
        decision_status=decision.decision_status,
        rule_evaluated=decision.rule_evaluated,
        rejection_reason=decision.rejection_reason,
        evaluated_at=decision.evaluated_at,
        context_metadata=metadata,
    )


@router.get("/appointments/{appointment_id}/events", response_model=AppointmentTimelineResponse, tags=["Events"])
def get_appointment_timeline(
    appointment_id: str,
    db: Session = Depends(get_db),
) -> AppointmentTimelineResponse:
    """Retrieve full append-only event history and audit trail for an appointment."""
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail=f"Appointment {appointment_id} not found")

    events = list(
        db.scalars(
            select(CheckInEvent)
            .where(CheckInEvent.appointment_id == appointment_id)
            .order_by(CheckInEvent.sequence_number.asc())
        ).all()
    )

    timeline = [
        EventResponse(
            event_id=e.event_id,
            appointment_id=e.appointment_id,
            sequence_number=e.sequence_number,
            event_type=e.event_type,
            occurrence_time=e.occurrence_time,
            recorded_time=e.recorded_time,
            actor=e.actor,
            payload=json.loads(e.payload_json) if e.payload_json else {},
        )
        for e in events
    ]

    appt_resp = AppointmentResponse(
        appointment_id=appt.appointment_id,
        facility_id=appt.facility_id,
        carrier_id=appt.carrier_id,
        vehicle_id=appt.vehicle_id,
        dock_id=appt.dock_id,
        yard_slot_id=appt.yard_slot_id,
        appointment_type=appt.appointment_type,
        requested_start=appt.requested_start,
        requested_end=appt.requested_end,
        scheduled_start=appt.scheduled_start,
        scheduled_end=appt.scheduled_end,
        duration_minutes=appt.duration_minutes,
        status=appt.status,
        version=appt.version,
    )
    return AppointmentTimelineResponse(appointment=appt_resp, timeline=timeline)


@router.get("/exceptions", tags=["Exceptions"])
def list_operational_exceptions(
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve recorded operational exceptions and ground-truth anomalies."""
    exceptions = list(db.scalars(select(OperationalException)).all())
    return [
        {
            "exception_id": e.exception_id,
            "appointment_id": e.appointment_id,
            "scenario_id": e.scenario_id,
            "issue_type": e.issue_type,
            "root_cause": e.root_cause,
            "expected_outcome": e.expected_outcome,
            "ground_truth_label": e.ground_truth_label,
            "is_injected_anomaly": e.is_injected_anomaly,
        }
        for e in exceptions
    ]


@router.get("/metrics", tags=["Analytics"])
def get_metrics(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve live operational performance and resource utilization metrics."""
    from logistics.analytics.metrics import calculate_evaluation_metrics
    return calculate_evaluation_metrics(db)
