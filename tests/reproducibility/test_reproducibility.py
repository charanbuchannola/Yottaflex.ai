"""Tests for End-to-End Reproducibility, Checksum Verification, and Canonical Equality."""

from datetime import datetime, timezone
import tempfile
from pathlib import Path
import pytest
from sqlalchemy.orm import Session

from logistics.config import PROFILES, ProfileType
from logistics.exporters.manifest import compute_sha256
from logistics.exporters.relational import export_canonical_csv_and_json
from logistics.generators.master_data import generate_master_data
from logistics.generators.transactions import generate_transactions
from logistics.models.base import Base
from logistics.models.database import create_db_engine
from logistics.scheduler.engine import SchedulingEngine
from logistics.simulation.engine import simulate_operational_events


def run_full_pipeline_to_temp_dir(seed: int, target_dir: Path) -> dict[str, str]:
    """Execute end-to-end generation and export to isolated temporary directory."""
    config = PROFILES[ProfileType.STARTER]
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    master = generate_master_data(config, seed, start_dt)
    tx = generate_transactions(master, config, seed, start_dt)

    engine_sched = SchedulingEngine()
    fac_map = {f.facility_id: f for f in master.facilities}
    docks_by_fac = {f.facility_id: [d for d in master.docks if d.facility_id == f.facility_id] for f in master.facilities}
    yards_by_fac = {f.facility_id: [y for y in master.yard_slots if y.facility_id == f.facility_id] for f in master.facilities}
    shifts_by_fac = {f.facility_id: [s for s in master.labor_shifts if s.facility_id == f.facility_id] for f in master.facilities}

    for appt in tx.appointments[:50]:
        engine_sched.allocate_appointment(
            appointment=appt,
            shipments=[],
            facility=fac_map[appt.facility_id],
            docks=docks_by_fac[appt.facility_id],
            yard_slots=yards_by_fac[appt.facility_id],
            shifts=shifts_by_fac[appt.facility_id],
        )

    events = simulate_operational_events(tx.appointments[:50], seed=seed)

    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as session:
        session.add_all(master.handling_requirements)
        session.add_all(master.facilities)
        session.add_all(master.carriers)
        session.flush()
        session.add_all(master.docks)
        session.add_all(master.yard_slots)
        session.add_all(master.vehicles)
        session.add_all(master.labor_shifts)
        session.add_all(master.dock_capabilities)
        session.flush()

        session.add_all(tx.shipments[:50])
        session.add_all(tx.appointments[:50])
        session.add_all(tx.appointment_shipments[:50])
        session.flush()
        session.add_all(events)
        session.commit()

        csv_dir = target_dir / "csv"
        json_dir = target_dir / "json"
        export_canonical_csv_and_json(session, csv_dir=csv_dir, json_dir=json_dir)

    Base.metadata.drop_all(bind=engine)

    # Compute checksums of all generated files
    hashes = {}
    for p in sorted(target_dir.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(target_dir)).replace("\\", "/")
            hashes[rel] = compute_sha256(p)
    return hashes


def test_identical_seed_produces_bitwise_identical_artifacts():
    seed = 20261022

    with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
        hashes_run_1 = run_full_pipeline_to_temp_dir(seed, Path(dir1))
        hashes_run_2 = run_full_pipeline_to_temp_dir(seed, Path(dir2))

        assert hashes_run_1 == hashes_run_2
        assert len(hashes_run_1) > 0


def test_different_seeds_produce_differing_checksums():
    seed_1 = 20261022
    seed_2 = 99999999

    with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:
        hashes_run_1 = run_full_pipeline_to_temp_dir(seed_1, Path(dir1))
        hashes_run_2 = run_full_pipeline_to_temp_dir(seed_2, Path(dir2))

        # Checksums must differ when seed changes
        assert hashes_run_1 != hashes_run_2
