"""Explicit Operational Scenario Injection and Anomaly Ground-Truth Generation."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Sequence

from logistics.generators.identifiers import generate_exception_id
from logistics.models.appointment import Appointment
from logistics.models.event import CheckInEvent
from logistics.models.exception import OperationalException
from logistics.models.facility import Dock
from logistics.models.labor import LaborShift
from logistics.models.shipment import Shipment
from logistics.scheduler.engine import intervals_overlap


class AnomalyInjectionResult:
    """Result container of the anomaly injection layer."""
    def __init__(
        self,
        exceptions: list[OperationalException],
        mutated_appointments: list[Appointment],
        mutated_events: list[CheckInEvent],
    ):
        self.exceptions = exceptions
        self.mutated_appointments = mutated_appointments
        self.mutated_events = mutated_events


def inject_anomaly_scenarios(
    appointments: list[Appointment],
    events: list[CheckInEvent],
    shipments: Sequence[Shipment],
    docks: Sequence[Dock],
    shifts: Sequence[LaborShift],
    sim_year: int = 2026,
) -> AnomalyInjectionResult:
    """Inject the 7 required operational exception scenarios with explicit ground-truth provenance."""
    exceptions: list[OperationalException] = []
    events_by_appt: dict[str, list[CheckInEvent]] = {}
    for evt in events:
        events_by_appt.setdefault(evt.appointment_id, []).append(evt)

    # Filter completed/allocated appointments for targeted scenario injection
    completed_appts = [a for a in appointments if a.scheduled_start is not None and a.dock_id is not None]

    exc_seq = 1

    # -------------------------------------------------------------------------
    # SCEN-01: Overlapping Appointments on Same Dock
    # -------------------------------------------------------------------------
    if len(completed_appts) >= 2:
        target_a1 = completed_appts[0]
        target_a2 = completed_appts[1]

        old_start = target_a2.scheduled_start
        target_a2.dock_id = target_a1.dock_id
        target_a2.scheduled_start = target_a1.scheduled_start
        target_a2.scheduled_end = target_a1.scheduled_end

        # Shift target_a2's events so its checkin aligns with its new date
        if old_start and target_a1.scheduled_start:
            delta = target_a1.scheduled_start - old_start
            for evt in events_by_appt.get(target_a2.appointment_id, []):
                evt.occurrence_time += delta

        exc1 = OperationalException(
            exception_id=generate_exception_id(sim_year, exc_seq),
            appointment_id=target_a2.appointment_id,
            scenario_id="SCEN-01",
            issue_type="OVERLAPPING_APPOINTMENTS",
            root_cause=f"Simultaneous reservation on {target_a1.dock_id} overlapping with {target_a1.appointment_id}.",
            expected_outcome="REJECT",
            ground_truth_label="ANOMALY_OVERLAP",
            is_injected_anomaly=True,
        )
        exceptions.append(exc1)
        exc_seq += 1

    # -------------------------------------------------------------------------
    # SCEN-02: Incompatible Dock Assignment (Hazmat to Non-Hazmat Dock)
    # -------------------------------------------------------------------------
    non_hazmat_docks = [d for d in docks if not d.has_hazmat_permit]
    if completed_appts and non_hazmat_docks:
        target_appt = completed_appts[2 % len(completed_appts)]
        # Find a non-hazmat dock that has NO overlapping appointments during target_appt's interval
        free_nh_dock = None
        for nh_dock in non_hazmat_docks:
            has_coll = False
            for other in completed_appts:
                if other.appointment_id != target_appt.appointment_id and other.dock_id == nh_dock.dock_id:
                    if other.scheduled_start and target_appt.scheduled_start and intervals_overlap(
                        other.scheduled_start, other.scheduled_end, target_appt.scheduled_start, target_appt.scheduled_end
                    ):
                        has_coll = True
                        break
            if not has_coll:
                free_nh_dock = nh_dock
                break

        target_dock = free_nh_dock or non_hazmat_docks[0]
        target_appt.dock_id = target_dock.dock_id

        exc2 = OperationalException(
            exception_id=generate_exception_id(sim_year, exc_seq),
            appointment_id=target_appt.appointment_id,
            scenario_id="SCEN-02",
            issue_type="INCOMPATIBLE_DOCK",
            root_cause=f"Shipment requiring HAZMAT permit assigned to non-certified dock {target_appt.dock_id}.",
            expected_outcome="REJECT",
            ground_truth_label="ANOMALY_INCOMPATIBLE_DOCK",
            is_injected_anomaly=True,
        )
        exceptions.append(exc2)
        exc_seq += 1

    # -------------------------------------------------------------------------
    # SCEN-03: Pre-Date Check-In (Check-in 24 hours before scheduled appointment)
    # -------------------------------------------------------------------------
    if len(completed_appts) >= 4:
        target_appt = completed_appts[3]
        appt_events = events_by_appt.get(target_appt.appointment_id, [])
        for evt in appt_events:
            if evt.event_type == "CHECKED_IN" and target_appt.scheduled_start:
                evt.occurrence_time = target_appt.scheduled_start - timedelta(days=1)
                break

        exc3 = OperationalException(
            exception_id=generate_exception_id(sim_year, exc_seq),
            appointment_id=target_appt.appointment_id,
            scenario_id="SCEN-03",
            issue_type="PRE_DATE_CHECKIN",
            root_cause="Driver attempted gate check-in 24 hours prior to scheduled calendar date.",
            expected_outcome="EXCEPTION_FLAG",
            ground_truth_label="ANOMALY_PRE_DATE_CHECKIN",
            is_injected_anomaly=True,
        )
        exceptions.append(exc3)
        exc_seq += 1

    # -------------------------------------------------------------------------
    # SCEN-04: Required Labor Unavailable During Service (Zero collateral damage)
    # -------------------------------------------------------------------------
    # Find a shift with the fewest appointments to avoid collateral corruption
    appts_by_shift = defaultdict(list)
    for a in completed_appts:
        if a.scheduled_start and a.appointment_id not in [e.appointment_id for e in exceptions]:
            for s in shifts:
                if s.facility_id == a.facility_id and s.start_time <= a.scheduled_start <= s.end_time:
                    appts_by_shift[s.shift_id].append((a, s))

    # Pick shift with smallest appointment count (ideally 1)
    best_candidate = None
    for shift_id, appt_pairs in sorted(appts_by_shift.items(), key=lambda x: len(x[1])):
        if appt_pairs:
            best_candidate = appt_pairs[0]
            break

    if best_candidate:
        target_appt, target_shift = best_candidate
        target_shift.forklift_certified_workers = 0

        exc4 = OperationalException(
            exception_id=generate_exception_id(sim_year, exc_seq),
            appointment_id=target_appt.appointment_id,
            scenario_id="SCEN-04",
            issue_type="LABOR_UNAVAILABLE",
            root_cause="Active labor shift has zero forklift certified operators during service window.",
            expected_outcome="REJECT",
            ground_truth_label="ANOMALY_LABOR_UNAVAILABLE",
            is_injected_anomaly=True,
        )
        exceptions.append(exc4)
        exc_seq += 1

    # -------------------------------------------------------------------------
    # SCEN-05: Unrecorded No-Show (Detectable absence past observation window)
    # -------------------------------------------------------------------------
    used_ids = {e.appointment_id for e in exceptions}
    avail_appts = [a for a in completed_appts if a.appointment_id not in used_ids]
    if avail_appts:
        target_appt = avail_appts[0]
        # Keep appointment as ALLOCATED but strip all post-allocation events (driver never arrived!)
        post_alloc_events = events_by_appt.get(target_appt.appointment_id, [])
        filtered_events = [e for e in post_alloc_events if e.event_type in ("REQUESTED", "ALLOCATED")]
        events_by_appt[target_appt.appointment_id] = filtered_events
        target_appt.status = "ALLOCATED"

        exc5 = OperationalException(
            exception_id=generate_exception_id(sim_year, exc_seq),
            appointment_id=target_appt.appointment_id,
            scenario_id="SCEN-05",
            issue_type="UNRECORDED_NO_SHOW",
            root_cause="Vehicle failed to check in within 120-minute post-appointment observation window.",
            expected_outcome="DETECT_ABSENCE",
            ground_truth_label="ANOMALY_UNRECORDED_NO_SHOW",
            is_injected_anomaly=True,
        )
        exceptions.append(exc5)
        exc_seq += 1

    # -------------------------------------------------------------------------
    # SCEN-06: Early Vehicle Arrival (Arrives 180 min early; staged in yard)
    # -------------------------------------------------------------------------
    used_ids = {e.appointment_id for e in exceptions}
    avail_appts = [a for a in completed_appts if a.appointment_id not in used_ids]
    if avail_appts:
        target_appt = avail_appts[0]
        appt_events = events_by_appt.get(target_appt.appointment_id, [])
        for evt in appt_events:
            if evt.event_type == "ARRIVED" and target_appt.scheduled_start:
                evt.occurrence_time = target_appt.scheduled_start - timedelta(minutes=180)
                break

        exc6 = OperationalException(
            exception_id=generate_exception_id(sim_year, exc_seq),
            appointment_id=target_appt.appointment_id,
            scenario_id="SCEN-06",
            issue_type="EARLY_ARRIVAL",
            root_cause="Carrier vehicle arrived 180 minutes prior to scheduled start; staged in yard slot.",
            expected_outcome="QUEUE_WAIT",
            ground_truth_label="OPERATIONAL_EARLY_ARRIVAL",
            is_injected_anomaly=True,
        )
        exceptions.append(exc6)
        exc_seq += 1

    # -------------------------------------------------------------------------
    # SCEN-07: Peak-Hour Congestion Rejections
    # -------------------------------------------------------------------------
    rejected_appts = [a for a in appointments if a.status == "REJECTED"]
    target_rej = rejected_appts[0] if rejected_appts else (appointments[-1] if appointments else None)
    if target_rej and target_rej.appointment_id not in {e.appointment_id for e in exceptions}:
        exc7 = OperationalException(
            exception_id=generate_exception_id(sim_year, exc_seq),
            appointment_id=target_rej.appointment_id,
            scenario_id="SCEN-07",
            issue_type="PEAK_CONGESTION",
            root_cause="Excess demand during peak diurnal dispatch window exceeded available dock capacity.",
            expected_outcome="REJECT",
            ground_truth_label="CONGESTION_REJECTION",
            is_injected_anomaly=True,
        )
        exceptions.append(exc7)

    # Reconstruct flattened event list
    flattened_events: list[CheckInEvent] = []
    for appt in appointments:
        flattened_events.extend(events_by_appt.get(appt.appointment_id, []))

    return AnomalyInjectionResult(
        exceptions=exceptions,
        mutated_appointments=appointments,
        mutated_events=flattened_events,
    )
