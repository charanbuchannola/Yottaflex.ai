# Reproducibility & Data Integrity Verification Report

**Final Verdict:** 100% REPRODUCIBLE (BITWISE EQUALITY)  
**Profile Evaluated:** `STARTER`  
**Fixed PRNG Seed:** `20261022`  
**Total Tracked Artifacts:** 34  
**Matching Artifact Checksums:** 34 / 34  

---

## 1. Per-Table Entity Row Count Verification

| Relational Entity Table | Run 1 Row Count | Run 2 Row Count | Verdict |
| :--- | :--- | :--- | :--- |
| `allocation_decisions` | 1,000 | 1,000 | **MATCH** |
| `appointment_shipments` | 1,000 | 1,000 | **MATCH** |
| `appointments` | 1,000 | 1,000 | **MATCH** |
| `carriers` | 10 | 10 | **MATCH** |
| `check_in_events` | 4,735 | 4,735 | **MATCH** |
| `dock_handling_capabilities` | 11 | 11 | **MATCH** |
| `docks` | 20 | 20 | **MATCH** |
| `facilities` | 2 | 2 | **MATCH** |
| `handling_requirements` | 5 | 5 | **MATCH** |
| `labor_shifts` | 28 | 28 | **MATCH** |
| `shipment_handling_requirements` | 423 | 423 | **MATCH** |
| `shipments` | 1,000 | 1,000 | **MATCH** |
| `vehicles` | 40 | 40 | **MATCH** |
| `yard_slots` | 30 | 30 | **MATCH** |

---

## 2. Canonical Artifact SHA-256 Checksum Comparison

| File Relative Path | Run 1 SHA-256 (Truncated) | Run 2 SHA-256 (Truncated) | Match Status |
| :--- | :--- | :--- | :--- |
| `data/ground_truth/ground_truth.csv` | `6b66cbf7ec0c...` | `6b66cbf7ec0c...` | **MATCH** |
| `data/ground_truth/ground_truth.json` | `50d534def5d9...` | `50d534def5d9...` | **MATCH** |
| `exports/csv/allocation_decisions.csv` | `73903b51267c...` | `73903b51267c...` | **MATCH** |
| `exports/csv/appointment_shipments.csv` | `547cd56d8faa...` | `547cd56d8faa...` | **MATCH** |
| `exports/csv/appointments.csv` | `a9952bdf2ac0...` | `a9952bdf2ac0...` | **MATCH** |
| `exports/csv/carriers.csv` | `32d692148c4d...` | `32d692148c4d...` | **MATCH** |
| `exports/csv/check_in_events.csv` | `6a000c03308b...` | `6a000c03308b...` | **MATCH** |
| `exports/csv/dock_handling_capabilities.csv` | `168b9300e044...` | `168b9300e044...` | **MATCH** |
| `exports/csv/docks.csv` | `4af4d8cee054...` | `4af4d8cee054...` | **MATCH** |
| `exports/csv/facilities.csv` | `efafd4e670fc...` | `efafd4e670fc...` | **MATCH** |
| `exports/csv/handling_requirements.csv` | `933f16183990...` | `933f16183990...` | **MATCH** |
| `exports/csv/labor_shifts.csv` | `9d8626f1e2b0...` | `9d8626f1e2b0...` | **MATCH** |
| `exports/csv/shipment_handling_requirements.csv` | `19a8b6963c88...` | `19a8b6963c88...` | **MATCH** |
| `exports/csv/shipments.csv` | `11b9fa4a4d2b...` | `11b9fa4a4d2b...` | **MATCH** |
| `exports/csv/vehicles.csv` | `87720b7728e5...` | `87720b7728e5...` | **MATCH** |
| `exports/csv/yard_slots.csv` | `b3f51f42aa8f...` | `b3f51f42aa8f...` | **MATCH** |
| `exports/json/allocation_decisions.json` | `0ad8cd365321...` | `0ad8cd365321...` | **MATCH** |
| `exports/json/appointment_shipments.json` | `74f57fc45929...` | `74f57fc45929...` | **MATCH** |
| `exports/json/appointments.json` | `0a747f38ef27...` | `0a747f38ef27...` | **MATCH** |
| `exports/json/carriers.json` | `1d5ea567872d...` | `1d5ea567872d...` | **MATCH** |
| `exports/json/check_in_events.json` | `7a4aa2d61f5a...` | `7a4aa2d61f5a...` | **MATCH** |
| `exports/json/dock_handling_capabilities.json` | `0873eadf6055...` | `0873eadf6055...` | **MATCH** |
| `exports/json/docks.json` | `de44c533580e...` | `de44c533580e...` | **MATCH** |
| `exports/json/facilities.json` | `4ea6edfab8c3...` | `4ea6edfab8c3...` | **MATCH** |
| `exports/json/handling_requirements.json` | `32e243c74afc...` | `32e243c74afc...` | **MATCH** |
| `exports/json/labor_shifts.json` | `8ca6036caf6b...` | `8ca6036caf6b...` | **MATCH** |
| `exports/json/shipment_handling_requirements.json` | `05c68bf75e27...` | `05c68bf75e27...` | **MATCH** |
| `exports/json/shipments.json` | `f684d6fb68ea...` | `f684d6fb68ea...` | **MATCH** |
| `exports/json/vehicles.json` | `2225f09e2786...` | `2225f09e2786...` | **MATCH** |
| `exports/json/yard_slots.json` | `289894584071...` | `289894584071...` | **MATCH** |
| `exports/reports/evaluation_metrics.json` | `f7ce096484b1...` | `f7ce096484b1...` | **MATCH** |
| `exports/reports/validation_report.json` | `96050c16e022...` | `96050c16e022...` | **MATCH** |
| `exports/sql/schema.sql` | `c64ba2f58ba0...` | `c64ba2f58ba0...` | **MATCH** |
| `exports/sql/seed.sql` | `9f6bb6fe2c15...` | `9f6bb6fe2c15...` | **MATCH** |

---

## 3. Analytical Metric Consistency

| Operational KPI | Run 1 Value | Run 2 Value | Match Status |
| :--- | :--- | :--- | :--- |
| Allocation Success Rate | 0.548 | 0.548 | **MATCH** |
| Dock Utilization Rate | 0.2698 | 0.2698 | **MATCH** |
| Average Wait Time (min) | 9.73 | 9.73 | **MATCH** |
| Exception Detection F1 | 1.0 | 1.0 | **MATCH** |

---

## 4. Deterministic Canonicalization Protocol

Reproducibility across repeated executions is guaranteed through strict adherence to:
1. **Fixed PRNG Seed**: Pure functional sequence generation rooted in `random.Random(20261022)`.
2. **Lexicographical Sort Orders**: All CSV and JSON exports are deterministically sorted by primary key prior to emission.
3. **Zero Volatile Timestamps**: Canonical files contain exclusively simulation timeline timestamps (`YYYY-MM-DDTHH:MM:SSZ`), separating deterministic dataset contents from ephemeral execution metadata.
4. **Exact Float Precision**: Numerical quantities are bounded to explicit rounding precisions.
