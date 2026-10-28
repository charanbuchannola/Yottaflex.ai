"""Unit Tests for Deterministic Allocation Engine and Constraint Evaluation."""

from datetime import date, datetime, timedelta, timezone
import pytest

from logistics.models.appointment import Appointment
from logistics.models.facility import Dock, Facility, YardSlot
from logistics.models.labor import LaborShift
from logistics.models.shipment import Shipment
from logistics.scheduler.engine import SchedulingEngine, SchedulerState, intervals_overlap
from logistics.scheduler.rules import RejectionCode


@pytest.fixture
def base_context():
    """Setup a standard single-facility context with 2 docks, 1 yard slot, and 1 shift."""
    fac = Facility(
        facility_id="FAC-001",
        name="Dallas DC",
        operating_start_hour=6,
        operating_end_hour=22,
        total_yard_slots=5,
    )
    docks = [
        Dock(
            dock_id="DOCK-FAC-001-001",
            facility_id="FAC-001",
            dock_number="Bay-01",
            dock_type="CROSS_DOCK",
            has_dock_leveler=True,
            has_cold_chain=False,
            has_hazmat_permit=False,
            is_active=True,
        ),
        Dock(
            dock_id="DOCK-FAC-001-002",
            facility_id="FAC-001",
            dock_number="Bay-02",
            dock_type="CROSS_DOCK",
            has_dock_leveler=True,
            has_cold_chain=True,
            has_hazmat_permit=True,
            is_active=True,
        ),
    ]
    yard_slots = [
        YardSlot(
            yard_slot_id="YARD-FAC-001-001",
            facility_id="FAC-001",
            slot_number="Y-01",
            slot_type="STANDARD",
        )
    ]
    shifts = [
        LaborShift(
            shift_id="SHIFT-FAC-001-20261022-01",
            facility_id="FAC-001",
            shift_date=date(2026, 10, 22),
            start_time=datetime(2026, 10, 22, 6, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc),
            total_workers=10,
            forklift_certified_workers=5,
            hazmat_certified_workers=2,
        )
    ]
    return fac, docks, yard_slots, shifts


def test_half_open_interval_overlap_logic():
    t08 = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)
    t09 = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    t10 = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)

    # Touching boundary: [08:00, 09:00) and [09:00, 10:00) do NOT overlap
    assert not intervals_overlap(t08, t09, t09, t10)

    # True overlap: [08:00, 09:30) and [09:00, 10:00) DO overlap
    t0930 = datetime(2026, 10, 22, 9, 30, tzinfo=timezone.utc)
    assert intervals_overlap(t08, t0930, t09, t10)


def test_successful_allocation_and_tie_breaking(base_context):
    fac, docks, yard_slots, shifts = base_context
    engine = SchedulingEngine()

    t_start = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 22, 11, 0, tzinfo=timezone.utc)

    appt = Appointment(
        appointment_id="APPT-2026-000001",
        facility_id="FAC-001",
        carrier_id="CARR-001",
        vehicle_id="VEH-0001",
        appointment_type="INBOUND",
        requested_start=t_start,
        requested_end=t_end,
        duration_minutes=60,
        status="REQUESTED",
    )

    decision = engine.allocate_appointment(
        appointment=appt,
        shipments=[],
        facility=fac,
        docks=docks,
        yard_slots=yard_slots,
        shifts=shifts,
        handling_codes=[],
    )

    assert decision.decision_status == "ALLOCATED"
    assert appt.status == "ALLOCATED"
    assert appt.scheduled_start == t_start
    assert appt.scheduled_end == t_start + timedelta(minutes=60)
    # Tie-breaking: DOCK-FAC-001-001 is sorted before DOCK-FAC-001-002
    assert appt.dock_id == "DOCK-FAC-001-001"


def test_dock_conflict_and_sequential_slot_search(base_context):
    fac, docks, yard_slots, shifts = base_context
    # Restrict to only 1 dock
    single_dock = [docks[0]]
    engine = SchedulingEngine()

    t_start = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)

    appt1 = Appointment(
        appointment_id="APPT-2026-000001",
        facility_id="FAC-001",
        carrier_id="CARR-001",
        vehicle_id="VEH-0001",
        appointment_type="INBOUND",
        requested_start=t_start,
        requested_end=t_end,
        duration_minutes=60,
        status="REQUESTED",
    )
    appt2 = Appointment(
        appointment_id="APPT-2026-000002",
        facility_id="FAC-001",
        carrier_id="CARR-001",
        vehicle_id="VEH-0002",
        appointment_type="INBOUND",
        requested_start=t_start,
        requested_end=t_end,
        duration_minutes=60,
        status="REQUESTED",
    )

    dec1 = engine.allocate_appointment(appt1, [], fac, single_dock, yard_slots, shifts)
    assert dec1.decision_status == "ALLOCATED"
    assert appt1.scheduled_start == t_start
    assert appt1.scheduled_end == t_start + timedelta(minutes=60)

    dec2 = engine.allocate_appointment(appt2, [], fac, single_dock, yard_slots, shifts)
    assert dec2.decision_status == "ALLOCATED"
    # Appt2 should automatically roll to the next 60m block: 09:00 to 10:00!
    assert appt2.scheduled_start == t_start + timedelta(minutes=60)
    assert appt2.scheduled_end == t_end


def test_rejection_when_window_saturated(base_context):
    fac, docks, yard_slots, shifts = base_context
    single_dock = [docks[0]]
    engine = SchedulingEngine()

    # Exact 60m window
    t_start = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)

    appt1 = Appointment(
        appointment_id="APPT-2026-000001",
        facility_id="FAC-001",
        carrier_id="CARR-001",
        vehicle_id="VEH-0001",
        appointment_type="INBOUND",
        requested_start=t_start,
        requested_end=t_end,
        duration_minutes=60,
        status="REQUESTED",
    )
    appt2 = Appointment(
        appointment_id="APPT-2026-000002",
        facility_id="FAC-001",
        carrier_id="CARR-001",
        vehicle_id="VEH-0002",
        appointment_type="INBOUND",
        requested_start=t_start,
        requested_end=t_end,
        duration_minutes=60,
        status="REQUESTED",
    )

    dec1 = engine.allocate_appointment(appt1, [], fac, single_dock, yard_slots, shifts)
    assert dec1.decision_status == "ALLOCATED"

    # Appt2 has no room left in the 1-hour window
    dec2 = engine.allocate_appointment(appt2, [], fac, single_dock, yard_slots, shifts)
    assert dec2.decision_status == "REJECTED"
    assert dec2.rejection_reason == RejectionCode.ERR_DOCK_OCCUPIED.value


def test_rejection_outside_operating_hours(base_context):
    fac, docks, yard_slots, shifts = base_context
    engine = SchedulingEngine()

    # Facility operating hours are 06:00 to 22:00
    # Request at 02:00 AM
    t_start = datetime(2026, 10, 22, 2, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 22, 4, 0, tzinfo=timezone.utc)

    appt = Appointment(
        appointment_id="APPT-2026-000003",
        facility_id="FAC-001",
        carrier_id="CARR-001",
        vehicle_id="VEH-0001",
        appointment_type="INBOUND",
        requested_start=t_start,
        requested_end=t_end,
        duration_minutes=60,
        status="REQUESTED",
    )

    dec = engine.allocate_appointment(appt, [], fac, docks, yard_slots, shifts)
    assert dec.decision_status == "REJECTED"
    assert dec.rejection_reason == RejectionCode.ERR_OUTSIDE_OPERATING_HOURS.value


def test_rejection_incompatible_hazmat(base_context):
    fac, docks, yard_slots, shifts = base_context
    # Remove the hazmat certified dock
    non_hazmat_docks = [docks[0]]  # Bay-01 has no hazmat permit
    engine = SchedulingEngine()

    t_start = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)

    appt = Appointment(
        appointment_id="APPT-2026-000004",
        facility_id="FAC-001",
        carrier_id="CARR-001",
        vehicle_id="VEH-0001",
        appointment_type="INBOUND",
        requested_start=t_start,
        requested_end=t_end,
        duration_minutes=60,
        status="REQUESTED",
    )

    dec = engine.allocate_appointment(
        appt, [], fac, non_hazmat_docks, yard_slots, shifts, handling_codes=["HAZMAT"]
    )
    assert dec.decision_status == "REJECTED"
    assert dec.rejection_reason == RejectionCode.ERR_INCOMPATIBLE_HAZMAT.value
