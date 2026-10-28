"""Integration Tests for Relational Models and Foreign Key Constraints."""

from datetime import datetime, timezone, date
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from logistics.models.base import Base
from logistics.models.database import create_db_engine
from logistics.models.facility import Facility, Dock, YardSlot
from logistics.models.carrier import Carrier, Vehicle
from logistics.models.shipment import Shipment, HandlingRequirement, ShipmentHandlingRequirement
from logistics.models.labor import LaborShift
from logistics.models.appointment import Appointment, AppointmentShipment, AllocationDecision
from logistics.models.event import CheckInEvent
from logistics.models.exception import OperationalException


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database with foreign keys enabled."""
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as session:
        yield session
    Base.metadata.drop_all(bind=engine)


def test_facility_and_dock_foreign_key_and_cascade(db_session: Session):
    facility = Facility(
        facility_id="FAC-001",
        name="Dallas Central Hub",
        timezone="America/Chicago",
        operating_start_hour=6,
        operating_end_hour=22,
        total_yard_slots=15,
        is_active=True,
    )
    dock = Dock(
        dock_id="DOCK-FAC-001-001",
        facility_id="FAC-001",
        dock_number="Bay-01",
        dock_type="CROSS_DOCK",
        has_dock_leveler=True,
        has_cold_chain=False,
        has_hazmat_permit=False,
        is_active=True,
    )
    db_session.add(facility)
    db_session.add(dock)
    db_session.commit()

    # Query facility and verify dock is linked
    f = db_session.get(Facility, "FAC-001")
    assert f is not None
    assert len(f.docks) == 1
    assert f.docks[0].dock_id == "DOCK-FAC-001-001"


def test_orphan_dock_foreign_key_violation(db_session: Session):
    dock = Dock(
        dock_id="DOCK-FAC-999-001",
        facility_id="FAC-999",  # Non-existent parent
        dock_number="Bay-01",
        dock_type="CROSS_DOCK",
    )
    db_session.add(dock)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_operating_hours_check_constraint(db_session: Session):
    # Invalid operating hours: start >= end
    invalid_fac = Facility(
        facility_id="FAC-002",
        name="Invalid Facility",
        operating_start_hour=22,
        operating_end_hour=6,
    )
    db_session.add(invalid_fac)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_appointment_and_event_lifecycle_persistence(db_session: Session):
    now = datetime(2026, 10, 22, 8, 0, 0, tzinfo=timezone.utc)
    now_plus_1h = datetime(2026, 10, 22, 9, 0, 0, tzinfo=timezone.utc)

    # 1. Setup master records
    fac = Facility(facility_id="FAC-001", name="Chicago Crossdock")
    carr = Carrier(carrier_id="CARR-001", name="Yotta Carrier", scac_code="YOTF")
    veh = Vehicle(vehicle_id="VEH-0001", carrier_id="CARR-001", vehicle_type="DRY_VAN", license_plate="IL-1234")
    db_session.add_all([fac, carr, veh])
    db_session.commit()

    # 2. Add appointment
    appt = Appointment(
        appointment_id="APPT-2026-000001",
        facility_id="FAC-001",
        carrier_id="CARR-001",
        vehicle_id="VEH-0001",
        appointment_type="INBOUND",
        requested_start=now,
        requested_end=now_plus_1h,
        duration_minutes=45,
        status="REQUESTED",
    )
    db_session.add(appt)
    db_session.commit()

    # 3. Add append-only event
    event = CheckInEvent(
        event_id="CHECK-APPT-2026-000001-01",
        appointment_id="APPT-2026-000001",
        sequence_number=1,
        event_type="REQUESTED",
        occurrence_time=now,
        actor="SUPPLIER",
        payload_json="{\"note\": \"Initial tender\"}",
    )
    db_session.add(event)
    db_session.commit()

    retrieved = db_session.get(Appointment, "APPT-2026-000001")
    assert retrieved is not None
    assert len(retrieved.events) == 1
    assert retrieved.events[0].sequence_number == 1
