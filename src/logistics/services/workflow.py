"""Domain Service Orchestrator: Shared Business Logic for CLI and API."""

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from logistics.analytics.ground_truth import export_ground_truth
from logistics.analytics.metrics import calculate_evaluation_metrics, export_evaluation_report
from logistics.analytics.reproducibility import generate_reproducibility_report
from logistics.config import PROFILES, ProfileConfig, ProfileType, settings
from logistics.exporters.manifest import generate_source_manifest
from logistics.exporters.relational import export_canonical_csv_and_json, export_sql_ddl_and_seed
from logistics.generators.identifiers import generate_appointment_id, generate_shipment_id
from logistics.generators.master_data import generate_master_data
from logistics.generators.transactions import generate_transactions
from logistics.models.appointment import AllocationDecision, Appointment, AppointmentShipment
from logistics.models.base import Base
from logistics.models.carrier import Carrier, Vehicle
from logistics.models.database import create_db_engine, init_db
from logistics.models.event import CheckInEvent
from logistics.models.exception import OperationalException
from logistics.models.facility import Dock, DockHandlingCapability, Facility, YardSlot
from logistics.models.labor import LaborShift
from logistics.models.shipment import HandlingRequirement, Shipment, ShipmentHandlingRequirement
from logistics.scheduler.engine import SchedulingEngine
from logistics.scheduler.service_duration import calculate_service_duration
from logistics.simulation.anomalies import inject_anomaly_scenarios
from logistics.simulation.engine import simulate_operational_events
from logistics.validators.runner import ValidatorRunner


class WorkflowService:
    """Unified application service coordinating simulation, scheduling, validation, and exports."""

    @classmethod
    def generate_pipeline(
        cls,
        profile: ProfileType,
        seed: int | None = None,
        inject_anomalies: bool = True,
        db_session: Session | None = None,
    ) -> dict[str, Any]:
        """Execute the complete deterministic logistics pipeline and export all artifacts."""
        active_seed = seed if seed is not None else settings.seed
        cfg: ProfileConfig = PROFILES[profile]
        sim_start = settings.simulation_start
        settings.ensure_directories()

        # 1. Master Data Generation
        master = generate_master_data(cfg, active_seed, sim_start)

        # 2. Transaction Generation
        tx = generate_transactions(master, cfg, active_seed, sim_start)

        # 3. Deterministic Appointment Allocation Engine
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

        decisions: list[AllocationDecision] = []
        for idx, appt in enumerate(tx.appointments, start=1):
            shp_id = appt_to_shp.get(appt.appointment_id)
            codes = shp_reqs_by_shp.get(shp_id, [])
            decision = engine_sched.allocate_appointment(
                appointment=appt,
                shipments=[],
                facility=fac_map[appt.facility_id],
                docks=docks_by_fac[appt.facility_id],
                yard_slots=yards_by_fac[appt.facility_id],
                shifts=shifts_by_fac[appt.facility_id],
                handling_codes=codes,
                decision_seq=1,
            )
            decisions.append(decision)

        # 4. Operational Discrete Event Simulation
        events = simulate_operational_events(tx.appointments, seed=active_seed)

        # 5. Anomaly Injection Layer (if requested)
        exceptions: list[OperationalException] = []
        if inject_anomalies:
            inj_res = inject_anomaly_scenarios(
                appointments=tx.appointments,
                events=events,
                shipments=tx.shipments,
                docks=master.docks,
                shifts=master.labor_shifts,
                sim_year=sim_start.year,
            )
            exceptions = inj_res.exceptions
            events = inj_res.mutated_events
            export_ground_truth(exceptions)

        # 6. Database Persistence
        engine = create_db_engine()
        Base.metadata.create_all(bind=engine)

        session = db_session or Session(bind=engine)
        try:
            # Wipe and reload
            session.query(CheckInEvent).delete()
            session.query(AllocationDecision).delete()
            session.query(AppointmentShipment).delete()
            session.query(Appointment).delete()
            session.query(ShipmentHandlingRequirement).delete()
            session.query(Shipment).delete()
            session.query(DockHandlingCapability).delete()
            session.query(LaborShift).delete()
            session.query(Vehicle).delete()
            session.query(YardSlot).delete()
            session.query(Dock).delete()
            session.query(Carrier).delete()
            session.query(Facility).delete()
            session.query(HandlingRequirement).delete()
            session.query(OperationalException).delete()
            session.commit()

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

            session.add_all(tx.shipments)
            session.add_all(tx.shipment_requirements)
            session.add_all(tx.appointments)
            session.add_all(tx.appointment_shipments)
            session.add_all(decisions)
            session.flush()

            session.add_all(events)
            if exceptions:
                session.add_all(exceptions)
            session.commit()

            # 7. Exports
            row_counts = export_canonical_csv_and_json(session)
            export_sql_ddl_and_seed(session)

            # 8. Validation
            val_runner = ValidatorRunner(session, is_anomaly_aware=inject_anomalies)
            val_report = val_runner.run_all(run_id=f"VAL-RUN-{profile.value}")
            val_report_path = settings.exports_dir / "reports" / "validation_report.json"
            val_report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(val_report_path, "w", encoding="utf-8") as f:
                json.dump(val_report.to_dict(), f, indent=2, sort_keys=True)

            # 9. Evaluation Metrics
            eval_metrics = calculate_evaluation_metrics(session, validation_report_path=val_report_path, profile=profile)
            export_evaluation_report(eval_metrics)

            # 10. Source Manifest
            manifest_path, manifest = generate_source_manifest(row_counts)

            summary = {
                "profile": profile.value,
                "seed": active_seed,
                "facilities": len(master.facilities),
                "docks": len(master.docks),
                "yard_slots": len(master.yard_slots),
                "carriers": len(master.carriers),
                "vehicles": len(master.vehicles),
                "shipments": len(tx.shipments),
                "appointments": len(tx.appointments),
                "events": len(events),
                "exceptions": len(exceptions),
                "validation_status": val_report.final_validation_status,
                "allocation_success_rate": eval_metrics["operational_throughput"]["allocation_success_rate"],
                "manifest_path": str(manifest_path),
            }
            return summary
        finally:
            if not db_session:
                session.close()

    @classmethod
    def run_reproducibility(cls, profile: ProfileType = ProfileType.STARTER) -> Path:
        """Execute double-run comparison and write reproducibility report."""
        seed = settings.seed
        # Run 1
        summary_1 = cls.generate_pipeline(profile=profile, seed=seed, inject_anomalies=True)
        manifest_1_path = Path(summary_1["manifest_path"])
        with open(manifest_1_path, encoding="utf-8") as f:
            manifest_1 = json.load(f)
        with open(settings.exports_dir / "reports" / "evaluation_metrics.json", encoding="utf-8") as f:
            metrics_1 = json.load(f)

        # Run 2
        summary_2 = cls.generate_pipeline(profile=profile, seed=seed, inject_anomalies=True)
        manifest_2_path = Path(summary_2["manifest_path"])
        with open(manifest_2_path, encoding="utf-8") as f:
            manifest_2 = json.load(f)
        with open(settings.exports_dir / "reports" / "evaluation_metrics.json", encoding="utf-8") as f:
            metrics_2 = json.load(f)

        report_path = generate_reproducibility_report(
            run_1_manifest=manifest_1,
            run_2_manifest=manifest_2,
            run_1_metrics=metrics_1,
            run_2_metrics=metrics_2,
        )
        return report_path
