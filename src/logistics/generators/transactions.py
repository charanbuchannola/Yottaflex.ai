"""Deterministic Transaction Data Generator for Shipments and Appointment Requests."""

from datetime import datetime, time, timedelta, timezone
import random
from typing import NamedTuple

from logistics.config import ProfileConfig
from logistics.generators.identifiers import (
    generate_appointment_id,
    generate_shipment_id,
)
from logistics.generators.master_data import MasterDataBundle
from logistics.models.appointment import Appointment, AppointmentShipment
from logistics.models.shipment import Shipment, ShipmentHandlingRequirement
from logistics.scheduler.service_duration import calculate_service_duration


class TransactionBundle(NamedTuple):
    """Container for generated transactional entities."""
    shipments: list[Shipment]
    shipment_requirements: list[ShipmentHandlingRequirement]
    appointments: list[Appointment]
    appointment_shipments: list[AppointmentShipment]


def generate_transactions(
    master: MasterDataBundle,
    config: ProfileConfig,
    seed: int,
    simulation_start: datetime,
) -> TransactionBundle:
    """Deterministically generate shipments and appointment requests."""
    rng = random.Random(seed)
    req_map = {r.code: r for r in master.handling_requirements}

    shipments: list[Shipment] = []
    shipment_requirements: list[ShipmentHandlingRequirement] = []
    appointments: list[Appointment] = []
    appointment_shipments: list[AppointmentShipment] = []

    sim_year = simulation_start.year
    start_date = simulation_start.date()

    # Pre-index vehicles by capability for fast, deterministic assignment
    reefer_vehicles = [v for v in master.vehicles if v.vehicle_type == "REEFER"]
    dry_vehicles = [v for v in master.vehicles if v.vehicle_type != "REEFER"]

    for idx in range(1, config.appointments_count + 1):
        # 1. Shipment Direction and Pallet count
        direction = "INBOUND" if rng.random() < 0.60 else "OUTBOUND"

        # Truncated normal distribution for pallets (mean 22, stdev 8, clamped [2, 54])
        raw_pallets = int(rng.gauss(22, 8))
        pallet_count = max(2, min(raw_pallets, 54))

        # Weight correlated with pallets (450kg/pallet +/- 40kg noise)
        base_weight = pallet_count * 450.0
        noise = rng.gauss(0, 40.0)
        weight_kg = round(max(100.0, base_weight + noise), 1)

        # Handling requirements selection
        req_codes: list[str] = []
        if rng.random() < 0.20 and "REEFER" in req_map:
            req_codes.append("REEFER")
        if rng.random() < 0.08 and "HAZMAT" in req_map:
            req_codes.append("HAZMAT")
        if rng.random() < 0.12 and "FRAGILE" in req_map:
            req_codes.append("FRAGILE")
        if rng.random() < 0.05 and "OVERSIZED" in req_map:
            req_codes.append("OVERSIZED")

        # 2. Timing and Calendar Placement
        day_offset = rng.randint(0, config.simulation_days - 1)
        appt_date = start_date + timedelta(days=day_offset)

        # Diurnal peak arrival hours: morning (07:00-10:00) or afternoon (13:00-15:00)
        is_peak = rng.random() < 0.65
        if is_peak:
            if rng.random() < 0.55:
                # Morning peak
                start_hour = rng.randint(7, 9)
            else:
                # Afternoon peak
                start_hour = rng.randint(13, 15)
        else:
            # Off-peak within operating hours
            start_hour = rng.randint(config.operating_start_hour, config.operating_end_hour - 3)

        start_minute = rng.choice([0, 15, 30, 45])
        req_start = datetime.combine(appt_date, time(start_hour, start_minute), tzinfo=timezone.utc)

        # Requested window width between 2 and 4 hours
        window_hours = rng.randint(2, 4)
        req_end = req_start + timedelta(hours=window_hours)

        # Ready time and due time for shipment
        ready_time = req_start - timedelta(hours=rng.randint(6, 24))
        due_time = req_end + timedelta(hours=rng.randint(12, 48))

        # 3. Create Shipment
        shp_id = generate_shipment_id(sim_year, idx)
        shipment = Shipment(
            shipment_id=shp_id,
            tracking_number=f"TRK-{sim_year}-{idx:06d}",
            shipment_type=direction,
            pallet_count=pallet_count,
            weight_kg=weight_kg,
            ready_time=ready_time,
            due_time=due_time,
            status="ASSIGNED",
        )
        shipments.append(shipment)

        # Create Shipment Handling Requirements
        for code in req_codes:
            req_entity = req_map[code]
            shipment_requirements.append(
                ShipmentHandlingRequirement(
                    shipment_id=shp_id,
                    requirement_id=req_entity.requirement_id,
                )
            )

        # 4. Derive Deterministic Service Duration (BR-DUR-001)
        duration_minutes = calculate_service_duration(
            pallet_count=pallet_count,
            shipment_type=direction,
            handling_codes=req_codes,
        )

        # 5. Facility and Carrier/Vehicle Matching
        target_facility = master.facilities[(idx - 1) % len(master.facilities)]

        # Select compatible vehicle
        if "REEFER" in req_codes and reefer_vehicles:
            vehicle = reefer_vehicles[rng.randint(0, len(reefer_vehicles) - 1)]
        else:
            vehicle = master.vehicles[rng.randint(0, len(master.vehicles) - 1)]

        appt_id = generate_appointment_id(sim_year, idx)
        appointment = Appointment(
            appointment_id=appt_id,
            facility_id=target_facility.facility_id,
            carrier_id=vehicle.carrier_id,
            vehicle_id=vehicle.vehicle_id,
            dock_id=None,
            yard_slot_id=None,
            appointment_type=direction,
            requested_start=req_start,
            requested_end=req_end,
            scheduled_start=None,
            scheduled_end=None,
            duration_minutes=duration_minutes,
            status="REQUESTED",
        )
        appointments.append(appointment)

        # Link bridge table
        appointment_shipments.append(
            AppointmentShipment(
                appointment_id=appt_id,
                shipment_id=shp_id,
            )
        )

    return TransactionBundle(
        shipments=shipments,
        shipment_requirements=shipment_requirements,
        appointments=appointments,
        appointment_shipments=appointment_shipments,
    )
