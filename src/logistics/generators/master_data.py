"""Deterministic Master Data Generator for Facilities, Docks, Yards, Shifts, Carriers, and Vehicles."""

from datetime import date, datetime, time, timedelta, timezone
import random
from typing import NamedTuple

from logistics.config import ProfileConfig
from logistics.generators.identifiers import (
    generate_carrier_id,
    generate_dock_id,
    generate_facility_id,
    generate_handling_requirement_id,
    generate_labor_shift_id,
    generate_vehicle_id,
    generate_yard_slot_id,
)
from logistics.models.carrier import Carrier, Vehicle
from logistics.models.facility import Dock, DockHandlingCapability, Facility, YardSlot
from logistics.models.labor import LaborShift
from logistics.models.shipment import HandlingRequirement

# Standard master handling requirements catalogue
STANDARD_HANDLING_REQUIREMENTS = [
    ("REEFER", "Refrigerated / Temperature-controlled cold chain cargo"),
    ("HAZMAT", "Hazardous materials requiring certified handling and spill containment"),
    ("FRAGILE", "High-value fragile items requiring gentle handling and strap restraints"),
    ("LIFTGATE", "Requires hydraulic liftgate loading or ground-level dock leveler"),
    ("OVERSIZED", "Oversized pallets or non-standard footprint cargo"),
]

FACILITY_CITIES = [
    ("Dallas Central DC", "America/Chicago"),
    ("Chicago Logistics Hub", "America/Chicago"),
    ("Atlanta Freight Center", "America/New_York"),
    ("Los Angeles Gateway", "America/Los_Angeles"),
    ("New Jersey Distribution", "America/New_York"),
    ("Memphis Consolidation Center", "America/Chicago"),
    ("Columbus Logistics Park", "America/New_York"),
    ("Kansas City Freight Hub", "America/Chicago"),
    ("Seattle Coastal DC", "America/Los_Angeles"),
    ("Phoenix Inland Port", "America/Phoenix"),
]

CARRIER_NAMES = [
    ("Apex Logistics", "APEX"),
    ("Blue Horizon Freight", "BHRZ"),
    ("Cardinal Express", "CARD"),
    ("Delta Transport", "DLTA"),
    ("Eagle Linehaul", "EAGL"),
    ("Falcon Logistics", "FALC"),
    ("Golden Gate Hauling", "GGHA"),
    ("Highland Freightways", "HGFW"),
    ("Ironclad Carriers", "IRNC"),
    ("Jupiter Transport", "JUPE"),
    ("Keystone Logistics", "KEYS"),
    ("Liberty Dispatch", "LBRT"),
    ("Midwest Freight Services", "MDFS"),
    ("North Star Freight", "NSTR"),
    ("Olympus Intermodal", "OLYM"),
]

VEHICLE_TYPE_DISTRIBUTION = [
    ("DRY_VAN", 0.65),
    ("REEFER", 0.22),
    ("FLATBED", 0.08),
    ("BOX_TRUCK", 0.05),
]

DOCK_TYPE_DISTRIBUTION = [
    ("INBOUND", 0.40),
    ("OUTBOUND", 0.40),
    ("CROSS_DOCK", 0.20),
]


class MasterDataBundle(NamedTuple):
    """Container for all generated master data entities."""
    facilities: list[Facility]
    docks: list[Dock]
    yard_slots: list[YardSlot]
    handling_requirements: list[HandlingRequirement]
    dock_capabilities: list[DockHandlingCapability]
    carriers: list[Carrier]
    vehicles: list[Vehicle]
    labor_shifts: list[LaborShift]


def generate_master_data(
    config: ProfileConfig,
    seed: int,
    simulation_start: datetime,
) -> MasterDataBundle:
    """Deterministically generate all master data entities using explicit distributions."""
    rng = random.Random(seed)

    # 1. Handling Requirements
    handling_requirements: list[HandlingRequirement] = []
    req_by_code: dict[str, HandlingRequirement] = {}
    for i, (code, desc) in enumerate(STANDARD_HANDLING_REQUIREMENTS, start=1):
        req = HandlingRequirement(
            requirement_id=generate_handling_requirement_id(i),
            code=code,
            description=desc,
        )
        handling_requirements.append(req)
        req_by_code[code] = req

    # 2. Facilities, Docks, Yard Slots, and Capabilities
    facilities: list[Facility] = []
    docks: list[Dock] = []
    yard_slots: list[YardSlot] = []
    dock_capabilities: list[DockHandlingCapability] = []

    for f_idx in range(1, config.facilities_count + 1):
        fac_id = generate_facility_id(f_idx)
        city_name, tz_name = FACILITY_CITIES[(f_idx - 1) % len(FACILITY_CITIES)]
        facility_name = f"{city_name} {fac_id}"

        facility = Facility(
            facility_id=fac_id,
            name=facility_name,
            timezone=tz_name,
            operating_start_hour=config.operating_start_hour,
            operating_end_hour=config.operating_end_hour,
            total_yard_slots=config.yard_slots_per_facility,
            is_active=True,
        )
        facilities.append(facility)

        # Docks for this facility
        for d_idx in range(1, config.docks_per_facility + 1):
            dock_id = generate_dock_id(fac_id, d_idx)
            # Deterministic dock type selection
            dock_type_r = rng.random()
            if dock_type_r < 0.40:
                dock_type = "INBOUND"
            elif dock_type_r < 0.80:
                dock_type = "OUTBOUND"
            else:
                dock_type = "CROSS_DOCK"

            # Cold chain and hazmat capabilities (~20% cold chain, ~10% hazmat)
            has_cold = rng.random() < 0.25
            has_haz = rng.random() < 0.15

            dock = Dock(
                dock_id=dock_id,
                facility_id=fac_id,
                dock_number=f"Bay-{d_idx:02d}",
                dock_type=dock_type,
                has_dock_leveler=True,
                has_cold_chain=has_cold,
                has_hazmat_permit=has_haz,
                is_active=True,
            )
            docks.append(dock)

            # Link capabilities to bridge table
            if has_cold and "REEFER" in req_by_code:
                dock_capabilities.append(
                    DockHandlingCapability(
                        dock_id=dock_id,
                        requirement_id=req_by_code["REEFER"].requirement_id,
                    )
                )
            if has_haz and "HAZMAT" in req_by_code:
                dock_capabilities.append(
                    DockHandlingCapability(
                        dock_id=dock_id,
                        requirement_id=req_by_code["HAZMAT"].requirement_id,
                    )
                )

        # Yard slots for this facility
        for y_idx in range(1, config.yard_slots_per_facility + 1):
            yard_slot_id = generate_yard_slot_id(fac_id, y_idx)
            y_rand = rng.random()
            if y_rand < 0.70:
                slot_type = "STANDARD"
            elif y_rand < 0.90:
                slot_type = "REEFER_PLUG"
            else:
                slot_type = "STAGING"

            yard_slot = YardSlot(
                yard_slot_id=yard_slot_id,
                facility_id=fac_id,
                slot_number=f"Y-{y_idx:02d}",
                slot_type=slot_type,
                is_occupied=False,
            )
            yard_slots.append(yard_slot)

    # 3. Carriers
    carriers: list[Carrier] = []
    for c_idx in range(1, config.carriers_count + 1):
        carr_id = generate_carrier_id(c_idx)
        name_base, scac_base = CARRIER_NAMES[(c_idx - 1) % len(CARRIER_NAMES)]
        carrier_name = f"{name_base} {carr_id}"
        if c_idx <= 10:
            scac_code = f"{scac_base[:3]}{c_idx % 10}"
        else:
            scac_code = f"{scac_base[:2]}{c_idx:02d}"

        carrier = Carrier(
            carrier_id=carr_id,
            name=carrier_name,
            scac_code=scac_code,
            is_active=True,
        )
        carriers.append(carrier)

    # 4. Vehicles
    vehicles: list[Vehicle] = []
    for v_idx in range(1, config.vehicles_count + 1):
        veh_id = generate_vehicle_id(v_idx)
        # Assign to carriers in round-robin fashion for stability
        assigned_carrier = carriers[(v_idx - 1) % len(carriers)]

        v_type_r = rng.random()
        cum_prob = 0.0
        selected_type = "DRY_VAN"
        for v_type, prob in VEHICLE_TYPE_DISTRIBUTION:
            cum_prob += prob
            if v_type_r <= cum_prob:
                selected_type = v_type
                break

        has_lift = rng.random() < 0.30
        plate_state = rng.choice(["TX", "IL", "CA", "OH", "GA", "TN"])
        license_plate = f"{plate_state}-{1000 + v_idx}"

        vehicle = Vehicle(
            vehicle_id=veh_id,
            carrier_id=assigned_carrier.carrier_id,
            vehicle_type=selected_type,
            license_plate=license_plate,
            has_liftgate=has_lift,
        )
        vehicles.append(vehicle)

    # 5. Labor Shifts (across simulation days for each facility)
    labor_shifts: list[LaborShift] = []
    start_date = simulation_start.date()

    for day_offset in range(config.simulation_days):
        current_date = start_date + timedelta(days=day_offset)
        date_compact = current_date.strftime("%Y%m%d")

        for facility in facilities:
            # Shift 1: Morning (06:00 to 14:00)
            s1_start = datetime.combine(current_date, time(6, 0), tzinfo=timezone.utc)
            s1_end = datetime.combine(current_date, time(14, 0), tzinfo=timezone.utc)
            shift_1 = LaborShift(
                shift_id=generate_labor_shift_id(facility.facility_id, date_compact, 1),
                facility_id=facility.facility_id,
                shift_date=current_date,
                start_time=s1_start,
                end_time=s1_end,
                total_workers=rng.randint(8, 14),
                forklift_certified_workers=rng.randint(4, 7),
                hazmat_certified_workers=rng.randint(2, 4),
            )
            labor_shifts.append(shift_1)

            # Shift 2: Afternoon/Evening (14:00 to 22:00)
            s2_start = datetime.combine(current_date, time(14, 0), tzinfo=timezone.utc)
            s2_end = datetime.combine(current_date, time(22, 0), tzinfo=timezone.utc)
            shift_2 = LaborShift(
                shift_id=generate_labor_shift_id(facility.facility_id, date_compact, 2),
                facility_id=facility.facility_id,
                shift_date=current_date,
                start_time=s2_start,
                end_time=s2_end,
                total_workers=rng.randint(6, 12),
                forklift_certified_workers=rng.randint(3, 6),
                hazmat_certified_workers=rng.randint(2, 3),
            )
            labor_shifts.append(shift_2)

    return MasterDataBundle(
        facilities=facilities,
        docks=docks,
        yard_slots=yard_slots,
        handling_requirements=handling_requirements,
        dock_capabilities=dock_capabilities,
        carriers=carriers,
        vehicles=vehicles,
        labor_shifts=labor_shifts,
    )
