"""
Phase 6: Deterministic Independence Logic.
Groups evidence items sharing an origin fingerprint, forward lineage, or report origin group
so they count as a single independent corroborating source.
"""

from typing import Dict, List, Sequence, Set
from backend.app.models.all_models import EvidenceItem


def get_independence_key(item: EvidenceItem) -> str:
    """
    Returns the canonical grouping key for an evidence item.
    Priority:
    1. explicit independence_group column
    2. associated report origin_group_id or source_fingerprint
    3. item ID (independent single item)
    """
    if item.independence_group:
        return item.independence_group

    if item.report:
        if getattr(item.report, "origin_group_id", None):
            return item.report.origin_group_id
        if getattr(item.report, "source_fingerprint", None):
            return item.report.source_fingerprint

    # Fallback to unique item ID
    return item.id


def compute_independent_source_count(evidence_items: Sequence[EvidenceItem]) -> int:
    """
    Computes the number of truly independent sources among the evidence items.
    Multiple items sharing the same origin/fingerprint count as ONE independent source.
    Items that are neutral, unassessed, or rejected are not counted toward corroborating independence.
    """
    seen_groups: Set[str] = set()

    for item in evidence_items:
        # Only supporting or corroborating items contribute to corroboration source count
        assessment = getattr(item, "assessment", None) or "unassessed"
        v_status = getattr(item, "verification_status", None)
        status_val = v_status.value if hasattr(v_status, "value") else str(v_status or "")

        if assessment in ("supports", "corroborating") or status_val in ("corroborating", "corroborated"):
            group_key = get_independence_key(item)
            seen_groups.add(group_key)

    return len(seen_groups)


def group_evidence_by_origin(
    evidence_items: Sequence[EvidenceItem],
) -> Dict[str, List[EvidenceItem]]:
    """Groups evidence items by their canonical independence group."""
    grouped: Dict[str, List[EvidenceItem]] = {}
    for item in evidence_items:
        key = get_independence_key(item)
        grouped.setdefault(key, []).append(item)
    return grouped
