"""Unit Tests for Event Store, Lifecycle FSM, Simulation, and Anomaly Injection."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session

from logistics.events.lifecycle import InvalidStateTransitionError, get_next_status
from logistics.events.store import EventStore
from logistics.generators.identifiers import generate_appointment_id
from logistics.models.appointment import Appointment
from logistics.models.base import Base
from logistics.models.carrier import Carrier, Vehicle
from logistics.models.database import create_db_engine
from logistics.models.facility import Dock, Facility
from logistics.models.labor import LaborShift
from logistics.simulation.anomalies import inject_anomaly_scenarios
from logistics.simulation.engine import simulate_operational_events


def test_fsm_legal_transitions():
    assert get_next_status("REQUESTED", "ALLOCATED") == "ALLOCATED"
    assert get_next_status("ALLOCATED", "ARRIVED") == "ARRIVED"
    assert get_next_status("ARRIVED", "CHECKED_IN") == "CHECKED_IN"
    assert get_next_status("CHECKED_IN", "UNLOADING_STARTED") == "IN_PROGRESS"
    assert get_next_status("IN_PROGRESS", "UNLOADING_COMPLETED") == "IN_PROGRESS"
    assert get_next_status("IN_PROGRESS", "DEPARTED") == "COMPLETED"


def test_fsm_illegal_transitions():
    with pytest.raises(InvalidStateTransitionError):
        # Cannot jump from REQUESTED directly to DEPARTED
        get_next_status("REQUESTED", "DEPARTED")

    with pytest.raises(InvalidStateTransitionError):
        # Cannot check in after already completed
        get_next_status("COMPLETED", "CHECKED_IN")


def test_event_store_and_replay_projection():
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    t0 = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)

    with Session(bind=engine) as session:
        fac = Facility(facility_id="FAC-001", name="Dallas Central Hub")
        carr = Carrier(carrier_id="CARR-001", name="Apex Logistics", scac_code="APEX")
        veh = Vehicle(vehicle_id="VEH-0001", carrier_id="CARR-001", vehicle_type="DRY_VAN", license_plate="TX-1001")
        session.add_all([fac, carr, veh])
        session.flush()

        appt = Appointment(
            appointment_id="APPT-2026-000001",
            facility_id="FAC-001",
            carrier_id="CARR-001",
            vehicle_id="VEH-0001",
            appointment_type="INBOUND",
            requested_start=t0,
            requested_end=t0 + timedelta(hours=2),
            duration_minutes=60,
            status="REQUESTED",
        )
        session.add(appt)
        session.commit()

        # Append events sequentially
        e1 = EventStore.append_event(session, appt, "REQUESTED", t0)
        assert e1.sequence_number == 1

        e2 = EventStore.append_event(session, appt, "ALLOCATED", t0 + timedelta(minutes=10))
        assert e2.sequence_number == 2
        assert appt.status == "ALLOCATED"

        e3 = EventStore.append_event(session, appt, "ARRIVED", t0 + timedelta(minutes=30))
        assert e3.sequence_number == 3
        assert appt.status == "ARRIVED"

        # Test replay projection
        reconstructed = EventStore.replay_projection([e1, e2, e3])
        assert reconstructed == "ARRIVED"

    Base.metadata.drop_all(bind=engine)


def test_simulate_operational_events():
    t_start = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 22, 11, 0, tzinfo=timezone.utc)

    appt = Appointment(
        appointment_id="APPT-2026-000001",
        facility_id="FAC-001",
        carrier_id="CARR-001",
        vehicle_id="VEH-0001",
        dock_id="DOCK-FAC-001-001",
        appointment_type="INBOUND",
        requested_start=t_start,
        requested_end=t_end + timedelta(hours=2),
        scheduled_start=t_start,
        scheduled_end=t_end,
        duration_minutes=60,
        status="ALLOCATED",
    )

    events = simulate_operational_events([appt], seed=20261022)
    assert len(events) == 7
    seq_nums = [e.sequence_number for e in events]
    assert seq_nums == [1, 2, 3, 4, 5, 6, 7]
    assert appt.status == "COMPLETED"


def test_inject_the_7_anomaly_scenarios():
    t_start = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 22, 11, 0, tzinfo=timezone.utc)

    appts = []
    for i in range(1, 10):
        a = Appointment(
            appointment_id=generate_appointment_id(2026, i),
            facility_id="FAC-001",
            carrier_id="CARR-001",
            vehicle_id="VEH-0001",
            dock_id="DOCK-FAC-001-001",
            appointment_type="INBOUND",
            requested_start=t_start,
            requested_end=t_end,
            scheduled_start=t_start,
            scheduled_end=t_end,
            duration_minutes=60,
            status="ALLOCATED",
        )
        appts.append(a)

    events = simulate_operational_events(appts, seed=20261022)

    docks = [
        Dock(dock_id="DOCK-FAC-001-001", facility_id="FAC-001", dock_number="Bay-01", has_hazmat_permit=False)
    ]
    shifts = [
        LaborShift(
            shift_id="SHIFT-FAC-001-20261022-01",
            facility_id="FAC-001",
            start_time=t_start,
            end_time=t_end,
            total_workers=10,
            forklift_certified_workers=4,
            hazmat_certified_workers=2,
        )
    ]

    res = inject_anomaly_scenarios(
        appointments=appts,
        events=events,
        shipments=[],
        docks=docks,
        shifts=shifts,
        sim_year=2026,
    )

    scenario_ids = [exc.scenario_id for exc in res.exceptions]
    assert "SCEN-01" in scenario_ids
    assert "SCEN-02" in scenario_ids
    assert "SCEN-03" in scenario_ids
    assert "SCEN-04" in scenario_ids
    assert "SCEN-05" in scenario_ids
    assert "SCEN-06" in scenario_ids
    assert len(res.exceptions) >= 6
