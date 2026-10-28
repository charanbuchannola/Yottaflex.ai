"""Lifecycle State Machine and Transition Rules."""

from enum import Enum


class AppointmentStatus(str, Enum):
    """Lifecycle projection states for an appointment."""
    REQUESTED = "REQUESTED"
    ALLOCATED = "ALLOCATED"
    REJECTED = "REJECTED"
    ARRIVED = "ARRIVED"
    CHECKED_IN = "CHECKED_IN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"


class EventType(str, Enum):
    """Authoritative domain lifecycle events."""
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    ALLOCATED = "ALLOCATED"
    REJECTED = "REJECTED"
    ARRIVED = "ARRIVED"
    CHECKED_IN = "CHECKED_IN"
    LOADING_STARTED = "LOADING_STARTED"
    UNLOADING_STARTED = "UNLOADING_STARTED"
    LOADING_COMPLETED = "LOADING_COMPLETED"
    UNLOADING_COMPLETED = "UNLOADING_COMPLETED"
    DEPARTED = "DEPARTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"


# Valid state transitions: Current Status -> Set of permitted EventTypes -> Resulting Status
VALID_TRANSITIONS: dict[AppointmentStatus, dict[EventType, AppointmentStatus]] = {
    AppointmentStatus.REQUESTED: {
        EventType.ALLOCATED: AppointmentStatus.ALLOCATED,
        EventType.REJECTED: AppointmentStatus.REJECTED,
        EventType.CANCELLED: AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.ALLOCATED: {
        EventType.ARRIVED: AppointmentStatus.ARRIVED,
        EventType.CANCELLED: AppointmentStatus.CANCELLED,
        EventType.NO_SHOW: AppointmentStatus.NO_SHOW,
        EventType.RESCHEDULED: AppointmentStatus.RESCHEDULED,
    },
    AppointmentStatus.ARRIVED: {
        EventType.CHECKED_IN: AppointmentStatus.CHECKED_IN,
        EventType.CANCELLED: AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.CHECKED_IN: {
        EventType.LOADING_STARTED: AppointmentStatus.IN_PROGRESS,
        EventType.UNLOADING_STARTED: AppointmentStatus.IN_PROGRESS,
        EventType.CANCELLED: AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.IN_PROGRESS: {
        EventType.LOADING_COMPLETED: AppointmentStatus.IN_PROGRESS,
        EventType.UNLOADING_COMPLETED: AppointmentStatus.IN_PROGRESS,
        EventType.DEPARTED: AppointmentStatus.COMPLETED,
        EventType.COMPLETED: AppointmentStatus.COMPLETED,
    },
    AppointmentStatus.RESCHEDULED: {
        EventType.ALLOCATED: AppointmentStatus.ALLOCATED,
        EventType.REJECTED: AppointmentStatus.REJECTED,
    },
    # Terminal states
    AppointmentStatus.COMPLETED: {},
    AppointmentStatus.REJECTED: {},
    AppointmentStatus.CANCELLED: {},
    AppointmentStatus.NO_SHOW: {},
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle state transition is attempted."""
    pass


def get_next_status(current_status: str, event_type: str) -> AppointmentStatus:
    """Validate transition and compute next projection status."""
    try:
        curr_enum = AppointmentStatus(current_status)
    except ValueError:
        raise InvalidStateTransitionError(f"Unknown current status: {current_status}")

    try:
        evt_enum = EventType(event_type)
    except ValueError:
        raise InvalidStateTransitionError(f"Unknown event type: {event_type}")

    permitted = VALID_TRANSITIONS.get(curr_enum, {})
    if evt_enum not in permitted:
        raise InvalidStateTransitionError(
            f"Illegal transition: Cannot apply event {evt_enum.value} to appointment with status {curr_enum.value}"
        )
    return permitted[evt_enum]
