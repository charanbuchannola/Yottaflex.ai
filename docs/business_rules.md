# Business Rules & Scheduling Engine Specification

---

## 1. Rule Catalogue Summary

Every scheduling decision in the YottaFlex AI platform is governed by explicit, deterministic business rules. Each rule has a stable identifier, a formal invariant, an evaluation phase, and an auditable outcome.

| Rule ID | Category | Name | Formal Invariant / Condition | Structured Rejection Code |
| :--- | :--- | :--- | :--- | :--- |
| **BR-DUR-001** | Duration | Service Duration Derivation | $T_{\text{service}} = T_{\text{base}} + (\text{pallets} \times T_{\text{pallet}}) + \sum T_{\text{handling\_penalties}}$ | N/A (Derived parameter) |
| **BR-FAC-001** | Facility | Operating Hours Compliance | $\text{Start} \ge \text{Facility.Open} \land \text{End} \le \text{Facility.Close}$ | `ERR_OUTSIDE_OPERATING_HOURS` |
| **BR-WIN-001** | Window | Requested Interval Fit | $[\text{Start}, \text{End}) \subseteq [\text{Req.WindowStart}, \text{Req.WindowEnd})$ | `ERR_OUTSIDE_REQUESTED_WINDOW` |
| **BR-COMP-001**| Compatibility | Cold Chain Compliance | $\text{Shipment.NeedsColdChain} \implies \text{Dock.HasColdChain} \land \text{Vehicle.IsReefer}$ | `ERR_INCOMPATIBLE_COLD_CHAIN` |
| **BR-COMP-002**| Compatibility | Hazmat Compliance | $\text{Shipment.IsHazmat} \implies \text{Dock.HasHazmatPermit}$ | `ERR_INCOMPATIBLE_HAZMAT` |
| **BR-COMP-003**| Compatibility | Vehicle Physical Docking | $\text{Vehicle.RequiresLiftgate} \implies (\text{Dock.HasLeveler} \lor \text{Vehicle.HasLiftgate})$ | `ERR_INCOMPATIBLE_VEHICLE_DOCK` |
| **BR-CAP-001** | Capacity | Dock Non-Overlap (Intervals) | For all existing appts $A_i$ on Dock $D$: $[\text{Start}, \text{End}) \cap [A_{i}.\text{Start}, A_{i}.\text{End}) = \emptyset$ | `ERR_DOCK_OCCUPIED` |
| **BR-CAP-002** | Capacity | Yard Slot Non-Overlap | If yard staging required: $[\text{Start}_{\text{yard}}, \text{End}_{\text{yard}}) \cap [Y_j.\text{Start}, Y_j.\text{End}) = \emptyset$ | `ERR_YARD_CAPACITY_EXCEEDED` |
| **BR-LAB-001** | Labor | General Staffing Available | For all $t \in [\text{Start}, \text{End})$, $\sum \text{AllocatedWorkers}(t) + \text{ReqWorkers} \le \text{Shift.TotalWorkers}(t)$ | `ERR_LABOR_UNAVAILABLE` |
| **BR-LAB-002** | Labor | Forklift Operator Qualified | If palletized: $\sum \text{AllocatedForklift}(t) + 1 \le \text{Shift.ForkliftWorkers}(t)$ | `ERR_FORKLIFT_OPERATOR_UNAVAILABLE` |
| **BR-LAB-003** | Labor | Hazmat Certified Staff | If hazmat: $\sum \text{AllocatedHazmat}(t) + 1 \le \text{Shift.HazmatWorkers}(t)$ | `ERR_HAZMAT_WORKER_UNAVAILABLE` |
| **BR-RES-001** | Reservation | Atomic Resource Lock | Successful allocation locks (Dock, YardSlot, Labor) atomically in a single DB transaction. | `ERR_CONCURRENT_ALLOCATION_CONFLICT` |
| **BR-SIM-001** | Simulation | Monotonic Event Timeline | $t_{\text{requested}} \le t_{\text{allocated}} \le t_{\text{arrived}} \le t_{\text{checked\_in}} \le t_{\text{service\_start}} \le t_{\text{service\_end}} \le t_{\text{departed}}$ | `ERR_INVALID_EVENT_SEQUENCE` |
| **BR-SIM-002** | Simulation | Idempotent Event Delivery | $\text{SequenceNumber}_{i} = \text{SequenceNumber}_{i-1} + 1$; duplicate `event_id` raises duplicate exception. | `ERR_DUPLICATE_EVENT` |
| **BR-SIM-003** | Simulation | Check-in Calendar Match | $\text{Date}(\text{OccurrenceTime}) = \text{Date}(\text{ScheduledStart})$ | `ERR_PRE_DATE_CHECKIN` |

---

## 2. Deterministic Service Duration Formula (BR-DUR-001)

Randomly generated durations are prohibited by Section 10. The system derives service durations using a transparent deterministic formula:

$$\text{Duration (minutes)} = T_{\text{base}} + (\text{PalletCount} \times R_{\text{pallet}}) + C_{\text{direction}} + \sum C_{\text{handling\_reqs}}$$

### Parameter Coefficients:
1. **$T_{\text{base}}$ (Baseline Setup & Teardown Time)**:
   - Standard Truck Docking & Inspection: **15 minutes**.
2. **Pallet Handling Rate ($R_{\text{pallet}}$)**:
   - **1.5 minutes per pallet**.
   - Example: 20 pallets = $20 \times 1.5 = 30$ minutes.
3. **Directional Adjustment ($C_{\text{direction}}$)**:
   - `INBOUND` (Unload + QC Inspection + Staging): **+10 minutes**.
   - `OUTBOUND` (Verification + Loading + Seal Inspection): **+5 minutes**.
4. **Handling Complexity Adders ($C_{\text{handling\_reqs}}$)**:
   - `REEFER` (Temperature log verification & seal inspection): **+15 minutes**.
   - `HAZMAT` (Hazardous manifest review, placard check, segregation check): **+25 minutes**.
   - `FRAGILE` (Manual visual inspection, strapping): **+10 minutes**.
   - `OVERSIZED` (Specialized handling, wide-turn maneuvers): **+15 minutes**.
5. **Rounding & Bounds**:
   - Total derived duration is rounded up to the nearest **15-minute slot boundary**.
   - Minimum service duration: **30 minutes**.
   - Maximum service duration: **240 minutes** (4 hours).

---

## 3. Half-Open Interval Semantics

All time-window allocations and collision detections utilize **half-open intervals**:
$$[t_{\text{start}}, t_{\text{end}}) \equiv \{t \mid t_{\text{start}} \le t < t_{\text{end}}\}$$

### Boundary Non-Conflict Theorem:
Two appointments $A_1 = [08:00, 09:00)$ and $A_2 = [09:00, 10:00)$ scheduled on the same dock do **not** conflict:
$$[08:00, 09:00) \cap [09:00, 10:00) = \emptyset$$
This eliminates artificial buffer dead-time while guaranteeing that no two vehicles occupy the same physical dock door or yard slot simultaneously.

---

## 4. Candidate Slot Search & Deterministic Tie-Breaking (BR-SCHED-TIE)

When an appointment request is submitted with a broad window (e.g., requested delivery between 08:00 and 16:00), the scheduler generates discrete candidate intervals based on a 15-minute search step:
$$t_{\text{candidate}} \in \{W_{\text{start}}, W_{\text{start}} + 15\text{m}, W_{\text{start}} + 30\text{m}, \dots, W_{\text{end}} - \text{Duration}\}$$

For each candidate start time:
1. **Dock Candidate Selection**:
   - Filter active docks in facility matching shipment direction (`INBOUND`, `OUTBOUND`, or `CROSS_DOCK`).
   - Filter docks satisfying Cold Chain (BR-COMP-001) and Hazmat (BR-COMP-002).
   - Filter docks accommodating the vehicle type (BR-COMP-003).
2. **Conflict Evaluation**:
   - Check if dock is free over $[t_{\text{candidate}}, t_{\text{candidate}} + \text{Duration})$.
   - Check if labor shift covers $[t_{\text{candidate}}, t_{\text{candidate}} + \text{Duration})$ and required worker headcount is available.
   - If yard staging slot is required, check yard slot availability.
3. **Deterministic Tie-Breaking Rule**:
   - **Primary Criterion**: Earliest `start_time`.
   - **Secondary Criterion**: Lowest numerical `dock_id` (e.g. `DOCK-FAC-001-001` beats `DOCK-FAC-001-002`).
   - **Tertiary Criterion**: Lowest `yard_slot_id`.
   - **Quaternary Criterion**: Lowest `labor_shift_id`.

If no feasible slot satisfies all constraints within the requested window, the allocation engine returns a structured rejection detailing the exact constraint failure.

---

## 5. Structured Rejection Payloads

Rejection is never returned as a raw boolean or generic string. It yields an auditable `AllocationDecision` record containing:
```json
{
  "decision_id": "DEC-APPT-2026-000001-01",
  "appointment_id": "APPT-2026-000001",
  "facility_id": "FAC-001",
  "decision_status": "REJECTED",
  "rule_evaluated": "BR-COMP-002",
  "rejection_reason": "ERR_INCOMPATIBLE_HAZMAT",
  "context_metadata": {
    "shipment_hazmat": true,
    "compatible_docks_at_facility": 0,
    "candidate_windows_evaluated": 16,
    "evaluated_at": "2026-10-22T08:00:00Z"
  }
}
```
