"""Command Line Interface (Typer) for YottaFlex Logistics Platform."""

from pathlib import Path
import time
import typer
import uvicorn

from logistics.config import ProfileType, settings
from logistics.models.database import create_db_engine, init_db
from logistics.services.workflow import WorkflowService

app = typer.Typer(
    name="logistics",
    help="YottaFlex AI Logistics Appointment Scheduling Platform CLI",
    add_completion=False,
)


@app.command()
def init() -> None:
    """Initialize database tables and directory scaffolding."""
    typer.echo("[+] Initializing database tables and storage directories...")
    init_db()
    typer.echo(f"[OK] Database successfully initialized at: {settings.database_url}")


@app.command()
def generate_starter(
    seed: int = typer.Option(settings.seed, "--seed", "-s", help="Deterministic PRNG seed"),
    anomalies: bool = typer.Option(True, "--anomalies/--no-anomalies", help="Inject 7 anomaly scenarios"),
) -> None:
    """Generate the starter profile (2 facilities, 20 docks, 1,000 appointments)."""
    typer.echo(f"[+] Starting generation for profile: STARTER (seed={seed})...")
    start = time.perf_counter()
    summary = WorkflowService.generate_pipeline(
        profile=ProfileType.STARTER,
        seed=seed,
        inject_anomalies=anomalies,
    )
    elapsed = round(time.perf_counter() - start, 2)
    typer.echo(f"[OK] Starter generation completed in {elapsed}s:")
    typer.echo(f"    - Facilities: {summary['facilities']}")
    typer.echo(f"    - Docks: {summary['docks']}")
    typer.echo(f"    - Appointments: {summary['appointments']:,}")
    typer.echo(f"    - Operational Events: {summary['events']:,}")
    typer.echo(f"    - Allocation Success Rate: {summary['allocation_success_rate'] * 100:.1f}%")
    typer.echo(f"    - Validation Status: {summary['validation_status']}")
    typer.echo(f"    - Source Manifest: {summary['manifest_path']}")


@app.command()
def generate_full(
    seed: int = typer.Option(settings.seed, "--seed", "-s", help="Deterministic PRNG seed"),
    anomalies: bool = typer.Option(True, "--anomalies/--no-anomalies", help="Inject 7 anomaly scenarios"),
) -> None:
    """Generate the full profile (10 facilities, 100 docks, 20,000 appointments, 60 days)."""
    typer.echo(f"[+] Starting high-throughput generation for profile: FULL (seed={seed})...")
    start = time.perf_counter()
    summary = WorkflowService.generate_pipeline(
        profile=ProfileType.FULL,
        seed=seed,
        inject_anomalies=anomalies,
    )
    elapsed = round(time.perf_counter() - start, 2)
    typer.echo(f"[OK] Full profile generation completed in {elapsed}s:")
    typer.echo(f"    - Facilities: {summary['facilities']}")
    typer.echo(f"    - Docks: {summary['docks']}")
    typer.echo(f"    - Appointments: {summary['appointments']:,}")
    typer.echo(f"    - Operational Events: {summary['events']:,}")
    typer.echo(f"    - Allocation Success Rate: {summary['allocation_success_rate'] * 100:.1f}%")
    typer.echo(f"    - Validation Status: {summary['validation_status']}")
    typer.echo(f"    - Source Manifest: {summary['manifest_path']}")


@app.command()
def validate(
    anomaly_aware: bool = typer.Option(True, "--anomaly-aware/--baseline-only", help="Run in anomaly-aware context"),
) -> None:
    """Run the 19 automated rule validators on the active database."""
    from sqlalchemy.orm import Session
    from logistics.validators.runner import ValidatorRunner

    typer.echo(f"[+] Executing automated validation (anomaly_aware={anomaly_aware})...")
    engine = create_db_engine()
    with Session(bind=engine) as session:
        runner = ValidatorRunner(session=session, is_anomaly_aware=anomaly_aware)
        report = runner.run_all(run_id="VAL-CLI-RUN")
        typer.echo(f"[OK] Validation Result: {report.final_validation_status}")
        typer.echo(f"    - Checks Executed: {report.checks_executed}")
        typer.echo(f"    - Passed Checks: {report.checks_passed}")
        typer.echo(f"    - Expected Anomalies Detected: {report.expected_violations_detected}")
        typer.echo(f"    - Unexpected Violations: {report.unexpected_violations_detected}")


@app.command()
def evaluate() -> None:
    """Calculate and export live operational KPI metrics."""
    from sqlalchemy.orm import Session
    from logistics.analytics.metrics import calculate_evaluation_metrics, export_evaluation_report

    typer.echo("[+] Computing operational evaluation metrics...")
    engine = create_db_engine()
    with Session(bind=engine) as session:
        metrics = calculate_evaluation_metrics(session)
        out_path = export_evaluation_report(metrics)
        typer.echo(f"[OK] Evaluation metrics saved to: {out_path}")
        typer.echo(f"    - Allocation Rate: {metrics['operational_throughput']['allocation_success_rate'] * 100:.1f}%")
        typer.echo(f"    - Dock Utilization: {metrics['resource_utilization']['dock_utilization_rate'] * 100:.1f}%")
        typer.echo(f"    - Avg Vehicle Wait: {metrics['service_level_metrics']['average_vehicle_wait_minutes']}m")


@app.command()
def reproduce(
    profile: ProfileType = typer.Option(ProfileType.STARTER, "--profile", "-p", help="Target dataset profile"),
) -> None:
    """Execute double-run verification and generate docs/reproducibility_report.md."""
    typer.echo(f"[+] Executing double-run bitwise reproducibility test on {profile.value} profile...")
    report_path = WorkflowService.run_reproducibility(profile=profile)
    typer.echo(f"[OK] Reproducibility verification completed. Report generated at: {report_path}")


@app.command()
def serve(
    host: str = typer.Option(settings.api_host, "--host", "-h", help="API server host"),
    port: int = typer.Option(settings.api_port, "--port", "-p", help="API server port"),
) -> None:
    """Launch the FastAPI REST API server."""
    typer.echo(f"[+] Starting FastAPI application on http://{host}:{port} ...")
    uvicorn.run("logistics.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
