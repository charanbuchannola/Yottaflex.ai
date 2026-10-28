"""Discrete Event Operational Simulation Engine."""

from datetime import datetime, timedelta, timezone
import random
from typing import Sequence

from logistics.generators.identifiers import generate_check_in_event_id
from logistics.models.appointment import Appointment
from logistics.models.event import CheckInEvent


def simulate_operational_events(
    appointments: Sequence[Appointment],
    seed: int,
) -> list[CheckInEvent]:
    """Chronologically simulate discrete physical operational events for all appointments."""
    rng = random.Random(seed)
    all_events: list[CheckInEvent] = []

    for appt in appointments:
        if appt.status == "ALLOCATED" and appt.scheduled_start and appt.scheduled_end:
            # 1. REQUESTED event
            req_time = appt.requested_start - timedelta(hours=2)
            e1 = CheckInEvent(
                event_id=generate_check_in_event_id(appt.appointment_id, 1),
                appointment_id=appt.appointment_id,
                sequence_number=1,
                event_type="REQUESTED",
                occurrence_time=req_time,
                recorded_time=req_time,
                actor="CARRIER",
                payload_json='{"status": "TENDERED"}',
            )
            all_events.append(e1)

            # 2. ALLOCATED event
            alloc_time = appt.requested_start - timedelta(hours=1)
            e2 = CheckInEvent(
                event_id=generate_check_in_event_id(appt.appointment_id, 2),
                appointment_id=appt.appointment_id,
                sequence_number=2,
                event_type="ALLOCATED",
                occurrence_time=alloc_time,
                recorded_time=alloc_time,
                actor="SYSTEM",
                payload_json=f'{{"dock_id": "{appt.dock_id}", "yard_slot_id": "{appt.yard_slot_id}"}}',
            )
            all_events.append(e2)

            # 3. ARRIVED event (slight gaussian variation: mean -5m, stdev 10m)
            arrival_offset_min = int(rng.gauss(-5, 10))
            arrived_time = appt.scheduled_start + timedelta(minutes=arrival_offset_min)
            e3 = CheckInEvent(
                event_id=generate_check_in_event_id(appt.appointment_id, 3),
                appointment_id=appt.appointment_id,
                sequence_number=3,
                event_type="ARRIVED",
                occurrence_time=arrived_time,
                recorded_time=arrived_time,
                actor="GATE_SENSOR",
                payload_json=f'{{"vehicle_id": "{appt.vehicle_id}"}}',
            )
            all_events.append(e3)

            # 4. CHECKED_IN event (3 to 6 minutes after arrival)
            checkin_time = arrived_time + timedelta(minutes=rng.randint(3, 6))
            e4 = CheckInEvent(
                event_id=generate_check_in_event_id(appt.appointment_id, 4),
                appointment_id=appt.appointment_id,
                sequence_number=4,
                event_type="CHECKED_IN",
                occurrence_time=checkin_time,
                recorded_time=checkin_time,
                actor="GATE_CLERK",
                payload_json='{"documents_verified": true}',
            )
            all_events.append(e4)

            # 5. SERVICE STARTED event (at scheduled start or after check-in)
            start_event_type = "UNLOADING_STARTED" if appt.appointment_type == "INBOUND" else "LOADING_STARTED"
            service_start = max(appt.scheduled_start, checkin_time + timedelta(minutes=2))
            e5 = CheckInEvent(
                event_id=generate_check_in_event_id(appt.appointment_id, 5),
                appointment_id=appt.appointment_id,
                sequence_number=5,
                event_type=start_event_type,
                occurrence_time=service_start,
                recorded_time=service_start,
                actor="WAREHOUSE_OPERATOR",
                payload_json=f'{{"dock_door": "{appt.dock_id}"}}',
            )
            all_events.append(e5)

            # 6. SERVICE COMPLETED event (service_start + duration - 5m)
            complete_event_type = "UNLOADING_COMPLETED" if appt.appointment_type == "INBOUND" else "LOADING_COMPLETED"
            service_complete = appt.scheduled_end - timedelta(minutes=5)
            e6 = CheckInEvent(
                event_id=generate_check_in_event_id(appt.appointment_id, 6),
                appointment_id=appt.appointment_id,
                sequence_number=6,
                event_type=complete_event_type,
                occurrence_time=service_complete,
                recorded_time=service_complete,
                actor="WAREHOUSE_OPERATOR",
                payload_json='{"bill_of_lading_signed": true}',
            )
            all_events.append(e6)

            # 7. DEPARTED event (at scheduled end)
            e7 = CheckInEvent(
                event_id=generate_check_in_event_id(appt.appointment_id, 7),
                appointment_id=appt.appointment_id,
                sequence_number=7,
                event_type="DEPARTED",
                occurrence_time=appt.scheduled_end,
                recorded_time=appt.scheduled_end,
                actor="GATE_CLERK",
                payload_json='{"gate_pass_issued": true}',
            )
            all_events.append(e7)

            # Update final projection status to COMPLETED
            appt.status = "COMPLETED"

        elif appt.status == "REJECTED":
            # Event 1: REQUESTED
            req_time = appt.requested_start - timedelta(hours=2)
            e1 = CheckInEvent(
                event_id=generate_check_in_event_id(appt.appointment_id, 1),
                appointment_id=appt.appointment_id,
                sequence_number=1,
                event_type="REQUESTED",
                occurrence_time=req_time,
                recorded_time=req_time,
                actor="CARRIER",
                payload_json='{"status": "TENDERED"}',
            )
            all_events.append(e1)

            # Event 2: REJECTED
            rej_time = appt.requested_start - timedelta(hours=1)
            e2 = CheckInEvent(
                event_id=generate_check_in_event_id(appt.appointment_id, 2),
                appointment_id=appt.appointment_id,
                sequence_number=2,
                event_type="REJECTED",
                occurrence_time=rej_time,
                recorded_time=rej_time,
                actor="SYSTEM",
                payload_json='{"rejection_recorded": true}',
            )
            all_events.append(e2)

    return all_events
