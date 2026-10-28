"""Integration Tests for FastAPI Endpoints and Typer CLI Commands."""

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from logistics.api.app import app
from logistics.main import app as cli_app
from logistics.models.base import Base
from logistics.models.carrier import Carrier, Vehicle
from logistics.models.database import get_db
from logistics.models.facility import Dock, Facility, YardSlot
from logistics.models.labor import LaborShift


@pytest.fixture
def api_test_client():
    """Create a FastAPI test client backed by an isolated in-memory SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    # Seed required facility & carrier master data
    with Session(bind=engine) as session:
        fac = Facility(facility_id="FAC-001", name="Chicago Crossdock", operating_start_hour=6, operating_end_hour=22)
        dock = Dock(dock_id="DOCK-FAC-001-001", facility_id="FAC-001", dock_number="Bay-01", has_cold_chain=True)
        carr = Carrier(carrier_id="CARR-001", name="Fast Logistics", scac_code="FAST")
        veh = Vehicle(vehicle_id="VEH-0001", carrier_id="CARR-001", vehicle_type="DRY_VAN", license_plate="IL-1111")
        shift = LaborShift(
            shift_id="SHIFT-FAC-001-20261022-01",
            facility_id="FAC-001",
            shift_date=datetime(2026, 10, 22).date(),
            start_time=datetime(2026, 10, 22, 6, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc),
            total_workers=10,
            forklift_certified_workers=5,
            hazmat_certified_workers=2,
        )
        session.add_all([fac, dock, carr, veh, shift])
        session.commit()

    def override_get_db():
        with Session(bind=engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_health_check_endpoint(api_test_client):
    response = api_test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "version" in data


def test_create_and_allocate_appointment_lifecycle(api_test_client):
    req_payload = {
        "facility_id": "FAC-001",
        "carrier_id": "CARR-001",
        "vehicle_id": "VEH-0001",
        "appointment_type": "INBOUND",
        "pallet_count": 24,
        "requested_start": "2026-10-22T08:00:00Z",
        "requested_end": "2026-10-22T11:00:00Z",
        "handling_codes": [],
    }

    # 1. Create appointment request
    create_resp = api_test_client.post("/appointments", json=req_payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    appt_id = created_data["appointment_id"]
    assert created_data["status"] == "REQUESTED"
    assert created_data["duration_minutes"] > 0

    # 2. Get appointment details
    get_resp = api_test_client.get(f"/appointments/{appt_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["appointment_id"] == appt_id

    # 3. Allocate appointment
    alloc_resp = api_test_client.post(f"/appointments/{appt_id}/allocate")
    assert alloc_resp.status_code == 200
    alloc_data = alloc_resp.json()
    assert alloc_data["decision_status"] == "ALLOCATED"
    assert alloc_data["dock_id"] == "DOCK-FAC-001-001"

    # 4. Inspect timeline events
    events_resp = api_test_client.get(f"/appointments/{appt_id}/events")
    assert events_resp.status_code == 200
    timeline_data = events_resp.json()
    assert len(timeline_data["timeline"]) >= 1
    assert timeline_data["timeline"][0]["event_type"] == "REQUESTED"


def test_cli_help_and_init():
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    assert "YottaFlex AI Logistics Appointment Scheduling Platform CLI" in result.output

    init_res = runner.invoke(cli_app, ["init"])
    assert init_res.exit_code == 0
    assert "Database successfully initialized" in init_res.output
