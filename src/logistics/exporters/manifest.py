"""Source Manifest & SHA-256 Checksum Generator."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from logistics.config import settings


def compute_sha256(file_path: Path) -> str:
    """Compute deterministic SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_source_manifest(
    record_counts: dict[str, int],
    output_path: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Scan all exported files, compute SHA-256 hashes, and generate source_manifest.json."""
    manifest_target = output_path or (settings.exports_dir / "source_manifest.json")
    manifest_target.parent.mkdir(parents=True, exist_ok=True)

    tracked_dirs = [
        settings.exports_dir / "csv",
        settings.exports_dir / "json",
        settings.exports_dir / "sql",
        settings.exports_dir / "reports",
        settings.data_dir / "ground_truth",
    ]

    files_manifest: dict[str, dict[str, Any]] = {}
    total_bytes = 0

    for d in tracked_dirs:
        if d.exists():
            for p in sorted(d.glob("*")):
                if p.is_file():
                    sha = compute_sha256(p)
                    size = p.stat().st_size
                    total_bytes += size
                    rel_path = str(p.relative_to(p.parent.parent.parent)).replace("\\", "/")
                    files_manifest[rel_path] = {
                        "sha256": sha,
                        "size_bytes": size,
                    }

    manifest_payload: dict[str, Any] = {
        "manifest_version": "1.0.0",
        "generated_at": f"{settings.sim_year}-10-22T00:00:00Z",
        "dataset_profile": settings.profile.value,
        "seed": settings.seed,
        "schema_version": "2.0.0",
        "generator_version": "0.1.0",
        "configuration": {
            "facilities_count": settings.active_profile_config.facilities_count,
            "docks_per_facility": settings.active_profile_config.docks_per_facility,
            "appointments_count": settings.active_profile_config.appointments_count,
            "simulation_days": settings.active_profile_config.simulation_days,
            "operating_hours": f"{settings.active_profile_config.operating_start_hour:02d}:00-{settings.active_profile_config.operating_end_hour:02d}:00",
        },
        "entity_counts": record_counts,
        "total_files": len(files_manifest),
        "total_bytes": total_bytes,
        "files": files_manifest,
    }

    with open(manifest_target, mode="w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2, sort_keys=True)

    return manifest_target, manifest_payload
