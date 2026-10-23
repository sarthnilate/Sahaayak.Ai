import math
from typing import Tuple

from backend.app.models.all_models import Incident, Report


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Haversine formula
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class MatchingService:
    @staticmethod
    def evaluate_match(report: Report, incident: Incident) -> Tuple[float, str]:
        """
        Calculates similarity score (0.0 to 1.0) and generates an explainable rationale.
        Considers:
        1. Category match
        2. Location / coordinates proximity
        3. Text keyword overlap (e.g. Hindmata, Dadar, Flyover, etc.)
        4. Time delta
        """
        score = 0.0
        reasons = []

        # 1. Category match
        report_cat = (report.extracted_json or {}).get("hazard_type", "waterlogging")
        if report_cat == incident.category:
            score += 0.35
            reasons.append(f"Matching incident category: {report_cat}")
        else:
            reasons.append(f"Differing hazard category ({report_cat} vs {incident.category})")

        # 2. Location proximity
        rep_lat = report.coordinates_lat or (report.extracted_json or {}).get("approximate_lat")
        rep_lng = report.coordinates_lng or (report.extracted_json or {}).get("approximate_lng")

        if rep_lat and rep_lng and incident.latitude and incident.longitude:
            dist = calculate_distance_km(rep_lat, rep_lng, incident.latitude, incident.longitude)
            if dist < 0.8:
                score += 0.40
                reasons.append(f"Very close spatial proximity: ~{int(dist * 1000)}m apart")
            elif dist < 2.5:
                score += 0.25
                reasons.append(f"Within localized cluster radius: ~{round(dist, 1)}km apart")
            else:
                reasons.append(f"Distant location: ~{round(dist, 1)}km apart")
        else:
            # Fallback to textual landmark matching
            loc_claim = (
                report.location_claim or (report.extracted_json or {}).get("location_name", "")
            ).lower()
            inc_loc = incident.location_name.lower()

            # Common token overlap
            tokens_rep = set(loc_claim.replace(",", " ").split())
            tokens_inc = set(inc_loc.replace(",", " ").split())
            common_tokens = tokens_rep.intersection(tokens_inc) - {
                "the",
                "near",
                "and",
                "at",
                "in",
                "road",
                "circle",
            }

            if common_tokens:
                score += 0.30
                reasons.append(f"Shared landmark tokens: {', '.join(common_tokens)}")

        # 3. Text content keyword overlap
        rep_text_words = set(report.original_text.lower().split())
        inc_summary_words = set((incident.summary + " " + incident.title).lower().split())
        shared_keywords = rep_text_words.intersection(inc_summary_words) - {
            "the",
            "is",
            "a",
            "of",
            "and",
            "to",
            "in",
            "at",
            "feet",
            "water",
        }
        if len(shared_keywords) >= 2:
            score += 0.20
            reasons.append(f"Contextual keyword overlap: {', '.join(list(shared_keywords)[:3])}")

        # 4. Temporal factor (within 12 hours)
        time_diff = abs((report.submitted_at - incident.created_at).total_seconds()) / 3600.0
        if time_diff < 4.0:
            score += 0.05
            reasons.append(f"Reported within {round(time_diff, 1)}h of incident creation")

        score = min(round(score, 2), 0.98)
        rationale = " | ".join(reasons)
        return score, rationale


matching_service = MatchingService()
