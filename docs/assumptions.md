# Operating Assumptions, Distributions, & Identifier Specifications

---

## 1. Core Operating Assumptions

1. **Local & Cloudless Execution**:
   - The platform runs 100% locally on Python 3.12 without external database daemons, message brokers (Kafka/RabbitMQ), or cloud API keys.
   - Persistence uses SQLite 3 with WAL mode and `PRAGMA foreign_keys = ON`.
2. **Fixed Simulation Temporal Anchor**:
   - Simulation start date: **`2026-10-22T00:00:00Z`** (aligned with default seed `20261022`).
   - Timezone standard: All database timestamps are persisted as UTC ISO-8601 strings (`YYYY-MM-DDTHH:MM:SSZ`).
   - Local facility conversion uses the facility's configured timezone (default: `UTC` or `America/Chicago`).
3. **Facility & Shift Topology**:
   - Facilities operate **16 hours per day** (06:00 to 22:00 local time).
   - Labor is staffed across **two 8-hour shifts**:
     - Morning Shift: `06:00:00` to `14:00:00`.
     - Afternoon/Evening Shift: `14:00:00` to `22:00:00`.
   - Each shift has a fixed pool of general workers, certified forklift drivers, and certified hazmat handlers.
4. **Dock Specialization & Yard Capacity**:
   - Standard dock doors handle standard dry freight.
   - Reefer-equipped dock doors feature cold storage seals and temperature monitoring.
   - Hazmat-certified dock doors feature spill containment basins, specialized ventilation, and safety permits.
   - Each facility maintains a finite number of yard staging slots for early arrivals and trailer drop-and-hook.

---

## 2. Statistical Distributions for Synthetic Generation

To avoid unrealistic uniform generation, master data and transaction generators employ realistic industrial distributions parameterized by the deterministic PRNG instance (`random.Random(seed)`):

| Attribute | Statistical Distribution | Mathematical Parameters | Real-World Justification |
| :--- | :--- | :--- | :--- |
| **Direction** | Bernoulli / Categorical | $P(\text{Inbound}) = 0.60$, $P(\text{Outbound}) = 0.40$ | Distribution centers process higher raw inbound volume compared to outbound consolidated shipments. |
| **Pallet Count** | Truncated Normal / Discrete | $\mu = 22, \sigma = 8$, bounded to $[2, 54]$ | Standard 53ft dry van holds 26 to 52 standard 48x40 pallets double-stacked. |
| **Shipment Weight** | Linear with Normal Noise | $W = \text{Pallets} \times 450\,\text{kg} + \mathcal{N}(0, 50\,\text{kg})$ | Palletized freight has proportional weight with density variations. |
| **Vehicle Types** | Categorical | Dry Van: 65%, Reefer: 22%, Flatbed: 8%, Box Truck: 5% | Standard North American fleet composition. |
| **Special Handling** | Bernoulli trials | Cold Chain: 20%, Hazmat: 8%, Fragile: 12%, Oversized: 5% | Industrial cross-dock specialization rates. |
| **Arrival Punctuality** | Gaussian / Normal | $\mu = -5\,\text{min}$ (5m early), $\sigma = 20\,\text{min}$ | Truck arrivals exhibit slight early bias with a long tail of congestion-induced late arrivals. |
| **Daily Request Volume**| Bimodal Diurnal Curve | Morning Peak: 07:00-10:00, Afternoon Peak: 13:00-15:00 | Standard freight dispatch schedules avoid urban rush-hour traffic. |

---

## 3. Centralized Deterministic Identifier Specifications

All entities use centralized, zero-padded, immutable business identifiers generated strictly from deterministic counters and namespace prefixes.

| Entity Type | Format Pattern | Example Value | Counter Width | Namespace Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Facility** | `FAC-{seq:03d}` | `FAC-001` | 3 digits (1-999) | Global |
| **Dock** | `DOCK-{facility_id}-{seq:03d}` | `DOCK-FAC-001-001` | 3 digits per facility | Facility-scoped |
| **Yard Slot** | `YARD-{facility_id}-{seq:03d}` | `YARD-FAC-001-001` | 3 digits per facility | Facility-scoped |
| **Labor Shift** | `SHIFT-{facility_id}-{date}-{seq:02d}` | `SHIFT-FAC-001-20261022-01` | 2 digits per day | Facility-date-scoped |
| **Carrier** | `CARR-{seq:03d}` | `CARR-001` | 3 digits (1-999) | Global |
| **Vehicle** | `VEH-{seq:04d}` | `VEH-0001` | 4 digits (1-9999) | Global |
| **Handling Requirement**| `REQ-{seq:03d}` | `REQ-001` | 3 digits | Global |
| **Shipment** | `SHP-{year}-{seq:06d}` | `SHP-2026-000001` | 6 digits (1-999,999) | Simulation Year |
| **Appointment** | `APPT-{year}-{seq:06d}` | `APPT-2026-000001` | 6 digits (1-999,999) | Simulation Year |
| **Allocation Decision** | `DEC-{appointment_id}-{seq:02d}` | `DEC-APPT-2026-000001-01` | 2 digits | Appointment-scoped |
| **Check-in Event** | `CHECK-{appointment_id}-{seq:02d}` | `CHECK-APPT-2026-000001-01` | 2 digits | Appointment-scoped |
| **Operational Exception**| `EXC-{year}-{seq:06d}` | `EXC-2026-000001` | 6 digits | Simulation Year |

### Invariant & Integrity Rules:
1. **No Non-Deterministic Generators**: `uuid.uuid4()`, `time.time()`, and random hashes are prohibited for business ID generation.
2. **Stable Sorting**: Because identifiers are zero-padded to fixed widths, lexicographical sorting (`str` sort) is 100% equivalent to integer sequence sorting.
3. **Overflow Protection**: Counter functions validate that sequence indices do not exceed the field width, raising `IdentifierOverflowError` upon boundary exhaustion.
4. **Deterministic Reset Policy**: Sequence counters reset deterministically when entering a new namespace or when re-seeding the generator pipeline.

---

## 4. Dataset Profiles

| Parameter | Starter Profile | Full Profile |
| :--- | :--- | :--- |
| **Number of Facilities** | 2 | 10 |
| **Total Docks** | 20 (10 per facility) | 100 (10 per facility) |
| **Total Yard Slots** | 30 (15 per facility) | 200 (20 per facility) |
| **Number of Carriers** | 10 | 50 |
| **Number of Vehicles** | 40 | 300 |
| **Number of Appointments** | 1,000 | 20,000 |
| **Total Events** | ~5,000 - 8,000 | ~100,000 - 140,000 |
| **Simulation Duration** | 7 Days | 60 Days |
| **Target Local Runtime** | < 10 seconds | < 90 seconds |
| **Target Memory Footprint** | < 150 MB RSS | < 500 MB RSS |
| **Primary Intended Use** | CI/CD testing, rapid integration | Stress-testing, analytical evaluation |

---

## 5. Public Data Guidance & Lawful Provenance

1. **Pure Synthetic Generation**:
   - The entire dataset across facilities, docks, carriers, vehicles, shipments, and appointments is **100% synthetically generated** in memory.
   - Zero external private, proprietary, commercial, or personally identifiable information (PII) was scraped, accessed, or redistributed.
2. **Schema Inspiration & Public Reference Data**:
   - **Carrier SCAC Codes**: Follows the structural naming format of the National Motor Freight Traffic Association (NMFTA) 4-character alpha/alphanumeric convention.
   - **Hazardous Materials Regulations**: Classification codes (`REQ-002`) reference standard US DOT 49 CFR hazardous materials handling guidelines for warehouse safety permits.
   - **Trailer & Pallet Dimensions**: Pallet counts and freight densities reflect standard North American 53-foot dry van and refrigerated freight capacities (26 to 52 standard GMA $48 \times 40$ inch pallets).
   - **Temporal Standards**: All timestamps are formatted strictly under ISO 8601 UTC standards (`YYYY-MM-DDTHH:MM:SSZ`).

