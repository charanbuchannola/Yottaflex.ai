"""End-to-End Pipeline & Integration Coverage Tests."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from typer.testing import CliRunner

from logistics.analytics.ground_truth import export_ground_truth
from logistics.analytics.metrics import calculate_evaluation_metrics, export_evaluation_report
from logistics.analytics.reproducibility import generate_reproducibility_report
from logistics.config import ProfileType, settings
from logistics.exporters.manifest import generate_source_manifest
from logistics.exporters.relational import export_canonical_csv_and_json, export_sql_ddl_and_seed
from logistics.main import app as cli_app
from logistics.models.base import Base
from logistics.models.carrier import Carrier, Vehicle
from logistics.models.exception import OperationalException
from logistics.models.facility import Dock, Facility, YardSlot
from logistics.models.labor import LaborShift
from logistics.models.shipment import HandlingRequirement
from logistics.services.workflow import WorkflowService
from logistics.simulation.anomalies import inject_anomaly_scenarios


def test_workflow_generate_pipeline_and_exporters(tmp_path):
    """Test full workflow pipeline execution, exporters, and ground truth generation."""
    # Test ground truth export directly
    exc = OperationalException(
        exception_id="EXC-2026-000001",
        appointment_id="APPT-2026-000001",
        scenario_id="SCEN-01",
        issue_type="OVERLAPPING_APPOINTMENTS",
        root_cause="Test overlap",
        expected_outcome="REJECT",
        ground_truth_label="ANOMALY_OVERLAP",
        is_injected_anomaly=True,
    )
    csv_gt, json_gt = export_ground_truth([exc], output_dir=tmp_path / "ground_truth")
    assert csv_gt.exists()
    assert json_gt.exists()

    # Test relational export and metrics
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as session:
        fac = Facility(facility_id="FAC-001", name="Test Hub", operating_start_hour=6, operating_end_hour=22)
        dock = Dock(dock_id="DOCK-FAC-001-001", facility_id="FAC-001", dock_number="D-01", has_hazmat_permit=True)
        carr = Carrier(carrier_id="CARR-001", name="Acme Carrier", scac_code="ACME")
        veh = Vehicle(vehicle_id="VEH-0001", carrier_id="CARR-001", vehicle_type="DRY_VAN", license_plate="IL-999")
        shift = LaborShift(
            shift_id="SHIFT-FAC-001-20261022-01",
            facility_id="FAC-001",
            shift_date=datetime(2026, 10, 22).date(),
            start_time=datetime(2026, 10, 22, 6, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 10, 22, 14, 0, tzinfo=timezone.utc),
            total_workers=8,
            forklift_certified_workers=4,
            hazmat_certified_workers=2,
        )
        session.add_all([fac, dock, carr, veh, shift, exc])
        session.commit()

        # Export relational CSV & JSON
        row_counts = export_canonical_csv_and_json(
            session,
            csv_dir=tmp_path / "csv",
            json_dir=tmp_path / "json",
        )
        assert row_counts["facilities"] == 1
        assert (tmp_path / "csv" / "facilities.csv").exists()
        assert (tmp_path / "json" / "facilities.json").exists()

        # Export SQL DDL and Seed
        ddl_p, seed_p = export_sql_ddl_and_seed(session, sql_dir=tmp_path / "sql")
        assert ddl_p.exists()
        assert seed_p.exists()

        # Compute metrics
        metrics = calculate_evaluation_metrics(session, profile=ProfileType.STARTER)
        assert "operational_throughput" in metrics
        assert metrics["profile"] == "STARTER"

        # Export evaluation report
        eval_path = export_evaluation_report(metrics, output_path=tmp_path / "eval.json")
        assert eval_path.exists()


def test_reproducibility_report_generation(tmp_path):
    """Test reproducibility comparison and markdown report generator."""
    manifest_1 = {
        "dataset_profile": "STARTER",
        "seed": 20261022,
        "files": {
            "exports/csv/facilities.csv": {"sha256": "abc1234567890", "size_bytes": 100},
            "exports/csv/docks.csv": {"sha256": "def1234567890", "size_bytes": 200},
        },
        "entity_counts": {"facilities": 2, "docks": 20},
    }
    manifest_2 = {
        "dataset_profile": "STARTER",
        "seed": 20261022,
        "files": {
            "exports/csv/facilities.csv": {"sha256": "abc1234567890", "size_bytes": 100},
            "exports/csv/docks.csv": {"sha256": "def1234567890", "size_bytes": 200},
        },
        "entity_counts": {"facilities": 2, "docks": 20},
    }
    metrics_1 = {
        "operational_throughput": {"allocation_success_rate": 0.55},
        "resource_utilization": {"dock_utilization_rate": 0.27},
        "service_level_metrics": {"average_vehicle_wait_minutes": 9.5},
        "anomaly_detection_performance": {"f1_score": 1.0},
    }
    metrics_2 = {
        "operational_throughput": {"allocation_success_rate": 0.55},
        "resource_utilization": {"dock_utilization_rate": 0.27},
        "service_level_metrics": {"average_vehicle_wait_minutes": 9.5},
        "anomaly_detection_performance": {"f1_score": 1.0},
    }

    report_path = generate_reproducibility_report(
        manifest_1,
        manifest_2,
        metrics_1,
        metrics_2,
        output_path=tmp_path / "reproducibility_report.md",
    )
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "100% REPRODUCIBLE" in content
    assert "MATCH" in content


def test_cli_validate_and_evaluate_commands():
    """Test CLI validate and evaluate commands execution."""
    runner = CliRunner()
    val_res = runner.invoke(cli_app, ["validate", "--anomaly-aware"])
    assert val_res.exit_code == 0
    assert "PASSED" in val_res.output

    eval_res = runner.invoke(cli_app, ["evaluate"])
    assert eval_res.exit_code == 0
    assert "Evaluation metrics saved" in eval_res.output
