"""Deterministic Constraint-Aware Appointment Scheduling Engine."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
from typing import Sequence

from logistics.generators.identifiers import generate_allocation_decision_id
from logistics.models.appointment import AllocationDecision, Appointment
from logistics.models.facility import Dock, Facility, YardSlot
from logistics.models.labor import LaborShift
from logistics.models.shipment import Shipment
from logistics.scheduler.rules import AllocationResult, RejectionCode, RuleId
from logistics.scheduler.service_duration import calculate_service_duration


def intervals_overlap(s1: datetime, e1: datetime, s2: datetime, e2: datetime) -> bool:
    """Evaluate half-open interval overlap: [s1, e1) and [s2, e2)."""
    return max(s1, s2) < min(e1, e2)


class SchedulerState:
    """In-memory interval ledger tracking reservations and labor capacity across simulation time."""

    def __init__(self):
        # dock_id -> list of (start_time, end_time, appointment_id)
        self.dock_reservations: dict[str, list[tuple[datetime, datetime, str]]] = defaultdict(list)
        # yard_slot_id -> list of (start_time, end_time, appointment_id)
        self.yard_reservations: dict[str, list[tuple[datetime, datetime, str]]] = defaultdict(list)
        # shift_id -> list of (start_time, end_time, workers_used, forklift_used, hazmat_used)
        self.labor_reservations: dict[str, list[tuple[datetime, datetime, int, int, int]]] = defaultdict(list)

    def is_dock_free(self, dock_id: str, start: datetime, end: datetime) -> bool:
        """Verify that dock has no overlapping reservation in [start, end)."""
        for r_start, r_end, _ in self.dock_reservations.get(dock_id, []):
            if intervals_overlap(start, end, r_start, r_end):
                return False
        return True

    def is_yard_slot_free(self, yard_slot_id: str, start: datetime, end: datetime) -> bool:
        """Verify that yard slot has no overlapping reservation in [start, end)."""
        for r_start, r_end, _ in self.yard_reservations.get(yard_slot_id, []):
            if intervals_overlap(start, end, r_start, r_end):
                return False
        return True

    def check_and_reserve_labor(
        self,
        shift: LaborShift,
        start: datetime,
        end: datetime,
        req_workers: int = 2,
        req_forklift: int = 1,
        req_hazmat: int = 0,
        commit: bool = False,
    ) -> bool:
        """Verify that labor shift has sufficient concurrent headcount throughout [start, end)."""
        # Sum concurrent workers currently reserved during this interval
        concurrent_total = 0
        concurrent_forklift = 0
        concurrent_hazmat = 0

        for r_start, r_end, w, f, h in self.labor_reservations.get(shift.shift_id, []):
            if intervals_overlap(start, end, r_start, r_end):
                concurrent_total += w
                concurrent_forklift += f
                concurrent_hazmat += h

        if concurrent_total + req_workers > shift.total_workers:
            return False
        if concurrent_forklift + req_forklift > shift.forklift_certified_workers:
            return False
        if concurrent_hazmat + req_hazmat > shift.hazmat_certified_workers:
            return False

        if commit:
            self.labor_reservations[shift.shift_id].append(
                (start, end, req_workers, req_forklift, req_hazmat)
            )
        return True

    def reserve(
        self,
        dock_id: str,
        start: datetime,
        end: datetime,
        appointment_id: str,
        yard_slot_id: str | None = None,
        shift: LaborShift | None = None,
        req_workers: int = 2,
        req_forklift: int = 1,
        req_hazmat: int = 0,
    ) -> None:
        """Commit atomic reservations across dock, yard, and labor pools."""
        self.dock_reservations[dock_id].append((start, end, appointment_id))
        if yard_slot_id:
            self.yard_reservations[yard_slot_id].append((start, end, appointment_id))
        if shift:
            self.check_and_reserve_labor(
                shift=shift,
                start=start,
                end=end,
                req_workers=req_workers,
                req_forklift=req_forklift,
                req_hazmat=req_hazmat,
                commit=True,
            )


class SchedulingEngine:
    """Deterministic, constraint-aware logistics appointment allocation engine."""

    def __init__(self, state: SchedulerState | None = None):
        self.state = state or SchedulerState()

    def evaluate_appointment(
        self,
        appointment: Appointment,
        shipments: Sequence[Shipment],
        facility: Facility,
        docks: Sequence[Dock],
        yard_slots: Sequence[YardSlot],
        shifts: Sequence[LaborShift],
        handling_codes: Sequence[str] = (),
    ) -> AllocationResult:
        """Evaluate all business rules and search for candidate slot (BR-FAC-001 through BR-LAB-003)."""
        duration = appointment.duration_minutes
        if duration <= 0:
            total_pallets = sum(s.pallet_count for s in shipments) or 20
            duration = calculate_service_duration(total_pallets, appointment.appointment_type, handling_codes)
            appointment.duration_minutes = duration

        duration_td = timedelta(minutes=duration)

        # 1. Check Window Width
        req_width = appointment.requested_end - appointment.requested_start
        if req_width < duration_td:
            return AllocationResult(
                is_allocated=False,
                rule_evaluated=RuleId.BR_WIN_001,
                decision_status="REJECTED",
                rejection_reason=RejectionCode.ERR_OUTSIDE_REQUESTED_WINDOW,
                duration_minutes=duration,
                metadata={"requested_width_min": req_width.total_seconds() / 60, "duration_min": duration},
            )

        # 2. Check Compatibility & Filter Docks
        is_reefer = "REEFER" in handling_codes
        is_hazmat = "HAZMAT" in handling_codes

        compatible_docks: list[Dock] = []
        for dock in docks:
            if not dock.is_active:
                continue
            if dock.dock_type != "CROSS_DOCK" and dock.dock_type != appointment.appointment_type:
                continue
            if is_reefer and not dock.has_cold_chain:
                continue
            if is_hazmat and not dock.has_hazmat_permit:
                continue
            compatible_docks.append(dock)

        # Sort docks deterministically by dock_id ASC (BR-SCHED-TIE)
        compatible_docks.sort(key=lambda d: d.dock_id)

        if not compatible_docks:
            rejection_reason = (
                RejectionCode.ERR_INCOMPATIBLE_HAZMAT if is_hazmat
                else RejectionCode.ERR_INCOMPATIBLE_COLD_CHAIN if is_reefer
                else RejectionCode.ERR_NO_DOCK_CAPACITY
            )
            return AllocationResult(
                is_allocated=False,
                rule_evaluated=RuleId.BR_COMP_002 if is_hazmat else RuleId.BR_COMP_001,
                decision_status="REJECTED",
                rejection_reason=rejection_reason,
                duration_minutes=duration,
                metadata={"is_reefer": is_reefer, "is_hazmat": is_hazmat, "total_docks": len(docks)},
            )

        # 3. Discrete Candidate Slot Search (15-minute grid)
        candidate_time = appointment.requested_start
        # Align to 15-minute boundary
        minute_rem = candidate_time.minute % 15
        if minute_rem != 0:
            candidate_time += timedelta(minutes=(15 - minute_rem))

        saw_operating_hours_violation = False
        saw_labor_shortage = False

        while candidate_time + duration_td <= appointment.requested_end:
            slot_end = candidate_time + duration_td

            # Check Facility Operating Hours (BR-FAC-001)
            # In UTC, operating hours check
            if candidate_time.hour < facility.operating_start_hour or slot_end.hour > facility.operating_end_hour:
                saw_operating_hours_violation = True
                candidate_time += timedelta(minutes=15)
                continue

            # Find matching labor shift covering [candidate_time, slot_end)
            covering_shift: LaborShift | None = None
            for shift in shifts:
                if shift.facility_id == facility.facility_id:
                    if shift.start_time <= candidate_time and shift.end_time >= slot_end:
                        covering_shift = shift
                        break

            if not covering_shift:
                saw_labor_shortage = True
                candidate_time += timedelta(minutes=15)
                continue

            req_hazmat_workers = 1 if is_hazmat else 0
            if not self.state.check_and_reserve_labor(
                shift=covering_shift,
                start=candidate_time,
                end=slot_end,
                req_workers=2,
                req_forklift=1,
                req_hazmat=req_hazmat_workers,
                commit=False,
            ):
                saw_labor_shortage = True
                candidate_time += timedelta(minutes=15)
                continue

            # Evaluate Compatible Docks in deterministic order
            for dock in compatible_docks:
                if self.state.is_dock_free(dock.dock_id, candidate_time, slot_end):
                    # Select available yard slot if available (optional)
                    selected_yard_slot: str | None = None
                    for y_slot in sorted(yard_slots, key=lambda y: y.yard_slot_id):
                        if self.state.is_yard_slot_free(y_slot.yard_slot_id, candidate_time, slot_end):
                            selected_yard_slot = y_slot.yard_slot_id
                            break

                    # Commit reservations atomically
                    self.state.reserve(
                        dock_id=dock.dock_id,
                        start=candidate_time,
                        end=slot_end,
                        appointment_id=appointment.appointment_id,
                        yard_slot_id=selected_yard_slot,
                        shift=covering_shift,
                        req_workers=2,
                        req_forklift=1,
                        req_hazmat=req_hazmat_workers,
                    )

                    return AllocationResult(
                        is_allocated=True,
                        rule_evaluated=RuleId.BR_RES_001,
                        decision_status="ALLOCATED",
                        scheduled_start=candidate_time,
                        scheduled_end=slot_end,
                        dock_id=dock.dock_id,
                        yard_slot_id=selected_yard_slot,
                        duration_minutes=duration,
                        metadata={
                            "dock_id": dock.dock_id,
                            "yard_slot_id": selected_yard_slot,
                            "shift_id": covering_shift.shift_id,
                        },
                    )

            candidate_time += timedelta(minutes=15)

        # Determine diagnostic rejection cause
        if saw_operating_hours_violation and not saw_labor_shortage:
            rejection = RejectionCode.ERR_OUTSIDE_OPERATING_HOURS
            rule = RuleId.BR_FAC_001
        elif saw_labor_shortage:
            rejection = RejectionCode.ERR_LABOR_UNAVAILABLE
            rule = RuleId.BR_LAB_001
        else:
            rejection = RejectionCode.ERR_DOCK_OCCUPIED
            rule = RuleId.BR_CAP_001

        return AllocationResult(
            is_allocated=False,
            rule_evaluated=rule,
            decision_status="REJECTED",
            rejection_reason=rejection,
            duration_minutes=duration,
            metadata={"evaluated_at": appointment.requested_start.isoformat()},
        )

    def allocate_appointment(
        self,
        appointment: Appointment,
        shipments: Sequence[Shipment],
        facility: Facility,
        docks: Sequence[Dock],
        yard_slots: Sequence[YardSlot],
        shifts: Sequence[LaborShift],
        handling_codes: Sequence[str] = (),
        decision_seq: int = 1,
    ) -> AllocationDecision:
        """Execute evaluation and construct auditable AllocationDecision entity."""
        result = self.evaluate_appointment(
            appointment=appointment,
            shipments=shipments,
            facility=facility,
            docks=docks,
            yard_slots=yard_slots,
            shifts=shifts,
            handling_codes=handling_codes,
        )

        dec_id = generate_allocation_decision_id(appointment.appointment_id, decision_seq)
        eval_time = appointment.requested_start

        if result.is_allocated:
            appointment.dock_id = result.dock_id
            appointment.yard_slot_id = result.yard_slot_id
            appointment.scheduled_start = result.scheduled_start
            appointment.scheduled_end = result.scheduled_end
            appointment.duration_minutes = result.duration_minutes
            appointment.status = "ALLOCATED"

            decision = AllocationDecision(
                decision_id=dec_id,
                appointment_id=appointment.appointment_id,
                facility_id=facility.facility_id,
                dock_id=result.dock_id,
                yard_slot_id=result.yard_slot_id,
                evaluated_at=eval_time,
                decision_status="ALLOCATED",
                rule_evaluated=result.rule_evaluated.value,
                rejection_reason=None,
                context_metadata_json=json.dumps(result.metadata),
            )
        else:
            appointment.status = "REJECTED"
            appointment.dock_id = None
            appointment.yard_slot_id = None
            appointment.scheduled_start = None
            appointment.scheduled_end = None

            decision = AllocationDecision(
                decision_id=dec_id,
                appointment_id=appointment.appointment_id,
                facility_id=facility.facility_id,
                dock_id=None,
                yard_slot_id=None,
                evaluated_at=eval_time,
                decision_status="REJECTED",
                rule_evaluated=result.rule_evaluated.value,
                rejection_reason=result.rejection_reason.value if result.rejection_reason else None,
                context_metadata_json=json.dumps(result.metadata),
            )

        return decision
