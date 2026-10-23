"""
Phase 6: Evidence Status Machine & Deterministic Suggestion Rules.
Governs overall incident evidence statuses:
  unassessed -> unverified -> partially_corroborated -> conflicting_evidence -> corroborated -> closed_after_review
"""

from typing import Dict, List, Optional, Sequence, Set
from backend.app.core.errors import InvalidStateTransitionError
from backend.app.models.all_models import AssessmentEnum, EvidenceItem, EvidenceStatusEnum
from backend.app.services.evidence.independence import compute_independent_source_count


# Single source of truth for allowed transitions in the evidence status machine
ALLOWED_EVIDENCE_TRANSITIONS: Dict[EvidenceStatusEnum, Set[EvidenceStatusEnum]] = {
    EvidenceStatusEnum.UNASSESSED: {
        EvidenceStatusEnum.UNVERIFIED,
        EvidenceStatusEnum.PARTIALLY_CORROBORATED,
        EvidenceStatusEnum.CONFLICTING_EVIDENCE,
    },
    EvidenceStatusEnum.UNVERIFIED: {
        EvidenceStatusEnum.PARTIALLY_CORROBORATED,
        EvidenceStatusEnum.CONFLICTING_EVIDENCE,
        EvidenceStatusEnum.UNASSESSED,
        EvidenceStatusEnum.CORROBORATED,
    },
    EvidenceStatusEnum.PARTIALLY_CORROBORATED: {
        EvidenceStatusEnum.CORROBORATED,
        EvidenceStatusEnum.CONFLICTING_EVIDENCE,
        EvidenceStatusEnum.UNVERIFIED,
        EvidenceStatusEnum.CLOSED_AFTER_REVIEW,
    },
    EvidenceStatusEnum.CONFLICTING_EVIDENCE: {
        EvidenceStatusEnum.PARTIALLY_CORROBORATED,
        EvidenceStatusEnum.CORROBORATED,
        EvidenceStatusEnum.UNVERIFIED,
        EvidenceStatusEnum.CLOSED_AFTER_REVIEW,
    },
    EvidenceStatusEnum.CORROBORATED: {
        EvidenceStatusEnum.CONFLICTING_EVIDENCE,
        EvidenceStatusEnum.PARTIALLY_CORROBORATED,
        EvidenceStatusEnum.CLOSED_AFTER_REVIEW,
    },
    EvidenceStatusEnum.CLOSED_AFTER_REVIEW: {
        # Terminal state for verification lifecycle; can be reopened to investigating if new evidence arrives
        EvidenceStatusEnum.PARTIALLY_CORROBORATED,
        EvidenceStatusEnum.UNVERIFIED,
        EvidenceStatusEnum.CONFLICTING_EVIDENCE,
    },
}

# Legacy alias mappings for backward compatibility
STATUS_COMPATIBILITY_MAP: Dict[str, EvidenceStatusEnum] = {
    "conflicting": EvidenceStatusEnum.CONFLICTING_EVIDENCE,
    "corroborating": EvidenceStatusEnum.PARTIALLY_CORROBORATED,
    "disproven": EvidenceStatusEnum.CONFLICTING_EVIDENCE,
}


def normalize_evidence_status(val: str | EvidenceStatusEnum) -> EvidenceStatusEnum:
    """Normalizes string or enum to canonical EvidenceStatusEnum."""
    if isinstance(val, EvidenceStatusEnum):
        return val
    raw = str(val).lower()
    if raw in STATUS_COMPATIBILITY_MAP:
        return STATUS_COMPATIBILITY_MAP[raw]
    try:
        return EvidenceStatusEnum(raw)
    except ValueError:
        return EvidenceStatusEnum.UNVERIFIED


def is_valid_evidence_transition(
    current: EvidenceStatusEnum | str,
    target: EvidenceStatusEnum | str,
) -> bool:
    """Validates if transition from current to target status is permitted."""
    curr_enum = normalize_evidence_status(current)
    tgt_enum = normalize_evidence_status(target)

    # Idempotent same-state is always permitted
    if curr_enum == tgt_enum:
        return True

    allowed = ALLOWED_EVIDENCE_TRANSITIONS.get(curr_enum, set())
    return tgt_enum in allowed


def validate_evidence_transition(
    current: EvidenceStatusEnum | str,
    target: EvidenceStatusEnum | str,
) -> None:
    """Raises InvalidStateTransitionError if transition is not allowed."""
    curr_enum = normalize_evidence_status(current)
    tgt_enum = normalize_evidence_status(target)

    if not is_valid_evidence_transition(curr_enum, tgt_enum):
        raise InvalidStateTransitionError(
            entity="incident_evidence_status",
            current_state=curr_enum.value,
            attempted_state=tgt_enum.value,
            message=f"Cannot transition evidence status from '{curr_enum.value}' to '{tgt_enum.value}'. Allowed transitions: {sorted([s.value for s in ALLOWED_EVIDENCE_TRANSITIONS.get(curr_enum, set())])}",
        )


def suggest_evidence_status(evidence_items: Sequence[EvidenceItem]) -> EvidenceStatusEnum:
    """
    Pure, deterministic rule function to compute suggested incident evidence status:
    1. If ANY evidence item contradicts (or is contradictory), status is CONFLICTING_EVIDENCE.
    2. Count truly independent supporting sources (deduplicating forwarded claims/lineage).
    3. If >= 2 independent supporting sources, status is CORROBORATED (Corroborated by Available Evidence).
    4. If == 1 independent supporting source, status is PARTIALLY_CORROBORATED.
    5. If evidence exists but none support or contradict (e.g. only neutral/contextual), status is UNVERIFIED.
    6. If no items or only unassessed items, status is UNASSESSED.
    """
    if not evidence_items:
        return EvidenceStatusEnum.UNASSESSED

    has_contradiction = False
    has_assessed_item = False

    for item in evidence_items:
        assessment = getattr(item, "assessment", None) or "unassessed"
        e_type = getattr(item, "evidence_type", None) or ""
        v_status = getattr(item, "verification_status", None)
        status_val = v_status.value if hasattr(v_status, "value") else str(v_status or "")

        if assessment != "unassessed" or status_val != "unverified":
            has_assessed_item = True

        if assessment == "contradicts" or e_type == "contradictory" or status_val in ("conflicting", "conflicting_evidence", "disproven"):
            has_contradiction = True

    if has_contradiction:
        return EvidenceStatusEnum.CONFLICTING_EVIDENCE

    # Compute independent supporting source count
    independent_support_count = compute_independent_source_count(evidence_items)

    if independent_support_count >= 2:
        return EvidenceStatusEnum.CORROBORATED
    elif independent_support_count == 1:
        return EvidenceStatusEnum.PARTIALLY_CORROBORATED
    elif has_assessed_item:
        return EvidenceStatusEnum.UNVERIFIED
    else:
        return EvidenceStatusEnum.UNASSESSED
