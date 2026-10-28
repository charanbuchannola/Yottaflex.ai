"""Tests for Automated Dual-Mode Validation Framework."""

from collections import defaultdict
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from logistics.config import PROFILES, ProfileType
from logistics.generators.master_data import generate_master_data
from logistics.generators.transactions import generate_transactions
from logistics.models.base import Base
from logistics.models.database import create_db_engine
from logistics.scheduler.engine import SchedulingEngine
from logistics.simulation.anomalies import inject_anomaly_scenarios
from logistics.simulation.engine import simulate_operational_events
from logistics.validators.runner import ValidatorRunner


def populate_db(session: Session, master, tx, appointments, events, exceptions=None):
    """Helper to populate database cleanly in dependency order."""
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

    appt_ids = {a.appointment_id for a in appointments}
    matched_shipments = tx.shipments[:len(appointments)]
    shp_ids = {s.shipment_id for s in matched_shipments}

    session.add_all(matched_shipments)
    matched_reqs = [r for r in tx.shipment_requirements if r.shipment_id in shp_ids]
    session.add_all(matched_reqs)
    session.add_all(appointments)
    matched_assocs = [assoc for assoc in tx.appointment_shipments if assoc.appointment_id in appt_ids]
    session.add_all(matched_assocs)
    session.flush()

    session.add_all(events)
    if exceptions:
        session.add_all(exceptions)
    session.commit()


def test_baseline_validation_produces_zero_violations():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    master = generate_master_data(config, seed, start_dt)
    tx = generate_transactions(master, config, seed, start_dt)

    appts = tx.appointments[:40]
    engine_sched = SchedulingEngine()
    fac_map = {f.facility_id: f for f in master.facilities}
    docks_by_fac = {f.facility_id: [d for d in master.docks if d.facility_id == f.facility_id] for f in master.facilities}
    yards_by_fac = {f.facility_id: [y for y in master.yard_slots if y.facility_id == f.facility_id] for f in master.facilities}
    shifts_by_fac = {f.facility_id: [s for s in master.labor_shifts if s.facility_id == f.facility_id] for f in master.facilities}

    req_code_by_id = {r.requirement_id: r.code for r in master.handling_requirements}
    shp_reqs_by_shp = defaultdict(list)
    for sr in tx.shipment_requirements:
        shp_reqs_by_shp[sr.shipment_id].append(req_code_by_id[sr.requirement_id])

    appt_to_shp = {assoc.appointment_id: assoc.shipment_id for assoc in tx.appointment_shipments}

    for appt in appts:
        shp_id = appt_to_shp.get(appt.appointment_id)
        codes = shp_reqs_by_shp.get(shp_id, [])
        engine_sched.allocate_appointment(
            appointment=appt,
            shipments=[],
            facility=fac_map[appt.facility_id],
            docks=docks_by_fac[appt.facility_id],
            yard_slots=yards_by_fac[appt.facility_id],
            shifts=shifts_by_fac[appt.facility_id],
            handling_codes=codes,
        )

    events = simulate_operational_events(appts, seed=seed)

    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as session:
        populate_db(session, master, tx, appts, events)
        runner = ValidatorRunner(session=session, is_anomaly_aware=False)
        report = runner.run_all(run_id="VAL-TEST-BASELINE")

        assert report.final_validation_status == "PASSED"
        assert report.unexpected_violations_detected == 0
        assert report.expected_violations_detected == 0

    Base.metadata.drop_all(bind=engine)


def test_anomaly_aware_validation_detects_scenarios():
    config = PROFILES[ProfileType.STARTER]
    seed = 20261022
    start_dt = datetime(2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc)

    master = generate_master_data(config, seed, start_dt)
    tx = generate_transactions(master, config, seed, start_dt)

    appts = tx.appointments[:40]
    engine_sched = SchedulingEngine()
    fac_map = {f.facility_id: f for f in master.facilities}
    docks_by_fac = {f.facility_id: [d for d in master.docks if d.facility_id == f.facility_id] for f in master.facilities}
    yards_by_fac = {f.facility_id: [y for y in master.yard_slots if y.facility_id == f.facility_id] for f in master.facilities}
    shifts_by_fac = {f.facility_id: [s for s in master.labor_shifts if s.facility_id == f.facility_id] for f in master.facilities}

    req_code_by_id = {r.requirement_id: r.code for r in master.handling_requirements}
    shp_reqs_by_shp = defaultdict(list)
    for sr in tx.shipment_requirements:
        shp_reqs_by_shp[sr.shipment_id].append(req_code_by_id[sr.requirement_id])

    appt_to_shp = {assoc.appointment_id: assoc.shipment_id for assoc in tx.appointment_shipments}

    for appt in appts:
        shp_id = appt_to_shp.get(appt.appointment_id)
        codes = shp_reqs_by_shp.get(shp_id, [])
        engine_sched.allocate_appointment(
            appointment=appt,
            shipments=[],
            facility=fac_map[appt.facility_id],
            docks=docks_by_fac[appt.facility_id],
            yard_slots=yards_by_fac[appt.facility_id],
            shifts=shifts_by_fac[appt.facility_id],
            handling_codes=codes,
        )

    events = simulate_operational_events(appts, seed=seed)

    # Inject anomalies
    inj_result = inject_anomaly_scenarios(
        appointments=appts,
        events=events,
        shipments=tx.shipments[:40],
        docks=master.docks,
        shifts=master.labor_shifts,
    )

    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as session:
        populate_db(
            session=session,
            master=master,
            tx=tx,
            appointments=inj_result.mutated_appointments,
            events=inj_result.mutated_events,
            exceptions=inj_result.exceptions,
        )

        runner = ValidatorRunner(session=session, is_anomaly_aware=True)
        report = runner.run_all(run_id="VAL-TEST-ANOMALY")

        assert report.final_validation_status == "PASSED"
        assert report.expected_violations_detected >= 3
        assert report.unexpected_violations_detected == 0

    Base.metadata.drop_all(bind=engine)
