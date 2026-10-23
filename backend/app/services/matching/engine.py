"""
Phase 5: Pure deterministic duplicate matching engine.
No database dependencies inside scoring functions.
Outputs structured signals, threshold-based bands (NOT probabilities),
and human-readable rationales with explicitly documented unknowns.
"""

import hashlib
import math
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from backend.app.services.matching.lexicon import (
    extract_canonical_concepts,
    jaccard_similarity,
    normalize_text,
    tokenize,
)


class MatchBand(str, Enum):
    STRONG = "strong"
    POSSIBLE = "possible"
    WEAK = "weak"


class MatchSignal(BaseModel):
    name: str
    weight: float
    matched: bool
    detail: str


class MatchEvaluation(BaseModel):
    band: MatchBand
    score: float  # Internal normalized weight for threshold testing
    signals_for: List[MatchSignal] = Field(default_factory=list)
    signals_against: List[MatchSignal] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    rationale: str
    is_suppressed: bool = False
    hard_negative_flag: Optional[str] = None
    is_same_origin: bool = False
    origin_fingerprint: Optional[str] = None


# Named thresholds from configuration
MATCH_STRONG_THRESHOLD = 0.65
MATCH_POSSIBLE_THRESHOLD = 0.35
MAX_TEMPORAL_WINDOW_HOURS = 24.0
CLOSE_GEO_DISTANCE_KM = 1.0


def calculate_haversine_distance_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculates great-circle distance in kilometers."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def compute_source_fingerprint(text: str, origin: Optional[str] = None) -> str:
    """Computes a deterministic SHA-256 fingerprint for copied-claim grouping."""
    normalized = normalize_text(text)
    payload = f"{normalized}:::{origin or ''}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


class MatchingEngine:
    """
    Pure deterministic matching service.
    Zero DB dependencies inside scoring logic.
    """

    @staticmethod
    def evaluate_pair(
        report_a: Dict[str, Any],
        report_b: Dict[str, Any],
    ) -> MatchEvaluation:
        """
        Evaluates duplicate matching between two reports or report & incident.
        """
        signals_for: List[MatchSignal] = []
        signals_against: List[MatchSignal] = []
        unknowns: List[str] = []
        hard_negative: Optional[str] = None

        # Extract attributes
        cat_a = (report_a.get("category") or report_a.get("hazard_type") or "unknown").lower()
        cat_b = (report_b.get("category") or report_b.get("hazard_type") or "unknown").lower()

        text_a = report_a.get("original_text") or report_a.get("summary") or ""
        text_b = report_b.get("original_text") or report_b.get("summary") or ""

        loc_a = (
            report_a.get("reported_location_text")
            or report_a.get("location_name")
            or report_a.get("location_claim")
            or ""
        )
        loc_b = (
            report_b.get("reported_location_text")
            or report_b.get("location_name")
            or report_b.get("location_claim")
            or ""
        )

        lat_a = report_a.get("latitude") or report_a.get("coordinates_lat")
        lng_a = report_a.get("longitude") or report_a.get("coordinates_lng")
        lat_b = report_b.get("latitude") or report_b.get("coordinates_lat")
        lng_b = report_b.get("longitude") or report_b.get("coordinates_lng")

        has_grounded_a = bool(report_a.get("has_grounded_coordinates") and lat_a and lng_a)
        has_grounded_b = bool(report_b.get("has_grounded_coordinates") and lat_b and lng_b)

        time_a = report_a.get("incident_time") or report_a.get("submitted_at") or report_a.get("created_at")
        time_b = report_b.get("incident_time") or report_b.get("submitted_at") or report_b.get("created_at")

        # Copied-claim detection
        fp_a = report_a.get("source_fingerprint") or compute_source_fingerprint(text_a)
        fp_b = report_b.get("source_fingerprint") or compute_source_fingerprint(text_b)
        is_forwarded_a = bool(report_a.get("is_forwarded_message"))
        is_forwarded_b = bool(report_b.get("is_forwarded_message"))

        is_same_origin = False
        origin_fingerprint = None
        if fp_a == fp_b or (is_forwarded_a and is_forwarded_b and normalize_text(text_a) == normalize_text(text_b)):
            is_same_origin = True
            origin_fingerprint = fp_a

        # 1. Category Signal (Weight: 0.35)
        cat_weight = 0.35
        if cat_a == cat_b and cat_a != "unknown":
            signals_for.append(
                MatchSignal(
                    name="same_category",
                    weight=cat_weight,
                    matched=True,
                    detail=f"Matching hazard category: {cat_a}",
                )
            )
        elif cat_a == "unknown" or cat_b == "unknown":
            unknowns.append("One or both reports have an unverified hazard category")
        else:
            # Hard Negative: explicitly conflicting categories
            hard_negative = f"Conflicting categories: '{cat_a}' vs '{cat_b}'"
            signals_against.append(
                MatchSignal(
                    name="same_category",
                    weight=cat_weight,
                    matched=False,
                    detail=f"Divergent categories: '{cat_a}' vs '{cat_b}'",
                )
            )

        # 2. Token / Lexicon Concept Overlap (Weight: 0.25)
        lex_weight = 0.25
        concepts_a = extract_canonical_concepts(text_a)
        concepts_b = extract_canonical_concepts(text_b)
        concept_jaccard = jaccard_similarity(concepts_a, concepts_b)
        shared_concepts = sorted(list(concepts_a.intersection(concepts_b)))

        if concept_jaccard >= 0.20 or len(shared_concepts) >= 2:
            detail_terms = ", ".join(shared_concepts[:4])
            signals_for.append(
                MatchSignal(
                    name="concept_overlap",
                    weight=lex_weight * min(1.0, concept_jaccard * 2.5),
                    matched=True,
                    detail=f"Cross-lingual concept overlap ({len(shared_concepts)} concepts: {detail_terms})",
                )
            )
        else:
            signals_against.append(
                MatchSignal(
                    name="concept_overlap",
                    weight=lex_weight,
                    matched=False,
                    detail=f"Low concept overlap (Jaccard: {concept_jaccard:.2f})",
                )
            )

        # 3. Location Text Overlap (Weight: 0.20)
        loc_weight = 0.20
        tokens_loc_a = set(tokenize(loc_a))
        tokens_loc_b = set(tokenize(loc_b))
        shared_loc_tokens = tokens_loc_a.intersection(tokens_loc_b)

        # Distinct location conflict check (e.g. Dadar vs Bandra)
        distinct_areas = {"dadar", "hindmata", "bandra", "kurla", "andheri", "colaba", "thane", "borivali"}
        areas_a = {t for t in tokens_loc_a if t in distinct_areas}
        areas_b = {t for t in tokens_loc_b if t in distinct_areas}

        if areas_a and areas_b and areas_a.isdisjoint(areas_b):
            hard_negative = f"Clearly distinct named geographic locations ({', '.join(areas_a)} vs {', '.join(areas_b)})"
            signals_against.append(
                MatchSignal(
                    name="location_overlap",
                    weight=loc_weight,
                    matched=False,
                    detail=f"Mutually exclusive localities: {', '.join(areas_a)} vs {', '.join(areas_b)}",
                )
            )
        elif shared_loc_tokens:
            signals_for.append(
                MatchSignal(
                    name="location_overlap",
                    weight=loc_weight,
                    matched=True,
                    detail=f"Shared location tokens: {', '.join(sorted(list(shared_loc_tokens)))}",
                )
            )
        elif not loc_a or not loc_b:
            unknowns.append("Reported location missing or unspecified in one or both reports")
        else:
            signals_against.append(
                MatchSignal(
                    name="location_overlap",
                    weight=loc_weight,
                    matched=False,
                    detail=f"No shared location tokens between '{loc_a}' and '{loc_b}'",
                )
            )

        # 4. Geo Distance (Weight: 0.15) — ONLY WHEN BOTH HAVE GROUNDED COORDS
        geo_weight = 0.15
        if has_grounded_a and has_grounded_b:
            dist_km = calculate_haversine_distance_km(lat_a, lng_a, lat_b, lng_b)
            if dist_km <= CLOSE_GEO_DISTANCE_KM:
                signals_for.append(
                    MatchSignal(
                        name="geo_distance",
                        weight=geo_weight,
                        matched=True,
                        detail=f"Spatial proximity: ~{int(dist_km * 1000)}m (within {int(CLOSE_GEO_DISTANCE_KM * 1000)}m threshold)",
                    )
                )
            elif dist_km > 5.0:
                hard_negative = f"Distant locations separated by {dist_km:.1f}km"
                signals_against.append(
                    MatchSignal(
                        name="geo_distance",
                        weight=geo_weight,
                        matched=False,
                        detail=f"Geodesic separation of {dist_km:.1f}km exceeds localized cluster radius",
                    )
                )
            else:
                signals_against.append(
                    MatchSignal(
                        name="geo_distance",
                        weight=geo_weight,
                        matched=False,
                        detail=f"Intermediate distance: {dist_km:.1f}km",
                    )
                )
        else:
            unknowns.append(
                "Geographic coordinates ungrounded or approximate; physical distance cannot be verified"
            )

        # 5. Temporal Proximity Window (Weight: 0.05)
        time_weight = 0.05
        if time_a and time_b:
            dt_a = time_a if isinstance(time_a, datetime) else datetime.fromisoformat(str(time_a).replace("Z", "+00:00"))
            dt_b = time_b if isinstance(time_b, datetime) else datetime.fromisoformat(str(time_b).replace("Z", "+00:00"))
            diff_hours = abs((dt_a - dt_b).total_seconds()) / 3600.0

            if diff_hours <= 4.0:
                signals_for.append(
                    MatchSignal(
                        name="time_window",
                        weight=time_weight,
                        matched=True,
                        detail=f"Time delta {diff_hours:.1f}h is within tight operational window (<=4h)",
                    )
                )
            elif diff_hours > MAX_TEMPORAL_WINDOW_HOURS:
                hard_negative = f"Temporal delta of {diff_hours:.1f}h exceeds max window ({MAX_TEMPORAL_WINDOW_HOURS}h)"
                signals_against.append(
                    MatchSignal(
                        name="time_window",
                        weight=time_weight,
                        matched=False,
                        detail=f"Time separation of {diff_hours:.1f}h exceeds {MAX_TEMPORAL_WINDOW_HOURS}h threshold",
                    )
                )
            else:
                signals_against.append(
                    MatchSignal(
                        name="time_window",
                        weight=time_weight,
                        matched=False,
                        detail=f"Time delta of {diff_hours:.1f}h exceeds tight window",
                    )
                )
        else:
            unknowns.append("Incident or submission timestamp unconfirmed on one or both items")

        # Sum total score from positive signals
        raw_score = sum(s.weight for s in signals_for)
        normalized_score = round(min(1.0, raw_score), 2)

        # Determine band based on named thresholds
        is_suppressed = False
        if hard_negative is not None:
            band = MatchBand.WEAK
            is_suppressed = True
            normalized_score = min(normalized_score, 0.20)
        elif normalized_score >= MATCH_STRONG_THRESHOLD:
            band = MatchBand.STRONG
        elif normalized_score >= MATCH_POSSIBLE_THRESHOLD:
            band = MatchBand.POSSIBLE
        else:
            band = MatchBand.WEAK

        # Construct human-readable rationale
        parts = []
        if is_same_origin:
            parts.append("COPIED/FORWARDED CLAIM: Reports share origin fingerprint and identical message body.")
        if hard_negative:
            parts.append(f"SUPPRESSION / HARD NEGATIVE: {hard_negative}.")
        if signals_for:
            pro_reasons = "; ".join(s.detail for s in signals_for)
            parts.append(f"Corroborating signals: {pro_reasons}.")
        if signals_against:
            con_reasons = "; ".join(s.detail for s in signals_against)
            parts.append(f"Contradicting/divergent signals: {con_reasons}.")
        if unknowns:
            unknown_str = "; ".join(unknowns)
            parts.append(f"Unknowns: {unknown_str}.")

        rationale = " ".join(parts)

        return MatchEvaluation(
            band=band,
            score=normalized_score,
            signals_for=signals_for,
            signals_against=signals_against,
            unknowns=unknowns,
            rationale=rationale,
            is_suppressed=is_suppressed,
            hard_negative_flag=hard_negative,
            is_same_origin=is_same_origin,
            origin_fingerprint=origin_fingerprint,
        )
