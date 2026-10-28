"""Unit Tests for Deterministic Service Duration Formula (BR-DUR-001)."""

import pytest

from logistics.scheduler.service_duration import calculate_service_duration


def test_standard_dry_inbound_duration():
    # 20 pallets, INBOUND, no special handling
    # Base: 15
    # Pallets: 20 * 1.5 = 30
    # Inbound: 10
    # Raw = 15 + 30 + 10 = 55
    # Ceil to 15 min: 60 minutes
    duration = calculate_service_duration(20, "INBOUND")
    assert duration == 60


def test_standard_dry_outbound_duration():
    # 20 pallets, OUTBOUND, no special handling
    # Base: 15
    # Pallets: 20 * 1.5 = 30
    # Outbound: 5
    # Raw = 15 + 30 + 5 = 50
    # Ceil to 15 min: 60 minutes
    duration = calculate_service_duration(20, "OUTBOUND")
    assert duration == 60


def test_handling_penalties_reefer_hazmat():
    # 10 pallets, INBOUND, REEFER + HAZMAT
    # Base: 15
    # Pallets: 10 * 1.5 = 15
    # Inbound: 10
    # Reefer penalty: 15
    # Hazmat penalty: 25
    # Raw = 15 + 15 + 10 + 15 + 25 = 80
    # Ceil to 15 min: 90 minutes
    duration = calculate_service_duration(10, "INBOUND", handling_codes=["REEFER", "HAZMAT"])
    assert duration == 90


def test_min_and_max_bounds():
    # 1 pallet, OUTBOUND -> Raw = 15 + 1.5 + 5 = 21.5 -> Ceil: 30
    min_dur = calculate_service_duration(1, "OUTBOUND")
    assert min_dur == 30

    # 150 pallets with hazmat & reefer -> should clamp to 240
    max_dur = calculate_service_duration(150, "INBOUND", handling_codes=["HAZMAT", "REEFER", "OVERSIZED"])
    assert max_dur == 240


def test_invalid_parameters():
    with pytest.raises(ValueError, match="Pallet count must be at least 1"):
        calculate_service_duration(0, "INBOUND")

    with pytest.raises(ValueError, match="Invalid shipment type"):
        calculate_service_duration(10, "UNKNOWN")
