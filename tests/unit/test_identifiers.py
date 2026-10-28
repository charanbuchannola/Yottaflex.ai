"""Unit Tests for Deterministic Identifier Generation."""

import pytest

from logistics.generators.identifiers import (
    FACILITY_PATTERN,
    DOCK_PATTERN,
    YARD_SLOT_PATTERN,
    CARRIER_PATTERN,
    VEHICLE_PATTERN,
    HANDLING_REQ_PATTERN,
    SHIPMENT_PATTERN,
    APPOINTMENT_PATTERN,
    LABOR_SHIFT_PATTERN,
    ALLOCATION_DECISION_PATTERN,
    CHECK_IN_EVENT_PATTERN,
    EXCEPTION_PATTERN,
    IdentifierOverflowError,
    generate_facility_id,
    generate_dock_id,
    generate_yard_slot_id,
    generate_carrier_id,
    generate_vehicle_id,
    generate_handling_requirement_id,
    generate_shipment_id,
    generate_appointment_id,
    generate_labor_shift_id,
    generate_allocation_decision_id,
    generate_check_in_event_id,
    generate_exception_id,
)


def test_facility_id_format_and_boundaries():
    assert generate_facility_id(1) == "FAC-001"
    assert generate_facility_id(42) == "FAC-042"
    assert generate_facility_id(999) == "FAC-999"
    assert FACILITY_PATTERN.match("FAC-001") is not None

    with pytest.raises(IdentifierOverflowError):
        generate_facility_id(1000)

    with pytest.raises(IdentifierOverflowError):
        generate_facility_id(0)


def test_dock_id_embeds_parent_facility():
    fid = generate_facility_id(1)
    did = generate_dock_id(fid, 1)
    assert did == "DOCK-FAC-001-001"
    assert DOCK_PATTERN.match(did) is not None
    assert "FAC-001" in did

    with pytest.raises(ValueError, match="Invalid parent facility ID format"):
        generate_dock_id("INVALID", 1)

    with pytest.raises(IdentifierOverflowError):
        generate_dock_id(fid, 1000)


def test_yard_slot_id_embeds_parent_facility():
    fid = generate_facility_id(2)
    yid = generate_yard_slot_id(fid, 5)
    assert yid == "YARD-FAC-002-005"
    assert YARD_SLOT_PATTERN.match(yid) is not None

    with pytest.raises(IdentifierOverflowError):
        generate_yard_slot_id(fid, 1000)


def test_carrier_and_vehicle_id():
    cid = generate_carrier_id(3)
    assert cid == "CARR-003"
    assert CARRIER_PATTERN.match(cid) is not None

    vid = generate_vehicle_id(42)
    assert vid == "VEH-0042"
    assert VEHICLE_PATTERN.match(vid) is not None

    with pytest.raises(IdentifierOverflowError):
        generate_vehicle_id(10000)


def test_handling_requirement_id():
    req_id = generate_handling_requirement_id(1)
    assert req_id == "REQ-001"
    assert HANDLING_REQ_PATTERN.match(req_id) is not None


def test_shipment_and_appointment_id():
    shp_id = generate_shipment_id(2026, 1)
    assert shp_id == "SHP-2026-000001"
    assert SHIPMENT_PATTERN.match(shp_id) is not None

    appt_id = generate_appointment_id(2026, 1)
    assert appt_id == "APPT-2026-000001"
    assert APPOINTMENT_PATTERN.match(appt_id) is not None

    with pytest.raises(IdentifierOverflowError):
        generate_appointment_id(2026, 1000000)


def test_labor_shift_id():
    fid = "FAC-001"
    shift_id = generate_labor_shift_id(fid, "20261022", 1)
    assert shift_id == "SHIFT-FAC-001-20261022-01"
    assert LABOR_SHIFT_PATTERN.match(shift_id) is not None

    with pytest.raises(IdentifierOverflowError):
        generate_labor_shift_id(fid, "20261022", 100)


def test_decision_and_event_id():
    appt_id = "APPT-2026-000001"
    dec_id = generate_allocation_decision_id(appt_id, 1)
    assert dec_id == "DEC-APPT-2026-000001-01"
    assert ALLOCATION_DECISION_PATTERN.match(dec_id) is not None

    evt_id = generate_check_in_event_id(appt_id, 1)
    assert evt_id == "CHECK-APPT-2026-000001-01"
    assert CHECK_IN_EVENT_PATTERN.match(evt_id) is not None


def test_exception_id():
    exc_id = generate_exception_id(2026, 1)
    assert exc_id == "EXC-2026-000001"
    assert EXCEPTION_PATTERN.match(exc_id) is not None
