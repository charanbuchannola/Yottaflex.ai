"""Unit and Integrity Tests for Deterministic Transaction Generation."""

from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from logistics.config import PROFILES, ProfileType
from logistics.generators.master_data import generate_master_data
from logistics.generators.transactions import generate_transactions
from logistics.models.appointment import Appointment
from logistics.models.base import Base
from logistics.models.database import create_db_engine


def test_starter_profile_transaction_counts():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    master = generate_master_data(config, seed, start_dt)
    tx = generate_transactions(master, config, seed, start_dt)

    assert len(tx.shipments) == 1000
    assert len(tx.appointments) == 1000
    assert len(tx.appointment_shipments) == 1000
    assert len(tx.shipment_requirements) > 0


def test_transaction_invariants():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    master = generate_master_data(config, seed, start_dt)
    tx = generate_transactions(master, config, seed, start_dt)

    fac_ids = {f.facility_id for f in master.facilities}
    veh_ids = {v.vehicle_id for v in master.vehicles}

    for appt in tx.appointments:
        assert appt.requested_start < appt.requested_end
        assert 30 <= appt.duration_minutes <= 240
        assert appt.status == "REQUESTED"
        assert appt.facility_id in fac_ids
        assert appt.vehicle_id in veh_ids

    for shp in tx.shipments:
        assert 2 <= shp.pallet_count <= 54
        assert shp.weight_kg > 0
        assert shp.due_time > shp.ready_time


def test_transaction_determinism():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    master = generate_master_data(config, seed, start_dt)
    tx_1 = generate_transactions(master, config, seed, start_dt)
    tx_2 = generate_transactions(master, config, seed, start_dt)

    assert [a.appointment_id for a in tx_1.appointments] == [a.appointment_id for a in tx_2.appointments]
    assert [a.duration_minutes for a in tx_1.appointments] == [a.duration_minutes for a in tx_2.appointments]
    assert [a.requested_start for a in tx_1.appointments] == [a.requested_start for a in tx_2.appointments]
    assert [s.pallet_count for s in tx_1.shipments] == [s.pallet_count for s in tx_2.shipments]
    assert [s.weight_kg for s in tx_1.shipments] == [s.weight_kg for s in tx_2.shipments]


def test_full_pipeline_database_persistence():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    master = generate_master_data(config, seed, start_dt)
    tx = generate_transactions(master, config, seed, start_dt)

    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as session:
        # Master data
        session.add_all(master.handling_requirements)
        session.flush()
        session.add_all(master.facilities)
        session.add_all(master.carriers)
        session.flush()
        session.add_all(master.docks)
        session.add_all(master.yard_slots)
        session.add_all(master.vehicles)
        session.add_all(master.labor_shifts)
        session.flush()
        session.add_all(master.dock_capabilities)
        session.flush()

        # Transactions
        session.add_all(tx.shipments)
        session.flush()
        session.add_all(tx.shipment_requirements)
        session.add_all(tx.appointments)
        session.flush()
        session.add_all(tx.appointment_shipments)
        session.commit()

        # Verify query count
        assert session.query(Appointment).count() == 1000

    Base.metadata.drop_all(bind=engine)
