"""Deterministic Service Duration Calculation (Rule BR-DUR-001)."""

import math
from typing import Sequence

BASE_SETUP_TEARDOWN_MINUTES = 15
MINUTES_PER_PALLET = 1.5

DIRECTIONAL_ADJUSTMENT = {
    "INBOUND": 10,
    "OUTBOUND": 5,
}

HANDLING_PENALTIES = {
    "REEFER": 15,
    "HAZMAT": 25,
    "FRAGILE": 10,
    "OVERSIZED": 15,
    "LIFTGATE": 10,
}

SLOT_GRANULARITY_MINUTES = 15
MIN_DURATION_MINUTES = 30
MAX_DURATION_MINUTES = 240


def calculate_service_duration(
    pallet_count: int,
    shipment_type: str,
    handling_codes: Sequence[str] = (),
) -> int:
    """Derive deterministic appointment service duration in minutes (BR-DUR-001).

    Formula:
        Raw = Base + (PalletCount * 1.5) + DirectionalAdj + Sum(HandlingPenalties)
        Duration = Clamp(CeilTo15Minutes(Raw), Min=30, Max=240)
    """
    if pallet_count < 1:
        raise ValueError(f"Pallet count must be at least 1, got {pallet_count}")

    direction = shipment_type.upper()
    if direction not in DIRECTIONAL_ADJUSTMENT:
        raise ValueError(f"Invalid shipment type: {shipment_type}. Must be INBOUND or OUTBOUND.")

    # 1. Base setup and pallet un/loading time
    raw_minutes = BASE_SETUP_TEARDOWN_MINUTES + (pallet_count * MINUTES_PER_PALLET)

    # 2. Directional adjustment
    raw_minutes += DIRECTIONAL_ADJUSTMENT[direction]

    # 3. Add handling complexity penalties
    for code in handling_codes:
        code_upper = code.upper()
        if code_upper in HANDLING_PENALTIES:
            raw_minutes += HANDLING_PENALTIES[code_upper]

    # 4. Round up to slot granularity (15 minutes)
    rounded_minutes = int(math.ceil(raw_minutes / SLOT_GRANULARITY_MINUTES) * SLOT_GRANULARITY_MINUTES)

    # 5. Clamp to operational bounds
    clamped_minutes = max(MIN_DURATION_MINUTES, min(rounded_minutes, MAX_DURATION_MINUTES))
    return clamped_minutes
