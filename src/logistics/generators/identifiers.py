"""Centralized Deterministic Identifier Generator and Format Validators."""

import re

# Regex patterns for business ID format validation
FACILITY_PATTERN = re.compile(r"^FAC-\d{3}$")
DOCK_PATTERN = re.compile(r"^DOCK-FAC-\d{3}-\d{3}$")
YARD_SLOT_PATTERN = re.compile(r"^YARD-FAC-\d{3}-\d{3}$")
CARRIER_PATTERN = re.compile(r"^CARR-\d{3}$")
VEHICLE_PATTERN = re.compile(r"^VEH-\d{4}$")
HANDLING_REQ_PATTERN = re.compile(r"^REQ-\d{3}$")
SHIPMENT_PATTERN = re.compile(r"^SHP-\d{4}-\d{6}$")
APPOINTMENT_PATTERN = re.compile(r"^APPT-\d{4}-\d{6}$")
LABOR_SHIFT_PATTERN = re.compile(r"^SHIFT-FAC-\d{3}-\d{8}-\d{2}$")
ALLOCATION_DECISION_PATTERN = re.compile(r"^DEC-APPT-\d{4}-\d{6}-\d{2}$")
CHECK_IN_EVENT_PATTERN = re.compile(r"^CHECK-APPT-\d{4}-\d{6}-\d{2}$")
EXCEPTION_PATTERN = re.compile(r"^EXC-\d{4}-\d{6}$")


class IdentifierOverflowError(ValueError):
    """Raised when an identifier sequence exceeds its configured zero-padded field width."""
    pass


def generate_facility_id(seq: int) -> str:
    """Generate fixed-width facility identifier, e.g. 'FAC-001'."""
    if not 1 <= seq <= 999:
        raise IdentifierOverflowError(f"Facility sequence {seq} out of bounds [1, 999]")
    return f"FAC-{seq:03d}"


def generate_dock_id(facility_id: str, seq: int) -> str:
    """Generate facility-scoped dock door identifier, e.g. 'DOCK-FAC-001-001'."""
    if not FACILITY_PATTERN.match(facility_id):
        raise ValueError(f"Invalid parent facility ID format: {facility_id}")
    if not 1 <= seq <= 999:
        raise IdentifierOverflowError(f"Dock sequence {seq} out of bounds [1, 999]")
    return f"DOCK-{facility_id}-{seq:03d}"


def generate_yard_slot_id(facility_id: str, seq: int) -> str:
    """Generate facility-scoped yard slot identifier, e.g. 'YARD-FAC-001-001'."""
    if not FACILITY_PATTERN.match(facility_id):
        raise ValueError(f"Invalid parent facility ID format: {facility_id}")
    if not 1 <= seq <= 999:
        raise IdentifierOverflowError(f"Yard slot sequence {seq} out of bounds [1, 999]")
    return f"YARD-{facility_id}-{seq:03d}"


def generate_carrier_id(seq: int) -> str:
    """Generate fixed-width carrier identifier, e.g. 'CARR-001'."""
    if not 1 <= seq <= 999:
        raise IdentifierOverflowError(f"Carrier sequence {seq} out of bounds [1, 999]")
    return f"CARR-{seq:03d}"


def generate_vehicle_id(seq: int) -> str:
    """Generate fixed-width vehicle identifier, e.g. 'VEH-0001'."""
    if not 1 <= seq <= 9999:
        raise IdentifierOverflowError(f"Vehicle sequence {seq} out of bounds [1, 9999]")
    return f"VEH-{seq:04d}"


def generate_handling_requirement_id(seq: int) -> str:
    """Generate handling requirement identifier, e.g. 'REQ-001'."""
    if not 1 <= seq <= 999:
        raise IdentifierOverflowError(f"Handling requirement sequence {seq} out of bounds [1, 999]")
    return f"REQ-{seq:03d}"


def generate_shipment_id(year: int, seq: int) -> str:
    """Generate simulation-year-scoped shipment identifier, e.g. 'SHP-2026-000001'."""
    if not 2000 <= year <= 2099:
        raise ValueError(f"Invalid simulation year: {year}")
    if not 1 <= seq <= 999999:
        raise IdentifierOverflowError(f"Shipment sequence {seq} out of bounds [1, 999999]")
    return f"SHP-{year}-{seq:06d}"


def generate_appointment_id(year: int, seq: int) -> str:
    """Generate simulation-year-scoped appointment identifier, e.g. 'APPT-2026-000001'."""
    if not 2000 <= year <= 2099:
        raise ValueError(f"Invalid simulation year: {year}")
    if not 1 <= seq <= 999999:
        raise IdentifierOverflowError(f"Appointment sequence {seq} out of bounds [1, 999999]")
    return f"APPT-{year}-{seq:06d}"


def generate_labor_shift_id(facility_id: str, date_compact: str, seq: int) -> str:
    """Generate labor shift identifier, e.g. 'SHIFT-FAC-001-20261022-01'."""
    if not FACILITY_PATTERN.match(facility_id):
        raise ValueError(f"Invalid parent facility ID format: {facility_id}")
    if not re.match(r"^\d{8}$", date_compact):
        raise ValueError(f"Date compact must be 8 digits YYYYMMDD, got: {date_compact}")
    if not 1 <= seq <= 99:
        raise IdentifierOverflowError(f"Labor shift sequence {seq} out of bounds [1, 99]")
    return f"SHIFT-{facility_id}-{date_compact}-{seq:02d}"


def generate_allocation_decision_id(appointment_id: str, seq: int) -> str:
    """Generate appointment-scoped decision identifier, e.g. 'DEC-APPT-2026-000001-01'."""
    if not APPOINTMENT_PATTERN.match(appointment_id):
        raise ValueError(f"Invalid appointment ID format: {appointment_id}")
    if not 1 <= seq <= 99:
        raise IdentifierOverflowError(f"Decision sequence {seq} out of bounds [1, 99]")
    return f"DEC-{appointment_id}-{seq:02d}"


def generate_check_in_event_id(appointment_id: str, seq: int) -> str:
    """Generate appointment-scoped check-in event identifier, e.g. 'CHECK-APPT-2026-000001-01'."""
    if not APPOINTMENT_PATTERN.match(appointment_id):
        raise ValueError(f"Invalid appointment ID format: {appointment_id}")
    if not 1 <= seq <= 99:
        raise IdentifierOverflowError(f"Check-in event sequence {seq} out of bounds [1, 99]")
    return f"CHECK-{appointment_id}-{seq:02d}"


def generate_exception_id(year: int, seq: int) -> str:
    """Generate simulation-year-scoped operational exception identifier, e.g. 'EXC-2026-000001'."""
    if not 2000 <= year <= 2099:
        raise ValueError(f"Invalid simulation year: {year}")
    if not 1 <= seq <= 999999:
        raise IdentifierOverflowError(f"Exception sequence {seq} out of bounds [1, 999999]")
    return f"EXC-{year}-{seq:06d}"
