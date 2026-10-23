"""
Applicability Engine: Deterministic, explainable matching between Live Official Alerts
and Incident context (District, State, or Lat/Lng coordinates).

Rules:
1. No LLM hallucinations: Uses exact or substring boundary matching of normalized geographic tokens.
2. Centroid matching: When circle/centroid lat,lng is available, calculates haversine distance.
3. OFFICIAL ADVISORIES DO NOT COUNT AS COMMUNITY CORROBORATION:
   Matches are classified as 'OFFICIAL_CONTEXT', not independent community verification.
"""

import math
import re
from typing import Dict, List, Optional, Tuple


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance in kilometers between two points."""
    r = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def normalize_geo_text(text: Optional[str]) -> str:
    if not text:
        return ""
    # Lowercase, strip non-alphanumeric except spaces
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


def check_alert_applicability(
    alert_area: str,
    alert_headline: str,
    incident_location_name: Optional[str] = None,
    incident_lat: Optional[float] = None,
    incident_lon: Optional[float] = None,
    alert_centroid: Optional[str] = None,
    max_distance_km: float = 75.0,
) -> Tuple[bool, str, Optional[float]]:
    """
    Evaluates whether an official alert applies to a given incident.
    Returns:
        (is_applicable, match_rationale, distance_km)
    """
    norm_area = normalize_geo_text(f"{alert_area} {alert_headline}")
    
    # 1. Geographic name match
    if incident_location_name:
        tokens = [t for t in normalize_geo_text(incident_location_name).split() if len(t) >= 4]
        for token in tokens:
            # Word boundary search in alert area
            if re.search(rf"\b{re.escape(token)}\b", norm_area):
                return True, f"Geographic entity '{token.title()}' explicitly referenced in advisory area.", None

    # 2. Coordinate centroid distance check
    if incident_lat is not None and incident_lon is not None and alert_centroid:
        try:
            parts = [float(p.strip()) for p in alert_centroid.split(",")]
            if len(parts) >= 2:
                alert_lat, alert_lon = parts[0], parts[1]
                dist = haversine_km(incident_lat, incident_lon, alert_lat, alert_lon)
                if dist <= max_distance_km:
                    return (
                        True,
                        f"Incident coordinates within {dist:.1f} km of advisory centroid ({max_distance_km} km radius).",
                        dist,
                    )
        except Exception:
            pass

    return False, "No geographic intersection detected.", None
