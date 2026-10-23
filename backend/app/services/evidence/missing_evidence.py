"""
Phase 6: Missing Evidence Rule Engine.
Computes epistemic gaps and unverified facets for an incident based on
attached evidence items, linked citizen reports, and location precision.
"""

from typing import Any, Dict, List, Sequence
from backend.app.models.all_models import EvidenceItem, Incident, Report


def compute_missing_evidence(
    incident: Incident,
    evidence_items: Sequence[EvidenceItem],
    reports: Sequence[Report] = (),
) -> List[Dict[str, Any]]:
    """
    Computes structured missing-evidence gaps for an incident.
    Returns a list of dicts with: {gap_type, description, severity}.
    """
    gaps: List[Dict[str, Any]] = []

    # 1. Visual / Photo corroboration check
    has_photo = False
    for rep in reports:
        if getattr(rep, "media_path", None):
            has_photo = True
            break
    for item in evidence_items:
        meta = getattr(item, "metadata_json", None) or {}
        if meta.get("has_photo") or meta.get("media_type") == "image":
            has_photo = True
            break

    if not has_photo:
        gaps.append({
            "gap_type": "missing_photo_evidence",
            "description": "No recent on-the-ground photo evidence attached",
            "severity": "medium",
        })

    # 2. Location grounding & precision check
    if not incident.has_grounded_coordinates or incident.location_precision in ("neighborhood", "area_only", "unknown", None):
        gaps.append({
            "gap_type": "low_location_precision",
            "description": "No exact grounded GPS coordinates (precision is landmark or neighborhood level)",
            "severity": "medium",
        })

    # 3. Independent corroborating sources check
    from backend.app.services.evidence.independence import compute_independent_source_count

    support_count = compute_independent_source_count(evidence_items)
    if support_count == 0:
        gaps.append({
            "gap_type": "no_independent_source",
            "description": "No independent corroborating source verified yet",
            "severity": "high",
        })
    elif support_count == 1:
        gaps.append({
            "gap_type": "single_source_only",
            "description": "Only a single independent source claim (lacks second corroboration)",
            "severity": "medium",
        })

    # 4. Official context feed check (Phase 6B readiness)
    has_official = False
    for item in evidence_items:
        if getattr(item, "evidence_type", None) == "official_context":
            has_official = True
            break

    if not has_official:
        gaps.append({
            "gap_type": "no_official_feed",
            "description": "No official external telemetry or alert feed corroboration (NDMA SACHET / IMD API pending Phase 6B)",
            "severity": "low",
        })

    # 5. Extraction gaps / contradictions from linked reports
    for rep in reports:
        ext = getattr(rep, "extracted_json", None) or {}
        if isinstance(ext, dict):
            missing_info = ext.get("missing_information") or []
            for m in missing_info:
                gap_entry = {
                    "gap_type": "extraction_gap",
                    "description": f"Report #{rep.id[:8]} missing: {m}",
                    "severity": "low",
                }
                if gap_entry not in gaps:
                    gaps.append(gap_entry)

    return gaps
