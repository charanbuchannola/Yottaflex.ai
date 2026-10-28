"""Ground-Truth Exporter and Zero-Leakage Verification."""

import csv
import json
from pathlib import Path
from typing import Sequence

from logistics.config import settings
from logistics.models.exception import OperationalException


def export_ground_truth(
    exceptions: Sequence[OperationalException],
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Export ground-truth labels and scenario provenance to isolated storage."""
    target_dir = output_dir or (settings.data_dir / "ground_truth")
    target_dir.mkdir(parents=True, exist_ok=True)

    csv_path = target_dir / "ground_truth.csv"
    json_path = target_dir / "ground_truth.json"

    records = []
    for exc in exceptions:
        records.append({
            "record_id": exc.appointment_id,
            "entity_type": "APPOINTMENT",
            "scenario_id": exc.scenario_id,
            "issue_type": exc.issue_type,
            "expected_decision": exc.expected_outcome,
            "ground_truth_label": exc.ground_truth_label,
            "root_cause": exc.root_cause,
            "is_injected_anomaly": exc.is_injected_anomaly,
        })

    # 1. Deterministic CSV export
    fieldnames = [
        "record_id",
        "entity_type",
        "scenario_id",
        "issue_type",
        "expected_decision",
        "ground_truth_label",
        "root_cause",
        "is_injected_anomaly",
    ]
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in sorted(records, key=lambda x: (x["scenario_id"], x["record_id"])):
            writer.writerow(r)

    # 2. Canonical JSON export (sorted keys, 2-space indent)
    sorted_records = sorted(records, key=lambda x: (x["scenario_id"], x["record_id"]))
    with open(json_path, mode="w", encoding="utf-8") as f:
        json.dump(sorted_records, f, indent=2, sort_keys=True)

    return csv_path, json_path
