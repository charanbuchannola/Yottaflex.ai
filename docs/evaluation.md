# Evaluation, Validation, & Ground-Truth Specification

---

## 1. Exception Simulation Matrix (The 7 Required Scenarios)

The platform generates pristine, rule-compliant baseline data first. Controlled operational anomalies are subsequently injected through an explicit scenario layer with traceable provenance, explicit scenario IDs, and pre-calculated ground-truth expectations.

| Scenario ID | Scenario Name | Mutation / Condition Injected | Expected Engine / Validator Outcome | Ground-Truth Label | Target Entity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SCEN-01`** | Overlapping Appointments | Forces simultaneous assignment of 2 appointments to the same dock during overlapping intervals. | Engine: `ERR_DOCK_OCCUPIED`. Validator: Flags collision on dock. | `ANOMALY_OVERLAP` | `Appointment` / `Dock` |
| **`SCEN-02`** | Incompatible Dock Assignment | Forces a HAZMAT shipment to be assigned to a non-hazmat certified dock. | Engine: `ERR_INCOMPATIBLE_HAZMAT`. Validator: Flags compatibility defect. | `ANOMALY_INCOMPATIBLE_DOCK` | `Appointment` / `Dock` |
| **`SCEN-03`** | Pre-Date Check-In | Driver check-in event timestamp occurs 24 hours prior to scheduled calendar appointment date. | Engine: Rejects early gate entry. Validator: Flags pre-date check-in violation. | `ANOMALY_PRE_DATE_CHECKIN` | `CheckInEvent` |
| **`SCEN-04`** | Labor Unavailable During Service | Allocates appointment requiring 2 forklift operators during a window where active shift has 0 certified staff. | Engine: `ERR_FORKLIFT_OPERATOR_UNAVAILABLE`. Validator: Flags labor deficit. | `ANOMALY_LABOR_UNAVAILABLE` | `Appointment` / `LaborShift` |
| **`SCEN-05`** | Unrecorded No-Show | Vehicle never arrives; no check-in event emitted. Detected as an unrecorded absence past observation window ($t > t_{\text{end}} + 120\text{m}$). | Validator / Auditor: Flags missing arrival / ghost booking. | `ANOMALY_UNRECORDED_NO_SHOW` | `Appointment` |
| **`SCEN-06`** | Early Vehicle Arrival | Vehicle arrives 180 minutes prior to scheduled start time; tests yard staging vs gate hold queue. | Simulation: Stages vehicle in YardSlot without dock contention. | `OPERATIONAL_EARLY_ARRIVAL` | `CheckInEvent` / `YardSlot` |
| **`SCEN-07`** | Peak-Hour Congestion | Concentrates 15 appointment requests into a single 60-minute window at an 8-dock facility. | Engine: Allocates 8 docks to capacity; gracefully rejects 7 with `ERR_NO_DOCK_CAPACITY`. | `CONGESTION_REJECTION` | `AllocationDecision` |

---

## 2. Ground-Truth Data Leakage Prevention

### Physical & Logical Segregation:
1. **Isolated Storage**: Ground-truth labels are written strictly to:
   - `data/ground_truth/ground_truth.csv`
   - `data/ground_truth/ground_truth.json`
2. **Zero Ingestion into Domain Code**: The scheduling engine (`logistics.scheduler.engine`) has zero code imports from the anomaly generator or ground-truth schemas.
3. **Operational Feature Purity**: Normal operational exports (`exports/csv/appointments.csv`, `exports/json/appointments.json`) contain zero scenario or ground-truth columns (`scenario_id`, `issue_type`, `ground_truth_label` are completely absent).
4. **Validation Separation**: The validator evaluates the operational database against relational invariants independently, then maps detected violations against ground truth to calculate confusion matrices.

### Ground-Truth Schema:
```json
{
  "record_id": "APPT-2026-000105",
  "entity_type": "APPOINTMENT",
  "issue_type": "INCOMPATIBLE_DOCK",
  "scenario_id": "SCEN-02",
  "expected_decision": "REJECT",
  "ground_truth_label": "ANOMALY_INCOMPATIBLE_DOCK",
  "root_cause": "Shipment SHP-2026-000105 requires HAZMAT permit but DOCK-FAC-001-002 lacks hazmat certification."
}
```

---

## 3. Dual-Mode Automated Validation Framework

The platform implements 19 automated rule checks executed across two distinct contexts:

### Context A: Baseline Validation
- Executed on uncorrupted baseline generation.
- **Strict Invariant**: Zero unexpected errors allowed. Every single record must pass 100% of foreign-key, interval, capacity, and compatibility invariants.

### Context B: Anomaly-Aware Validation
- Executed after scenario injection.
- **Strict Invariant**: Every injected scenario must be detected and matched with its expected rule violation ($FN = 0$). No collateral corruption of non-scenario baseline records is permitted ($FP = 0$).

### 19 Automated Validator Checks:
1. `VAL-PK-001`: Primary key uniqueness across all 14 relational tables.
2. `VAL-BID-001`: Business ID format pattern compliance and namespace uniqueness.
3. `VAL-FK-001`: Referential integrity (zero orphaned foreign keys).
4. `VAL-ENUM-001`: Enumeration domain membership for status, vehicle, and dock types.
5. `VAL-REQ-001`: Mandatory column nullability constraints.
6. `VAL-INT-001`: Date/time chronological ordering ($t_{\text{start}} < t_{\text{end}}$).
7. `VAL-FSM-001`: Lifecycle state transition legality against FSM graph.
8. `VAL-SEQ-001`: Event sequence monotonic increment ($seq_{i} = seq_{i-1} + 1$).
9. `VAL-IDEMP-001`: Event idempotency (no duplicate event IDs).
10. `VAL-DUR-001`: Service duration mathematical consistency with BR-DUR-001.
11. `VAL-CAP-001`: Dock capacity non-overlap ($[s_1, e_1) \cap [s_2, e_2) = \emptyset$).
12. `VAL-CAP-002`: Yard slot non-overlap.
13. `VAL-COMP-001`: Cold chain dock/vehicle compatibility.
14. `VAL-COMP-002`: Hazmat dock certification compatibility.
15. `VAL-COMP-003`: Liftgate physical dock compatibility.
16. `VAL-LAB-001`: Labor shift coverage and worker headcount sufficiency.
17. `VAL-HOURS-001`: Operating hours compliance with facility schedule.
18. `VAL-GT-001`: Ground-truth referential consistency and label separation.
19. `VAL-XFILE-001`: Cross-file relational integrity across CSV, JSON, and SQLite.

### Structure of `validation_report.json`:
```json
{
  "run_id": "VAL-RUN-20261028-01",
  "seed": 20261022,
  "profile": "STARTER",
  "total_records_checked": 5420,
  "checks_executed": 19,
  "checks_passed": 19,
  "checks_failed": 0,
  "expected_violations_detected": 14,
  "unexpected_violations_detected": 0,
  "final_validation_status": "PASSED"
}
```

---

## 4. Measurable Operational KPIs

All metrics are calculated directly from physical records:

$$\text{Allocation Success Rate} = \frac{N_{\text{allocated}}}{N_{\text{requested}}}$$

$$\text{Dock Utilization} = \frac{\sum_{\text{allocated}} \text{Duration (hours)}}{\text{Total Docks} \times \text{Operating Hours/Day} \times \text{Days}}$$

$$\text{Yard Utilization} = \frac{\sum_{\text{staged}} \text{Staging Time (hours)}}{\text{Total Yard Slots} \times 24\,\text{h} \times \text{Days}}$$

$$\text{Average Waiting Time} = \frac{1}{N_{\text{serviced}}} \sum (t_{\text{service\_started}} - t_{\text{arrived}})$$

$$\text{P95 Waiting Time} = \text{95th percentile of } (t_{\text{service\_started}} - t_{\text{arrived}})$$

$$\text{Early Arrival Rate} = \frac{N_{\text{arrived before window}}}{N_{\text{total arrived}}}$$

$$\text{Unrecorded No-Show Rate} = \frac{N_{\text{allocated without arrival}}}{N_{\text{total allocated}}}$$

$$\text{Exception Detection Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F_1 = 2 \times \frac{P \times R}{P + R}$$
