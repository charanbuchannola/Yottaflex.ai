# Relational Data Dictionary

---

## 1. Table: `facilities`
Authoritative master data defining physical logistics warehouses and distribution hubs.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `facility_id` | Business identifier | `VARCHAR(16)` | Required | Format: `^FAC-\d{3}$` | Any matching regex | Primary Key | None | None | Source |
| `name` | Human-readable facility name | `VARCHAR(128)` | Required | Non-empty string | Any | Unique | None | None | Source |
| `timezone` | Local operational timezone | `VARCHAR(64)` | Required | Valid IANA timezone | E.g. `UTC`, `America/Chicago` | Non-unique | None | None | Source |
| `operating_start_hour` | Daily gate opening hour | `INTEGER` | Required | $0 \le x \le 23$ | `0` to `23` | Non-unique | Hours (24h) | None | Source |
| `operating_end_hour` | Daily gate closing hour | `INTEGER` | Required | $\text{Start} < x \le 24$ | `1` to `24` | Non-unique | Hours (24h) | None | Source |
| `total_yard_slots` | Total staging spaces in yard | `INTEGER` | Required | $x \ge 0$ | Positive integers | Non-unique | Count | None | Source |
| `is_active` | Operational status flag | `BOOLEAN` | Required | Boolean | `true`, `false` | Non-unique | Flag | None | Source |
| `created_at` | Record creation timestamp | `TIMESTAMP` | Required | Valid UTC ISO-8601 | Datetime | Non-unique | UTC | None | Audit |

---

## 2. Table: `docks`
Physical dock doors at a facility where trucks dock for loading/unloading.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `dock_id` | Business identifier | `VARCHAR(32)` | Required | Format: `^DOCK-FAC-\d{3}-\d{3}$` | Matching regex | Primary Key | None | None | Source |
| `facility_id` | Parent facility reference | `VARCHAR(16)` | Required | Existing facility | Valid `facility_id` | Non-unique | None | `facilities.facility_id` | Source |
| `dock_number` | Visible bay door number | `VARCHAR(16)` | Required | Non-empty | E.g. `"Bay-01"` | Unique per facility | None | None | Source |
| `dock_type` | Operational freight capability | `VARCHAR(32)` | Required | Enumeration | `INBOUND`, `OUTBOUND`, `CROSS_DOCK` | Non-unique | None | None | Source |
| `has_dock_leveler` | Hydraulic leveler installed | `BOOLEAN` | Required | Boolean | `true`, `false` | Non-unique | Flag | None | Source |
| `has_cold_chain` | Refrigerated seal and cooling | `BOOLEAN` | Required | Boolean | `true`, `false` | Non-unique | Flag | None | Source |
| `has_hazmat_permit` | Hazmat spill protection permit | `BOOLEAN` | Required | Boolean | `true`, `false` | Non-unique | Flag | None | Source |
| `is_active` | Availability flag | `BOOLEAN` | Required | Boolean | `true`, `false` | Non-unique | Flag | None | Source |
| `created_at` | Record creation timestamp | `TIMESTAMP` | Required | Valid UTC ISO-8601 | Datetime | Non-unique | UTC | None | Audit |

---

## 3. Table: `yard_slots`
Designated trailer parking/staging spaces in the facility yard.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `yard_slot_id` | Business identifier | `VARCHAR(32)` | Required | Format: `^YARD-FAC-\d{3}-\d{3}$` | Matching regex | Primary Key | None | None | Source |
| `facility_id` | Parent facility reference | `VARCHAR(16)` | Required | Existing facility | Valid `facility_id` | Non-unique | None | `facilities.facility_id` | Source |
| `slot_number` | Staged slot identifier | `VARCHAR(16)` | Required | Non-empty | E.g. `"Y-01"` | Unique per facility | None | None | Source |
| `slot_type` | Electrical/staging type | `VARCHAR(32)` | Required | Enumeration | `STANDARD`, `REEFER_PLUG`, `STAGING` | Non-unique | None | None | Source |
| `is_occupied` | Current physical presence | `BOOLEAN` | Required | Boolean | `true`, `false` | Non-unique | Flag | None | Derived |
| `created_at` | Record creation timestamp | `TIMESTAMP` | Required | Valid UTC ISO-8601 | Datetime | Non-unique | UTC | None | Audit |

---

## 4. Table: `carriers`
Logistics and freight transportation providers.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `carrier_id` | Business identifier | `VARCHAR(16)` | Required | Format: `^CARR-\d{3}$` | Matching regex | Primary Key | None | None | Source |
| `name` | Legal carrier name | `VARCHAR(128)` | Required | Non-empty | Any | Unique | None | None | Source |
| `scac_code` | Standard Carrier Alpha Code | `VARCHAR(4)` | Required | 2-4 uppercase characters | E.g. `"YOTF"` | Unique | None | None | Source |
| `is_active` | Active vendor status | `BOOLEAN` | Required | Boolean | `true`, `false` | Non-unique | Flag | None | Source |
| `created_at` | Record creation timestamp | `TIMESTAMP` | Required | Valid UTC ISO-8601 | Datetime | Non-unique | UTC | None | Audit |

---

## 5. Table: `vehicles`
Tractors, trailers, and box trucks operated by carriers.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `vehicle_id` | Business identifier | `VARCHAR(16)` | Required | Format: `^VEH-\d{4}$` | Matching regex | Primary Key | None | None | Source |
| `carrier_id` | Operating carrier reference | `VARCHAR(16)` | Required | Existing carrier | Valid `carrier_id` | Non-unique | None | `carriers.carrier_id` | Source |
| `vehicle_type` | Equipment classification | `VARCHAR(32)` | Required | Enumeration | `DRY_VAN`, `REEFER`, `FLATBED`, `BOX_TRUCK` | Non-unique | None | None | Source |
| `license_plate` | Registration plate | `VARCHAR(32)` | Required | Non-empty | Alphanumeric | Unique | None | None | Source |
| `has_liftgate` | Rear hydraulic lift installed | `BOOLEAN` | Required | Boolean | `true`, `false` | Non-unique | Flag | None | Source |
| `created_at` | Record creation timestamp | `TIMESTAMP` | Required | Valid UTC ISO-8601 | Datetime | Non-unique | UTC | None | Audit |

---

## 6. Table: `labor_shifts`
Scheduled warehouse personnel shifts providing unloading, loading, and material handling capacity.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shift_id` | Business identifier | `VARCHAR(32)` | Required | Format: `^SHIFT-FAC-\d{3}-\d{8}-\d{2}$` | Matching regex | Primary Key | None | None | Source |
| `facility_id` | Parent facility reference | `VARCHAR(16)` | Required | Existing facility | Valid `facility_id` | Non-unique | None | `facilities.facility_id` | Source |
| `shift_date` | Calendar date of shift | `DATE` | Required | Valid calendar date | `YYYY-MM-DD` | Non-unique | Date | None | Source |
| `start_time` | Shift commence timestamp | `TIMESTAMP` | Required | $\text{start} < \text{end}$ | Datetime | Non-unique | UTC | None | Source |
| `end_time` | Shift conclude timestamp | `TIMESTAMP` | Required | $\text{end} > \text{start}$ | Datetime | Non-unique | UTC | None | Source |
| `total_workers` | Total staff rostered | `INTEGER` | Required | $x > 0$ | $\ge 1$ | Non-unique | Workers | None | Source |
| `forklift_certified_workers`| Forklift operator count | `INTEGER` | Required | $0 \le x \le \text{total}$ | $\le \text{total\_workers}$ | Non-unique | Workers | None | Source |
| `hazmat_certified_workers` | Hazmat certified count | `INTEGER` | Required | $0 \le x \le \text{total}$ | $\le \text{total\_workers}$ | Non-unique | Workers | None | Source |

---

## 7. Table: `handling_requirements`
Master catalog of specialized handling certifications and requirements.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `requirement_id` | Business identifier | `VARCHAR(16)` | Required | Format: `^REQ-\d{3}$` | Matching regex | Primary Key | None | None | Source |
| `code` | Machine-readable code | `VARCHAR(32)` | Required | Uppercase enumeration | `REEFER`, `HAZMAT`, `FRAGILE`, `LIFTGATE`, `OVERSIZED` | Unique | None | None | Source |
| `description` | Standard SOP description | `VARCHAR(255)` | Required | Non-empty | String | Non-unique | None | None | Source |

---

## 8. Table: `shipments`
Physical cargo lots tendered for inbound intake or outbound dispatch.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shipment_id` | Business identifier | `VARCHAR(32)` | Required | Format: `^SHP-\d{4}-\d{6}$` | Matching regex | Primary Key | None | None | Source |
| `tracking_number` | Carrier/shipper BOL tracking | `VARCHAR(64)` | Required | Format: `^TRK-[A-Z0-9]+$` | Alphanumeric | Unique | None | None | Source |
| `shipment_type` | Direction of movement | `VARCHAR(16)` | Required | Enumeration | `INBOUND`, `OUTBOUND` | Non-unique | None | None | Source |
| `pallet_count` | Number of pallet positions | `INTEGER` | Required | $1 \le x \le 60$ | Integer | Non-unique | Pallets | None | Source |
| `weight_kg` | Gross physical weight | `FLOAT` | Required | $x > 0$ | Floating point | Non-unique | Kilograms | None | Source |
| `ready_time` | Earliest availability | `TIMESTAMP` | Required | Valid UTC datetime | Datetime | Non-unique | UTC | None | Source |
| `due_time` | Required delivery deadline | `TIMESTAMP` | Required | $\text{due} > \text{ready}$ | Datetime | Non-unique | UTC | None | Source |
| `status` | Cargo transit state | `VARCHAR(32)` | Required | Enumeration | `CREATED`, `ASSIGNED`, `IN_TRANSIT`, `DELIVERED` | Non-unique | None | None | Derived |

---

## 9. Table: `shipment_handling_requirements` (Bridge Table)
Many-to-many relationship mapping shipments to required handling certifications.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shipment_id` | Shipment reference | `VARCHAR(32)` | Required | Existing shipment | Valid ID | Composite PK | `shipments.shipment_id` | Source |
| `requirement_id`| Requirement reference | `VARCHAR(16)` | Required | Existing requirement | Valid ID | Composite PK | `handling_requirements.requirement_id` | Source |

---

## 10. Table: `appointments`
Core scheduling aggregate and current-state projection.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `appointment_id` | Business identifier | `VARCHAR(32)` | Required | Format: `^APPT-\d{4}-\d{6}$` | Matching regex | Primary Key | None | None | Source |
| `facility_id` | Scheduled destination | `VARCHAR(16)` | Required | Existing facility | Valid ID | Non-unique | None | `facilities.facility_id` | Source |
| `carrier_id` | Contracted carrier | `VARCHAR(16)` | Required | Existing carrier | Valid ID | Non-unique | None | `carriers.carrier_id` | Source |
| `vehicle_id` | Assigned vehicle | `VARCHAR(16)` | Required | Existing vehicle | Valid ID | Non-unique | None | `vehicles.vehicle_id` | Source |
| `dock_id` | Assigned dock door | `VARCHAR(32)` | Optional | Existing dock | Valid ID or NULL | Non-unique | None | `docks.dock_id` | Derived |
| `yard_slot_id` | Assigned yard slot | `VARCHAR(32)` | Optional | Existing yard slot | Valid ID or NULL | Non-unique | None | `yard_slots.yard_slot_id` | Derived |
| `appointment_type` | Direction of appointment | `VARCHAR(16)` | Required | Enumeration | `INBOUND`, `OUTBOUND` | Non-unique | None | None | Source |
| `requested_start` | Requested window start | `TIMESTAMP` | Required | $\text{start} < \text{end}$ | Datetime | Non-unique | UTC | None | Source |
| `requested_end` | Requested window end | `TIMESTAMP` | Required | $\text{end} > \text{start}$ | Datetime | Non-unique | UTC | None | Source |
| `scheduled_start` | Allocated start time | `TIMESTAMP` | Optional | $\text{start} < \text{end}$ | Datetime or NULL | Non-unique | UTC | None | Derived |
| `scheduled_end` | Allocated end time | `TIMESTAMP` | Optional | $\text{end} > \text{start}$ | Datetime or NULL | Non-unique | UTC | None | Derived |
| `duration_minutes` | Calculated service duration | `INTEGER` | Required | Formula BR-DUR-001 | $30 \le x \le 240$ | Non-unique | Minutes | None | Derived |
| `status` | Lifecycle projection state | `VARCHAR(32)` | Required | Enumeration | `REQUESTED`, `ALLOCATED`, `REJECTED`, `ARRIVED`, `CHECKED_IN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `NO_SHOW` | Non-unique | None | None | Derived |
| `version` | Optimistic locking counter | `INTEGER` | Required | Increments on update | $\ge 1$ | Non-unique | None | None | Audit |
| `created_at` | Record creation timestamp | `TIMESTAMP` | Required | Valid UTC ISO-8601 | Datetime | Non-unique | UTC | None | Audit |
| `updated_at` | Record update timestamp | `TIMESTAMP` | Required | Valid UTC ISO-8601 | Datetime | Non-unique | UTC | None | Audit |

---

## 11. Table: `appointment_shipments` (Bridge Table)
Links shipments to appointments (supports multi-shipment consolidated trailers).

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `appointment_id`| Appointment reference | `VARCHAR(32)` | Required | Existing appointment | Valid ID | Composite PK | `appointments.appointment_id` | Source |
| `shipment_id` | Shipment reference | `VARCHAR(32)` | Required | Existing shipment | Valid ID | Composite PK | `shipments.shipment_id` | Source |

---

## 12. Table: `allocation_decisions`
Auditable record of every evaluation produced by the scheduling engine.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `decision_id` | Business identifier | `VARCHAR(48)` | Required | Format: `^DEC-APPT-\d{4}-\d{6}-\d{2}$` | Matching regex | Primary Key | None | None | Source |
| `appointment_id` | Subject appointment | `VARCHAR(32)` | Required | Existing appointment | Valid ID | Non-unique | None | `appointments.appointment_id` | Source |
| `facility_id` | Facility evaluated | `VARCHAR(16)` | Required | Existing facility | Valid ID | Non-unique | None | `facilities.facility_id` | Source |
| `dock_id` | Selected dock door | `VARCHAR(32)` | Optional | Existing dock | Valid ID or NULL | Non-unique | None | `docks.dock_id` | Derived |
| `yard_slot_id` | Selected yard slot | `VARCHAR(32)` | Optional | Existing yard slot | Valid ID or NULL | Non-unique | None | `yard_slots.yard_slot_id` | Derived |
| `evaluated_at` | Simulation timestamp | `TIMESTAMP` | Required | Valid UTC datetime | Datetime | Non-unique | UTC | None | Audit |
| `decision_status`| Final allocation outcome | `VARCHAR(16)` | Required | Enumeration | `ALLOCATED`, `REJECTED` | Non-unique | None | None | Derived |
| `rule_evaluated` | Primary rule governing | `VARCHAR(32)` | Required | Catalogue ID | E.g. `BR-CAP-001` | Non-unique | None | None | Derived |
| `rejection_reason`| Structured reason code | `VARCHAR(64)` | Optional | Standard error enum | E.g. `ERR_NO_DOCK_CAPACITY` | Non-unique | None | None | Derived |
| `context_metadata_json`| Full snapshot payload | `TEXT` | Required | Valid JSON string | JSON document | Non-unique | None | None | Audit |

---

## 13. Table: `check_in_events`
Append-only operational event ledger.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | Business identifier | `VARCHAR(64)` | Required | Format: `^CHECK-APPT-\d{4}-\d{6}-\d{2}$` | Matching regex | Primary Key | None | None | Source |
| `appointment_id` | Root appointment | `VARCHAR(32)` | Required | Existing appointment | Valid ID | Non-unique | None | `appointments.appointment_id` | Source |
| `sequence_number`| Monotonic sequence | `INTEGER` | Required | $x \ge 1$ | $1, 2, 3\dots$ | Composite Unique | None | None | Source |
| `event_type` | Lifecycle event | `VARCHAR(32)` | Required | Valid event enum | `REQUESTED`, `ALLOCATED`, `ARRIVED`, `CHECKED_IN`, etc. | Non-unique | None | None | Source |
| `occurrence_time`| Real-world event time | `TIMESTAMP` | Required | Valid UTC ISO-8601 | Datetime | Non-unique | UTC | None | Source |
| `recorded_time` | Ingestion timestamp | `TIMESTAMP` | Required | $\text{recorded} \ge \text{occurred}$ | Datetime | Non-unique | UTC | None | Audit |
| `actor` | Operational actor | `VARCHAR(32)` | Required | Enumeration | `SYSTEM`, `CARRIER`, `GATE_CLERK`, `WAREHOUSE_OP` | Non-unique | None | None | Source |
| `payload_json` | Event context | `TEXT` | Required | Valid JSON string | JSON document | Non-unique | None | None | Source |

---

## 14. Table: `operational_exceptions` (Ground-Truth & Anomalies)
Segregated repository of injected operational exceptions and ground-truth labels.

| Field Name | Description | Data Type | Req/Opt | Validation Rule | Allowed Values | Uniqueness | Unit | Foreign Key | Origin Type |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `exception_id` | Business identifier | `VARCHAR(32)` | Required | Format: `^EXC-\d{4}-\d{6}$` | Matching regex | Primary Key | None | None | Source |
| `appointment_id` | Target appointment | `VARCHAR(32)` | Required | Existing appointment | Valid ID | Non-unique | None | `appointments.appointment_id` | Source |
| `scenario_id` | Scenario identifier | `VARCHAR(32)` | Required | Format: `^SCEN-\d{2}$` | `SCEN-01` to `SCEN-07` | Non-unique | None | None | Source |
| `issue_type` | Anomaly classification | `VARCHAR(64)` | Required | Enumeration | `OVERLAPPING_APPOINTMENTS`, `INCOMPATIBLE_DOCK`, `PRE_DATE_CHECKIN`, `LABOR_UNAVAILABLE`, `UNRECORDED_NO_SHOW`, `EARLY_ARRIVAL`, `PEAK_CONGESTION` | Non-unique | None | None | Source |
| `root_cause` | Detailed explanation | `TEXT` | Required | Non-empty | String | Non-unique | None | None | Source |
| `expected_outcome`| Required engine behavior| `VARCHAR(64)` | Required | Enumeration | `REJECT`, `EXCEPTION_FLAG`, `QUEUE_WAIT`, `DETECT_ABSENCE` | Non-unique | None | None | Source |
| `ground_truth_label`| Binary evaluation label| `VARCHAR(32)` | Required | Enumeration | `ANOMALY`, `NORMAL` | Non-unique | None | None | Ground Truth |
| `is_injected_anomaly`| Synthetic injection flag| `BOOLEAN` | Required | Boolean | `true`, `false` | Non-unique | Flag | None | Ground Truth |
| `created_at` | Record creation timestamp | `TIMESTAMP` | Required | Valid UTC ISO-8601 | Datetime | Non-unique | UTC | None | Audit |
