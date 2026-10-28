"""Canonical Relational Exporters for CSV, JSON, and SQL DDL / Seed."""

import csv
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from logistics.config import settings
from logistics.models.appointment import AllocationDecision, Appointment, AppointmentShipment
from logistics.models.base import Base
from logistics.models.carrier import Carrier, Vehicle
from logistics.models.event import CheckInEvent
from logistics.models.facility import Dock, DockHandlingCapability, Facility, YardSlot
from logistics.models.labor import LaborShift
from logistics.models.shipment import HandlingRequirement, Shipment, ShipmentHandlingRequirement

EXPORT_TABLES = [
    ("facilities", Facility, "facility_id"),
    ("docks", Dock, "dock_id"),
    ("yard_slots", YardSlot, "yard_slot_id"),
    ("dock_handling_capabilities", DockHandlingCapability, "dock_id"),
    ("carriers", Carrier, "carrier_id"),
    ("vehicles", Vehicle, "vehicle_id"),
    ("handling_requirements", HandlingRequirement, "requirement_id"),
    ("shipments", Shipment, "shipment_id"),
    ("shipment_handling_requirements", ShipmentHandlingRequirement, "shipment_id"),
    ("labor_shifts", LaborShift, "shift_id"),
    ("appointments", Appointment, "appointment_id"),
    ("appointment_shipments", AppointmentShipment, "appointment_id"),
    ("allocation_decisions", AllocationDecision, "decision_id"),
    ("check_in_events", CheckInEvent, "event_id"),
]


def _serialize_val(val: Any) -> Any:
    """Canonicalize values for serialization (dates, booleans, nulls)."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


VOLATILE_FIELDS = {"created_at", "updated_at", "recorded_time"}


def export_canonical_csv_and_json(
    session: Session,
    csv_dir: Path | None = None,
    json_dir: Path | None = None,
) -> dict[str, int]:
    """Export all relational tables to canonical CSV and JSON files, returning row counts."""
    c_dir = csv_dir or (settings.exports_dir / "csv")
    j_dir = json_dir or (settings.exports_dir / "json")
    c_dir.mkdir(parents=True, exist_ok=True)
    j_dir.mkdir(parents=True, exist_ok=True)

    table_row_counts: dict[str, int] = {}

    for table_name, model_cls, pk_field in EXPORT_TABLES:
        rows = list(session.scalars(select(model_cls)).all())
        records = []
        for r in rows:
            # Extract column attributes excluding volatile runtime timestamps
            rec = {}
            for col in model_cls.__table__.columns:
                if col.name not in VOLATILE_FIELDS:
                    rec[col.name] = _serialize_val(getattr(r, col.name))
            records.append(rec)

        # Stable sort by primary key
        records.sort(key=lambda x: str(x.get(pk_field, "")))
        table_row_counts[table_name] = len(records)

        # 1. Export CSV
        csv_file = c_dir / f"{table_name}.csv"
        if records:
            fieldnames = sorted(records[0].keys())
            with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for rec in records:
                    writer.writerow({k: ("" if v is None else v) for k, v in rec.items()})
        else:
            with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
                f.write("")

        # 2. Export JSON
        json_file = j_dir / f"{table_name}.json"
        with open(json_file, mode="w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, sort_keys=True)

    return table_row_counts


def export_sql_ddl_and_seed(
    session: Session,
    sql_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Export complete SQL DDL schema and seed INSERT statements."""
    target_dir = sql_dir or (settings.exports_dir / "sql")
    target_dir.mkdir(parents=True, exist_ok=True)

    ddl_file = target_dir / "schema.sql"
    seed_file = target_dir / "seed.sql"

    # 1. DDL Schema
    ddl_lines = ["-- YottaFlex AI Synthetic Logistics Database Schema DDL\n"]
    for table in Base.metadata.sorted_tables:
        ddl_lines.append(str(CreateTable(table).compile(session.bind)))
        ddl_lines.append(";\n")

    with open(ddl_file, mode="w", encoding="utf-8") as f:
        f.writelines(ddl_lines)

    # 2. SQL Seed Inserts
    seed_lines = ["-- YottaFlex AI Seed Inserts\n", "BEGIN TRANSACTION;\n"]
    for table_name, model_cls, pk_field in EXPORT_TABLES:
        rows = sorted(
            list(session.scalars(select(model_cls)).all()),
            key=lambda r: str(getattr(r, pk_field, "")),
        )
        cols = [c.name for c in model_cls.__table__.columns if c.name not in VOLATILE_FIELDS]
        for r in rows:
            val_strs = []
            for col in cols:
                v = getattr(r, col)
                if v is None:
                    val_strs.append("NULL")
                elif isinstance(v, (int, float)):
                    val_strs.append(str(v))
                elif isinstance(v, bool):
                    val_strs.append("1" if v else "0")
                else:
                    escaped = str(v).replace("'", "''")
                    val_strs.append(f"'{escaped}'")
            seed_lines.append(f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({', '.join(val_strs)});\n")

    seed_lines.append("COMMIT;\n")
    with open(seed_file, mode="w", encoding="utf-8") as f:
        f.writelines(seed_lines)

    return ddl_file, seed_file
