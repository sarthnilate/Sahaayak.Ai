"""
Incident Status State Machine — single source of truth for all valid transitions.
"""

from backend.app.models.all_models import IncidentStatusEnum

# Allowed transitions: current_status -> set of valid next statuses
VALID_TRANSITIONS: dict[IncidentStatusEnum, set[IncidentStatusEnum]] = {
    IncidentStatusEnum.OPEN: {
        IncidentStatusEnum.INVESTIGATING,
        IncidentStatusEnum.MITIGATING,
        IncidentStatusEnum.CLOSED,  # requires confirmation + reason
    },
    IncidentStatusEnum.INVESTIGATING: {
        IncidentStatusEnum.MITIGATING,
        IncidentStatusEnum.RESOLVED,
        IncidentStatusEnum.OPEN,  # rollback
    },
    IncidentStatusEnum.MITIGATING: {
        IncidentStatusEnum.RESOLVED,
        IncidentStatusEnum.INVESTIGATING,  # rollback
    },
    IncidentStatusEnum.RESOLVED: {
        IncidentStatusEnum.CLOSED,
        IncidentStatusEnum.INVESTIGATING,  # re-open
    },
    IncidentStatusEnum.CLOSED: set(),  # Terminal — no transitions out
}

# Statuses that require a close_reason
CLOSE_REQUIRES_REASON = {IncidentStatusEnum.CLOSED}

# Task statuses that are considered "open" (blocking incident close)
OPEN_TASK_STATUSES = {"suggested", "pending", "in_progress"}


def is_valid_transition(current: IncidentStatusEnum, target: IncidentStatusEnum) -> bool:
    """Check if a status transition is allowed."""
    allowed = VALID_TRANSITIONS.get(current, set())
    return target in allowed


def get_allowed_transitions(current: IncidentStatusEnum) -> list[str]:
    """Return the list of allowed next statuses from current."""
    return sorted([s.value for s in VALID_TRANSITIONS.get(current, set())])
