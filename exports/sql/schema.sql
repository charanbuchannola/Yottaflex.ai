-- YottaFlex AI Synthetic Logistics Database Schema DDL

CREATE TABLE carriers (
	carrier_id VARCHAR(16) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	scac_code VARCHAR(4) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (carrier_id), 
	UNIQUE (name), 
	UNIQUE (scac_code)
)

;

CREATE TABLE facilities (
	facility_id VARCHAR(16) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	timezone VARCHAR(64) NOT NULL, 
	operating_start_hour INTEGER NOT NULL, 
	operating_end_hour INTEGER NOT NULL, 
	total_yard_slots INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (facility_id), 
	CONSTRAINT check_op_hours CHECK (operating_start_hour >= 0 AND operating_start_hour < operating_end_hour), 
	CONSTRAINT check_op_end_hour CHECK (operating_end_hour <= 24), 
	CONSTRAINT check_yard_slots_non_negative CHECK (total_yard_slots >= 0), 
	UNIQUE (name)
)

;

CREATE TABLE handling_requirements (
	requirement_id VARCHAR(16) NOT NULL, 
	code VARCHAR(32) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	PRIMARY KEY (requirement_id), 
	CONSTRAINT check_req_code CHECK (code IN ('REEFER', 'HAZMAT', 'FRAGILE', 'LIFTGATE', 'OVERSIZED')), 
	UNIQUE (code)
)

;

CREATE TABLE shipments (
	shipment_id VARCHAR(32) NOT NULL, 
	tracking_number VARCHAR(64) NOT NULL, 
	shipment_type VARCHAR(16) NOT NULL, 
	pallet_count INTEGER NOT NULL, 
	weight_kg FLOAT NOT NULL, 
	ready_time DATETIME NOT NULL, 
	due_time DATETIME NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (shipment_id), 
	CONSTRAINT check_pallet_count_range CHECK (pallet_count >= 1 AND pallet_count <= 60), 
	CONSTRAINT check_weight_positive CHECK (weight_kg > 0), 
	CONSTRAINT check_shipment_time_order CHECK (due_time > ready_time), 
	CONSTRAINT check_shipment_type CHECK (shipment_type IN ('INBOUND', 'OUTBOUND')), 
	CONSTRAINT check_shipment_status CHECK (status IN ('CREATED', 'ASSIGNED', 'IN_TRANSIT', 'DELIVERED')), 
	UNIQUE (tracking_number)
)

;

CREATE TABLE docks (
	dock_id VARCHAR(32) NOT NULL, 
	facility_id VARCHAR(16) NOT NULL, 
	dock_number VARCHAR(16) NOT NULL, 
	dock_type VARCHAR(32) NOT NULL, 
	has_dock_leveler BOOLEAN NOT NULL, 
	has_cold_chain BOOLEAN NOT NULL, 
	has_hazmat_permit BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (dock_id), 
	CONSTRAINT uq_facility_dock_number UNIQUE (facility_id, dock_number), 
	CONSTRAINT check_dock_type CHECK (dock_type IN ('INBOUND', 'OUTBOUND', 'CROSS_DOCK')), 
	FOREIGN KEY(facility_id) REFERENCES facilities (facility_id) ON DELETE CASCADE
)

;

CREATE TABLE labor_shifts (
	shift_id VARCHAR(32) NOT NULL, 
	facility_id VARCHAR(16) NOT NULL, 
	shift_date DATE NOT NULL, 
	start_time DATETIME NOT NULL, 
	end_time DATETIME NOT NULL, 
	total_workers INTEGER NOT NULL, 
	forklift_certified_workers INTEGER NOT NULL, 
	hazmat_certified_workers INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (shift_id), 
	CONSTRAINT check_shift_time_order CHECK (end_time > start_time), 
	CONSTRAINT check_total_workers_positive CHECK (total_workers > 0), 
	CONSTRAINT check_forklift_workers_range CHECK (forklift_certified_workers >= 0 AND forklift_certified_workers <= total_workers), 
	CONSTRAINT check_hazmat_workers_range CHECK (hazmat_certified_workers >= 0 AND hazmat_certified_workers <= total_workers), 
	FOREIGN KEY(facility_id) REFERENCES facilities (facility_id) ON DELETE CASCADE
)

;

CREATE TABLE shipment_handling_requirements (
	shipment_id VARCHAR(32) NOT NULL, 
	requirement_id VARCHAR(16) NOT NULL, 
	PRIMARY KEY (shipment_id, requirement_id), 
	FOREIGN KEY(shipment_id) REFERENCES shipments (shipment_id) ON DELETE CASCADE, 
	FOREIGN KEY(requirement_id) REFERENCES handling_requirements (requirement_id) ON DELETE CASCADE
)

;

CREATE TABLE vehicles (
	vehicle_id VARCHAR(16) NOT NULL, 
	carrier_id VARCHAR(16) NOT NULL, 
	vehicle_type VARCHAR(32) NOT NULL, 
	license_plate VARCHAR(32) NOT NULL, 
	has_liftgate BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (vehicle_id), 
	CONSTRAINT check_vehicle_type CHECK (vehicle_type IN ('DRY_VAN', 'REEFER', 'FLATBED', 'BOX_TRUCK')), 
	FOREIGN KEY(carrier_id) REFERENCES carriers (carrier_id) ON DELETE CASCADE, 
	UNIQUE (license_plate)
)

;

CREATE TABLE yard_slots (
	yard_slot_id VARCHAR(32) NOT NULL, 
	facility_id VARCHAR(16) NOT NULL, 
	slot_number VARCHAR(16) NOT NULL, 
	slot_type VARCHAR(32) NOT NULL, 
	is_occupied BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (yard_slot_id), 
	CONSTRAINT uq_facility_yard_slot UNIQUE (facility_id, slot_number), 
	CONSTRAINT check_slot_type CHECK (slot_type IN ('STANDARD', 'REEFER_PLUG', 'STAGING')), 
	FOREIGN KEY(facility_id) REFERENCES facilities (facility_id) ON DELETE CASCADE
)

;

CREATE TABLE appointments (
	appointment_id VARCHAR(32) NOT NULL, 
	facility_id VARCHAR(16) NOT NULL, 
	carrier_id VARCHAR(16) NOT NULL, 
	vehicle_id VARCHAR(16) NOT NULL, 
	dock_id VARCHAR(32), 
	yard_slot_id VARCHAR(32), 
	appointment_type VARCHAR(16) NOT NULL, 
	requested_start DATETIME NOT NULL, 
	requested_end DATETIME NOT NULL, 
	scheduled_start DATETIME, 
	scheduled_end DATETIME, 
	duration_minutes INTEGER NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	version INTEGER NOT NULL, 
	updated_at DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (appointment_id), 
	CONSTRAINT check_requested_window CHECK (requested_end > requested_start), 
	CONSTRAINT check_duration_range CHECK (duration_minutes >= 30 AND duration_minutes <= 240), 
	CONSTRAINT check_appointment_type CHECK (appointment_type IN ('INBOUND', 'OUTBOUND')), 
	CONSTRAINT check_appointment_status CHECK (status IN ('REQUESTED', 'ALLOCATED', 'REJECTED', 'ARRIVED', 'CHECKED_IN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'NO_SHOW')), 
	FOREIGN KEY(facility_id) REFERENCES facilities (facility_id) ON DELETE RESTRICT, 
	FOREIGN KEY(carrier_id) REFERENCES carriers (carrier_id) ON DELETE RESTRICT, 
	FOREIGN KEY(vehicle_id) REFERENCES vehicles (vehicle_id) ON DELETE RESTRICT, 
	FOREIGN KEY(dock_id) REFERENCES docks (dock_id) ON DELETE SET NULL, 
	FOREIGN KEY(yard_slot_id) REFERENCES yard_slots (yard_slot_id) ON DELETE SET NULL
)

;

CREATE TABLE dock_handling_capabilities (
	dock_id VARCHAR(32) NOT NULL, 
	requirement_id VARCHAR(16) NOT NULL, 
	PRIMARY KEY (dock_id, requirement_id), 
	FOREIGN KEY(dock_id) REFERENCES docks (dock_id) ON DELETE CASCADE, 
	FOREIGN KEY(requirement_id) REFERENCES handling_requirements (requirement_id) ON DELETE CASCADE
)

;

CREATE TABLE allocation_decisions (
	decision_id VARCHAR(48) NOT NULL, 
	appointment_id VARCHAR(32) NOT NULL, 
	facility_id VARCHAR(16) NOT NULL, 
	dock_id VARCHAR(32), 
	yard_slot_id VARCHAR(32), 
	evaluated_at DATETIME NOT NULL, 
	decision_status VARCHAR(16) NOT NULL, 
	rule_evaluated VARCHAR(32) NOT NULL, 
	rejection_reason VARCHAR(64), 
	context_metadata_json TEXT NOT NULL, 
	PRIMARY KEY (decision_id), 
	CONSTRAINT check_decision_status CHECK (decision_status IN ('ALLOCATED', 'REJECTED')), 
	FOREIGN KEY(appointment_id) REFERENCES appointments (appointment_id) ON DELETE CASCADE, 
	FOREIGN KEY(facility_id) REFERENCES facilities (facility_id) ON DELETE RESTRICT, 
	FOREIGN KEY(dock_id) REFERENCES docks (dock_id) ON DELETE SET NULL, 
	FOREIGN KEY(yard_slot_id) REFERENCES yard_slots (yard_slot_id) ON DELETE SET NULL
)

;

CREATE TABLE appointment_shipments (
	appointment_id VARCHAR(32) NOT NULL, 
	shipment_id VARCHAR(32) NOT NULL, 
	PRIMARY KEY (appointment_id, shipment_id), 
	FOREIGN KEY(appointment_id) REFERENCES appointments (appointment_id) ON DELETE CASCADE, 
	FOREIGN KEY(shipment_id) REFERENCES shipments (shipment_id) ON DELETE CASCADE
)

;

CREATE TABLE check_in_events (
	event_id VARCHAR(64) NOT NULL, 
	appointment_id VARCHAR(32) NOT NULL, 
	sequence_number INTEGER NOT NULL, 
	event_type VARCHAR(32) NOT NULL, 
	occurrence_time DATETIME NOT NULL, 
	recorded_time DATETIME NOT NULL, 
	actor VARCHAR(32) NOT NULL, 
	payload_json TEXT NOT NULL, 
	PRIMARY KEY (event_id), 
	CONSTRAINT uq_appointment_event_sequence UNIQUE (appointment_id, sequence_number), 
	CONSTRAINT check_positive_event_sequence CHECK (sequence_number >= 1), 
	CONSTRAINT check_event_type CHECK (event_type IN ('REQUESTED', 'APPROVED', 'ALLOCATED', 'ARRIVED', 'CHECKED_IN', 'LOADING_STARTED', 'UNLOADING_STARTED', 'LOADING_COMPLETED', 'UNLOADING_COMPLETED', 'DEPARTED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'NO_SHOW')), 
	FOREIGN KEY(appointment_id) REFERENCES appointments (appointment_id) ON DELETE CASCADE
)

;

CREATE TABLE operational_exceptions (
	exception_id VARCHAR(32) NOT NULL, 
	appointment_id VARCHAR(32) NOT NULL, 
	scenario_id VARCHAR(32) NOT NULL, 
	issue_type VARCHAR(64) NOT NULL, 
	root_cause TEXT NOT NULL, 
	expected_outcome VARCHAR(64) NOT NULL, 
	ground_truth_label VARCHAR(32) NOT NULL, 
	is_injected_anomaly BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (exception_id), 
	CONSTRAINT check_exception_issue_type CHECK (issue_type IN ('OVERLAPPING_APPOINTMENTS', 'INCOMPATIBLE_DOCK', 'PRE_DATE_CHECKIN', 'LABOR_UNAVAILABLE', 'UNRECORDED_NO_SHOW', 'EARLY_ARRIVAL', 'PEAK_CONGESTION')), 
	FOREIGN KEY(appointment_id) REFERENCES appointments (appointment_id) ON DELETE CASCADE
)

;
