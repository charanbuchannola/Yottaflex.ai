# YottaFlex AI — Synthetic Logistics Appointment Scheduling Platform
### Forward Deployed Engineer 72-Hour Code Challenge Submission

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://www.sqlalchemy.org)
[![Tests Passing](https://img.shields.io/badge/pytest-47%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Executive Summary & Business Scope

Logistics distribution facilities handle complex, multi-modal freight movements subject to severe physical, equipment, and labor constraints. Misallocations lead to yard gridlock, driver detention demurrage, labor idle-time, and regulatory safety breaches (e.g., hazmat segregation failures).

This repository implements a **locally runnable, high-throughput, deterministic synthetic logistics appointment scheduling platform**. It provides:
1. **Normalized Relational Domain Modeling**: 14 tables in SQLAlchemy 2.0 enforcing referential integrity and database constraints.
2. **Deterministic Constraint-Aware Allocation Engine**: Strict multi-resource fit evaluating operating hours, dock capabilities (cold chain, hazmat), yard capacity, and labor shift certified worker headcounts.
3. **Append-Only Event Sourcing**: Immutable lifecycle event ledger with reconstructible current-state projections.
4. **Controlled Exception Simulation**: Controlled injection of the 7 required operational exception scenarios with explicit ground-truth provenance.
5. **Zero Data Leakage Protocol**: Physical and logical segregation of ground-truth evaluation labels from operational data features.
6. **Dual-Mode Automated Validation**: 19 automated rule validators verifying baseline purity and anomaly detection.
7. **Bitwise Reproducibility**: Exact canonical hashing and SHA-256 source manifest generation.

### Primary Actors & Operational Workflows
- **Supplier**: Originates outbound shipments, specifies handling requirements (cold chain, hazmat), and requests delivery slots.
- **Planner**: Evaluates facility calendars and executes deterministic, multi-resource slot allocations.
- **Carrier / Warehouse Operator**: Executes gate arrivals, check-ins, yard staging, and loading/unloading operations.
- **Logistics Analyst**: Evaluates operational throughput, resource utilization, driver wait times, and exception detection metrics.
- **Operations Manager**: Manages shift labor allocations, resolves operational exceptions, and audits compliance.

---

## 2. Architecture & Component Responsibilities

The system decouples interfaces, domain logic, persistence, and evaluation:

```
                      +---------------------------------------+
                      |       CLI Commands / FastAPI API      |
                      +---------------------------------------+
                                          |
                      +---------------------------------------+
                      |         Application Services          |
                      | (Scheduling, Simulation, Validation)  |
                      +---------------------------------------+
                        /                 |                 \
                       /                  |                  \
    +-----------------------+ +-----------------------+ +-----------------------+
    |  Deterministic Engine | | Event Sourcing Engine | | Anomaly & GT Engine   |
    |  - Multi-resource fit | | - Append-only journal | | - Provenance tracking |
    |  - Duration formula   | | - State projections   | | - Zero leakage        |
    |  - Tie-breaking       | | - Event sequence      | | - Detection matrix    |
    +-----------------------+ +-----------------------+ +-----------------------+
               \                          |                         /
                \                         |                        /
                 +------------------------------------------------+
                 |            SQLAlchemy 2.0 / SQLite             |
                 | (Normalized Schema, Foreign Keys, Indexes)     |
                 +------------------------------------------------+
                                          |
                 +------------------------------------------------+
                 |         Analytical Exporters & Reports         |
                 |  (CSV, JSON, SQL Seed, Validation, Evaluation) |
                 +------------------------------------------------+
```

| Layer / Module | Implementation Path | Primary Responsibility |
| :--- | :--- | :--- |
| **Configuration** | `src/logistics/config.py` | Pydantic immutable settings, seed anchor (`20261022`), profiles. |
| **ORM Models** | `src/logistics/models/` | Declarative SQLAlchemy schema with strict FKs and CheckConstraints. |
| **Deterministic IDs**| `src/logistics/generators/identifiers.py` | Zero-padded, stable IDs (`FAC-001`, `APPT-2026-000001`, etc.). |
| **Master Generator** | `src/logistics/generators/master_data.py` | Facilities, Docks, Yard Slots, Labor Shifts, Carriers, Vehicles. |
| **Tx Generator** | `src/logistics/generators/transactions.py` | Shipments, handling associations, appointment requests. |
| **Duration Formula** | `src/logistics/scheduler/service_duration.py` | Deterministic duration derivation (`BR-DUR-001`). |
| **Allocation Engine**| `src/logistics/scheduler/engine.py` | Multi-resource candidate slot search & structured rejections. |
| **Event Ledger** | `src/logistics/events/store.py` | Append-only event journaling & projection replay. |
| **Anomaly Injector** | `src/logistics/simulation/anomalies.py` | Controlled mutation of the 7 required exception scenarios. |
| **Ground Truth** | `src/logistics/analytics/ground_truth.py` | Segregated ground-truth CSV/JSON export with zero feature leakage. |
| **Validator Suite** | `src/logistics/validators/runner.py` | 19 automated rule checks (Dual-Mode: Baseline vs Anomaly-Aware). |
| **Metrics Engine** | `src/logistics/analytics/metrics.py` | KPI calculation (utilization, wait times, confusion matrix). |
| **Canonical Exporter**| `src/logistics/exporters/relational.py`| Canonical CSV, JSON, and SQL DDL/Seed generation. |
| **Manifest Generator**| `src/logistics/exporters/manifest.py` | SHA-256 checksums and source manifest. |
| **REST API** | `src/logistics/api/` | FastAPI endpoints with Pydantic request/response contracts. |
| **CLI Application** | `src/logistics/main.py` | Typer command-line interface. |

---

## 3. Scheduling Algorithm & Business Rules

### Deterministic Service Duration (Rule `BR-DUR-001`)
Duration is calculated strictly from domain parameters rather than random generation:
$$\text{Duration (min)} = T_{\text{base}} + (\text{PalletCount} \times R_{\text{pallet}}) + C_{\text{direction}} + \sum C_{\text{handling\_penalties}}$$
- **Base Setup ($T_{\text{base}}$)**: 15 minutes.
- **Pallet Rate ($R_{\text{pallet}}$)**: 1.5 minutes per pallet.
- **Direction ($C_{\text{direction}}$)**: $+10\,\text{m}$ for `INBOUND`, $+5\,\text{m}$ for `OUTBOUND`.
- **Handling Penalties**: `REEFER` ($+15\,\text{m}$), `HAZMAT` ($+25\,\text{m}$), `FRAGILE` ($+10\,\text{m}$), `OVERSIZED` ($+15\,\text{m}$).
- **Slot Boundary & Clamping**: Rounded up to nearest 15-minute slot boundary; clamped to $[30\,\text{min}, 240\,\text{min}]$.

### Half-Open Interval Semantics
All physical resource bookings use half-open intervals $[t_{\text{start}}, t_{\text{end}})$. Two appointments touching at the boundary ($[08:00, 09:00)$ and $[09:00, 10:00)$) do **not** conflict.

### Candidate Search & Deterministic Tie-Breaking
1. Discrete 15-minute candidate grid search within requested window.
2. Facility operating hours check (`06:00` to `22:00`).
3. Labor shift concurrent worker check (general workers + certified forklift + certified hazmat).
4. Physical dock door filtering by capability (direction, cold chain, hazmat).
5. **Deterministic Tie-Breaker**:
   $$\text{Selection Order} = (\text{Candidate Start Time ASC}, \text{Dock ID ASC}, \text{Yard Slot ID ASC})$$

Structured rejection codes are returned upon constraint failure: `ERR_OUTSIDE_OPERATING_HOURS`, `ERR_INCOMPATIBLE_HAZMAT`, `ERR_INCOMPATIBLE_COLD_CHAIN`, `ERR_DOCK_OCCUPIED`, `ERR_LABOR_UNAVAILABLE`.

---

## 4. Lifecycle & Event Sourcing Model

Appointments transition across a formal Finite State Machine (FSM):
$$\text{Requested} \longrightarrow \text{Allocated} \longrightarrow \text{Arrived} \longrightarrow \text{Checked In} \longrightarrow \text{In Progress} \longrightarrow \text{Completed}$$
*(Exception branches: Rejected, Cancelled, No-Show, Rescheduled)*

- **Append-Only Ledger**: Every transition is persisted as an immutable `CheckInEvent` record.
- **Monotonic Sequencing**: Each event increments sequence counter ($1, 2, 3\dots$).
- **Projection Replay**: The `appointments` table is a materialized view that can be completely reconstructed by replaying the event journal.

---

## 5. The 7 Required Anomaly Scenarios

Pristine baseline data is generated first. Controlled mutations are injected through an explicit scenario layer:

| Scenario ID | Name | Injected Mutation | Expected Validator Response |
| :--- | :--- | :--- | :--- |
| **`SCEN-01`** | Overlapping Appointments | Forces 2 appointments to occupy the same dock over overlapping intervals. | Flags collision on dock (`VAL-CAP-001`). |
| **`SCEN-02`** | Incompatible Dock Assignment | Assigns a HAZMAT shipment to a non-certified dock. | Flags hazmat dock incompatibility (`VAL-COMP-002`). |
| **`SCEN-03`** | Pre-Date Check-In | Driver attempts gate check-in 24 hours prior to scheduled calendar date. | Flags pre-date check-in violation (`VAL-HOURS-001`). |
| **`SCEN-04`** | Labor Unavailable During Service | Sets forklift operator headcount to 0 during an active service window. | Flags qualified labor deficit (`VAL-LAB-001`). |
| **`SCEN-05`** | Unrecorded No-Show | Allocated vehicle never arrives; zero arrival events emitted past grace window. | Flags detectable unrecorded absence (`VAL-FSM-001`). |
| **`SCEN-06`** | Early Vehicle Arrival | Vehicle arrives 180 minutes prior to scheduled start; staged in yard slot. | Verifies yard queue hold without dock contention. |
| **`SCEN-07`** | Peak-Hour Congestion | Excess demand during peak dispatch hours triggers graceful capacity rejections. | Verifies structured rejection logging. |

### Zero Data Leakage Guarantee:
Ground-truth labels are written exclusively to `data/ground_truth/ground_truth.csv` and `ground_truth.json`. Normal operational exports and runtime scheduling routines have zero dependencies on ground-truth schemas.

---

## 6. Installation & Local Execution

### Prerequisites
- Python 3.12+ (standard CPython)
- SQLite 3 (bundled in Python standard library)

### Quickstart Setup
```bash
# 1. Clone the repository
git clone https://github.com/your-username/yottaflex-logistics.git
cd yottaflex-logistics

# 2. Create virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install pinned dependencies in editable mode
pip install -e ".[dev]"

# 4. Copy environment configuration
cp .env.example .env
```

---

## 7. Command Line Interface (CLI)

The Typer CLI exposes all core workflows:

```bash
# Initialize database tables and folders
logistics init

# Generate the Starter Profile (2 facilities, 20 docks, 1,000 appointments)
logistics generate-starter

# Generate the Full Profile (10 facilities, 100 docks, 20,000 appointments, 60 days)
logistics generate-full

# Run the 19 automated rule validators
logistics validate --anomaly-aware

# Calculate and export operational evaluation metrics
logistics evaluate

# Run double-run bitwise reproducibility verification
logistics reproduce --profile STARTER

# Launch the FastAPI REST server
logistics serve --host 127.0.0.1 --port 8000
```

---

## 8. REST API Documentation

When running `logistics serve`, interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

### Core Endpoints:
- `GET /health`: System health and version.
- `POST /appointments`: Tender a new appointment request.
- `GET /appointments/{id}`: Inspect current appointment state projection.
- `POST /appointments/{id}/allocate`: Evaluate and allocate appointment against constraints.
- `GET /appointments/{id}/events`: Retrieve append-only chronological audit timeline.
- `GET /exceptions`: Inspect operational exception log and ground-truth metadata.
- `GET /metrics`: Retrieve live throughput, utilization, and service-level KPIs.

---

## 9. Test Suite & Verification Results

The automated test suite contains **47 test cases** across unit, integration, validation, and reproducibility modules:

```bash
# Execute full test suite
pytest -v
```

### Observed Verification Results:
- **Unit Tests (`tests/unit/`)**:
  - Deterministic identifier generation & zero-padding bounds: **PASSED**
  - Service duration formula (`BR-DUR-001`): **PASSED**
  - Master data distributions & referential integrity: **PASSED**
  - Transaction generation invariants: **PASSED**
  - Scheduling engine multi-resource fit & tie-breaking: **PASSED**
  - Event store FSM transitions & replay projections: **PASSED**
  - The 7 anomaly scenario mutations: **PASSED**
- **Integration Tests (`tests/integration/`)**:
  - SQLite foreign key and CheckConstraint enforcement: **PASSED**
  - End-to-end appointment allocation & persistence: **PASSED**
  - FastAPI endpoints & Typer CLI commands: **PASSED**
  - Full pipeline execution & report generation: **PASSED**
- **Validation Tests (`tests/validation/`)**:
  - Baseline dataset produces 0 unexpected violations: **PASSED**
  - Anomaly-aware validation detects all injected scenarios: **PASSED**
- **Reproducibility Tests (`tests/reproducibility/`)**:
  - Independent double-runs with identical seed produce bitwise identical checksums: **PASSED**
  - Runs with different seeds produce differing checksums: **PASSED**

---

## 10. Reproducibility & Source Manifest

All exported datasets include an authoritative source manifest [`exports/source_manifest.json`](file:///c:/Users/Administrator/Yottaflex.ai/exports/source_manifest.json) recording:
- Dataset Profile & Seed (`20261022`)
- Generator and Schema Versions
- Table row counts
- Canonical SHA-256 checksums for every CSV, JSON, SQL, and report artifact.

Detailed comparison tables and metric stability proofs are documented in [`docs/reproducibility_report.md`](file:///c:/Users/Administrator/Yottaflex.ai/docs/reproducibility_report.md).

---

## 11. Reviewer Demonstration Guide

To demonstrate the platform to a reviewer in under 3 minutes:

1. **Verify Test Suite**:
   ```bash
   pytest -v
   ```
   *Expected Outcome*: 47 tests pass in ~4 seconds.

2. **Generate Starter Dataset & Export Artifacts**:
   ```bash
   logistics generate-starter
   ```
   *Expected Outcome*: Generates 2 facilities, 20 docks, 1,000 appointments, ~6,000 events, exports CSV/JSON/SQL, runs validation, and outputs source manifest in < 5 seconds.

3. **Verify Dual-Mode Validation**:
   ```bash
   logistics validate --anomaly-aware
   ```
   *Expected Outcome*: Final status `PASSED`, all injected scenarios detected with 0 unexpected errors.

4. **Run Bitwise Reproducibility Verification**:
   ```bash
   logistics reproduce --profile STARTER
   ```
   *Expected Outcome*: Generates [`docs/reproducibility_report.md`](file:///c:/Users/Administrator/Yottaflex.ai/docs/reproducibility_report.md) proving 100% bitwise matching SHA-256 hashes across runs.

5. **Start API and Inspect Docs**:
   ```bash
   logistics serve
   ```
   Open `http://127.0.0.1:8000/docs` in your browser to inspect and interact with the endpoints.

---

## 12. Public Data Guidance & Lawful Provenance

1. **Pure Synthetic Generation**:
   All entities (facilities, docks, carriers, vehicles, shipments, appointments, events, and exceptions) are 100% synthetically generated via deterministic algorithms rooted in PRNG seed `20261022`.
2. **Zero PII & Confidential Data**:
   No external personal data, proprietary freight logs, carrier accounts, or access controls were bypassed or redistributed.
3. **Regulatory & Industry Inspiration**:
   Public standards (NMFTA SCAC conventions, US DOT 49 CFR Hazmat categories, and ISO 8601 UTC timestamping) were cited purely for schema architecture and realistic modeling inspiration.

---

## 13. GitHub Submission & Verification Checklist

- [x] **Complete Relational Data Model**: 14 tables with foreign keys and check constraints.
- [x] **Deterministic Allocation Engine**: Multi-resource constraint checks with $[s, e)$ interval logic.
- [x] **Event Sourcing & Lifecycle Simulation**: Append-only event store with projection replay.
- [x] **Edge Case & Anomaly Handling**: 7 operational exception scenarios with isolated ground truth.
- [x] **Zero Feature Leakage**: Ground truth separated into `data/ground_truth/`.
- [x] **Automated Validation**: 19 rule validators with dual-mode reporting.
- [x] **Canonical Exports**: CSV, JSON, SQL DDL, SQL Seed, and source manifest with SHA-256 digests.
- [x] **Bitwise Reproducibility**: 100% matching checksums across independent runs.
- [x] **Automated Test Suite**: 47 unit, integration, validation, and reproducibility tests passing.
- [x] **Comprehensive Documentation**: Complete `docs/` suite, `PROMPT_HISTORY.md`, and `README.md`.

