"""Unit and Integrity Tests for Deterministic Master Data Generation."""

from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from logistics.config import PROFILES, ProfileType
from logistics.generators.master_data import generate_master_data
from logistics.models.base import Base
from logistics.models.database import create_db_engine


def test_starter_profile_master_data_counts():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    bundle = generate_master_data(config, seed, start_dt)

    assert len(bundle.facilities) == 2
    assert len(bundle.docks) == 20
    assert len(bundle.yard_slots) == 30
    assert len(bundle.carriers) == 10
    assert len(bundle.vehicles) == 40
    assert len(bundle.handling_requirements) == 5
    # 2 facilities * 7 days * 2 shifts = 28 shifts
    assert len(bundle.labor_shifts) == 28


def test_master_data_determinism():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    bundle_1 = generate_master_data(config, seed, start_dt)
    bundle_2 = generate_master_data(config, seed, start_dt)

    # Identifiers must match exactly
    assert [f.facility_id for f in bundle_1.facilities] == [f.facility_id for f in bundle_2.facilities]
    assert [d.dock_id for d in bundle_1.docks] == [d.dock_id for d in bundle_2.docks]
    assert [d.dock_type for d in bundle_1.docks] == [d.dock_type for d in bundle_2.docks]
    assert [d.has_cold_chain for d in bundle_1.docks] == [d.has_cold_chain for d in bundle_2.docks]
    assert [v.license_plate for v in bundle_1.vehicles] == [v.license_plate for v in bundle_2.vehicles]
    assert [s.total_workers for s in bundle_1.labor_shifts] == [s.total_workers for s in bundle_2.labor_shifts]


def test_master_data_referential_integrity():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    bundle = generate_master_data(config, seed, start_dt)
    fac_ids = {f.facility_id for f in bundle.facilities}
    carr_ids = {c.carrier_id for c in bundle.carriers}

    # Verify every dock references a known facility
    for dock in bundle.docks:
        assert dock.facility_id in fac_ids

    # Verify every yard slot references a known facility
    for slot in bundle.yard_slots:
        assert slot.facility_id in fac_ids

    # Verify every vehicle references a known carrier
    for veh in bundle.vehicles:
        assert veh.carrier_id in carr_ids

    # Verify labor shifts satisfy constraints
    for shift in bundle.labor_shifts:
        assert shift.facility_id in fac_ids
        assert shift.forklift_certified_workers <= shift.total_workers
        assert shift.hazmat_certified_workers <= shift.total_workers
        assert shift.end_time > shift.start_time


def test_master_data_database_persistence():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    bundle = generate_master_data(config, seed, start_dt)

    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as session:
        # Insert in dependency order
        session.add_all(bundle.handling_requirements)
        session.flush()

        session.add_all(bundle.facilities)
        session.add_all(bundle.carriers)
        session.flush()

        session.add_all(bundle.docks)
        session.add_all(bundle.yard_slots)
        session.add_all(bundle.vehicles)
        session.add_all(bundle.labor_shifts)
        session.flush()

        session.add_all(bundle.dock_capabilities)
        session.commit()

    Base.metadata.drop_all(bind=engine)
