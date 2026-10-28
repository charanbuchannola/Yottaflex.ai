"""Business Rule Identifiers, Structured Error Codes, and Evaluation Structures."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RejectionCode(str, Enum):
    """Standardized machine-readable rejection reasons."""
    ERR_OUTSIDE_OPERATING_HOURS = "ERR_OUTSIDE_OPERATING_HOURS"
    ERR_OUTSIDE_REQUESTED_WINDOW = "ERR_OUTSIDE_REQUESTED_WINDOW"
    ERR_INCOMPATIBLE_COLD_CHAIN = "ERR_INCOMPATIBLE_COLD_CHAIN"
    ERR_INCOMPATIBLE_HAZMAT = "ERR_INCOMPATIBLE_HAZMAT"
    ERR_INCOMPATIBLE_VEHICLE_DOCK = "ERR_INCOMPATIBLE_VEHICLE_DOCK"
    ERR_NO_DOCK_CAPACITY = "ERR_NO_DOCK_CAPACITY"
    ERR_DOCK_OCCUPIED = "ERR_DOCK_OCCUPIED"
    ERR_YARD_CAPACITY_EXCEEDED = "ERR_YARD_CAPACITY_EXCEEDED"
    ERR_LABOR_UNAVAILABLE = "ERR_LABOR_UNAVAILABLE"
    ERR_FORKLIFT_OPERATOR_UNAVAILABLE = "ERR_FORKLIFT_OPERATOR_UNAVAILABLE"
    ERR_HAZMAT_WORKER_UNAVAILABLE = "ERR_HAZMAT_WORKER_UNAVAILABLE"


class RuleId(str, Enum):
    """Authoritative business rule catalogue identifiers."""
    BR_DUR_001 = "BR-DUR-001"
    BR_FAC_001 = "BR-FAC-001"
    BR_WIN_001 = "BR-WIN-001"
    BR_COMP_001 = "BR-COMP-001"
    BR_COMP_002 = "BR-COMP-002"
    BR_COMP_003 = "BR-COMP-003"
    BR_CAP_001 = "BR-CAP-001"
    BR_CAP_002 = "BR-CAP-002"
    BR_LAB_001 = "BR-LAB-001"
    BR_LAB_002 = "BR-LAB-002"
    BR_LAB_003 = "BR-LAB-003"
    BR_RES_001 = "BR-RES-001"


@dataclass
class AllocationResult:
    """Detailed result of a single appointment allocation evaluation."""
    is_allocated: bool
    rule_evaluated: RuleId
    decision_status: str  # "ALLOCATED" or "REJECTED"
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    dock_id: str | None = None
    yard_slot_id: str | None = None
    duration_minutes: int = 0
    rejection_reason: RejectionCode | None = None
    metadata: dict = field(default_factory=dict)
