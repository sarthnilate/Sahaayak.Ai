import json
import logging
import os
from typing import Any, Dict, Optional

from backend.app.core.config import settings
from backend.app.schemas.all_schemas import ExtractionResultSchema

logger = logging.getLogger(__name__)

# Deterministic Demo Database for reliable, reproducible demonstrations
DEMO_KNOWLEDGE_BASE = [
    {
        "keywords": [
            "hindmata",
            "dadar",
            "waterlogging",
            "3 feet",
            "flooding",
            "दादर",
            "हिंदमाता",
            "पाणी",
            "गाड़ियां",
        ],
        "result": {
            "hazard_type": "waterlogging",
            "severity": "critical",
            "water_depth_cm": 90,
            "location_name": "Hindmata Flyover, Dadar TT Circle, Mumbai",
            "approximate_lat": 19.0178,
            "approximate_lng": 72.8478,
            "has_grounded_coordinates": True,
            "affected_infrastructure": ["Dadar TT Roadway", "BEST Bus Route", "Subway Access"],
            "urgent_needs": [
                "Industrial Dewatering Pumps",
                "Traffic Police Diversion",
                "Stranded Commuter Assistance",
            ],
            "casualties_flag": False,
            "confidence_score": 0.96,
            "sentiment_urgency": "critical",
            "language_detected": "mixed",
            "summary": "Severe waterlogging (approx 90cm) at Hindmata Flyover underpass causing vehicular breakdown and public transit standstill.",
        },
    },
    {
        "keywords": ["tree", "fallen", "bandra", "western express", "highway", "झाड", "रास्ता"],
        "result": {
            "hazard_type": "tree_fall",
            "severity": "high",
            "water_depth_cm": None,
            "location_name": "Western Express Highway near Bandra Flyover Northbound",
            "approximate_lat": 19.0596,
            "approximate_lng": 72.8450,
            "has_grounded_coordinates": True,
            "affected_infrastructure": ["WEH Northbound Lane 1 & 2"],
            "urgent_needs": ["Tree Cutting Crew", "Crane/Tow Truck", "Hazard Cones"],
            "casualties_flag": False,
            "confidence_score": 0.94,
            "sentiment_urgency": "urgent",
            "language_detected": "en",
            "summary": "Large banyan tree fallen across 2 lanes of Western Express Highway near Bandra; heavy vehicular congestion forming.",
        },
    },
    {
        "keywords": ["dam", "collapse", "bridge", "burst", "whatsapp", "अफवाह", "धरण"],
        "result": {
            "hazard_type": "unverified_rumor",
            "severity": "medium",
            "water_depth_cm": None,
            "location_name": "Vihar Dam / Powai Lake Overflow (Unconfirmed)",
            "approximate_lat": 19.1415,
            "approximate_lng": 72.9038,
            "has_grounded_coordinates": False,
            "affected_infrastructure": ["Unknown / Forwarded Claim"],
            "urgent_needs": [
                "Fact Verification with Municipal Disaster Cell",
                "Public Clarification",
            ],
            "casualties_flag": False,
            "confidence_score": 0.45,
            "sentiment_urgency": "moderate",
            "language_detected": "en",
            "summary": "Unverified social media rumor regarding municipal dam breach without corroborating telemetry or authority statement.",
        },
    },
    {
        "keywords": ["somewhere", "water", "help", "road", "gully", "कुठेतरी", "गल्ली"],
        "result": {
            "hazard_type": "waterlogging",
            "severity": "medium",
            "water_depth_cm": 35,
            "location_name": "Unspecified Street (Contradictory landmarks reported)",
            "approximate_lat": None,
            "approximate_lng": None,
            "has_grounded_coordinates": False,
            "affected_infrastructure": ["Local gully"],
            "urgent_needs": ["Location Confirmation", "Ward Inspection"],
            "casualties_flag": False,
            "confidence_score": 0.52,
            "sentiment_urgency": "moderate",
            "language_detected": "en",
            "summary": "Localized waterlogging reported with ambiguous location cues; requires coordinator clarification.",
        },
    },
]


class AIAdapter:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = settings.GEMINI_MODEL
        self.client = None

        if self.api_key:
            try:
                from google import genai

                self.client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Google Gemini Client successfully.")
            except Exception as e:
                logger.warning(
                    f"Could not initialize Google GenAI Client: {e}. Falling back to Demo Adapter."
                )
                self.client = None

    @property
    def is_live(self) -> bool:
        return self.client is not None and bool(self.api_key)

    @property
    def provider_mode(self) -> str:
        return (
            f"Google Gemini ({self.model_name})" if self.is_live else "Deterministic Demo Adapter"
        )

    async def extract_incident_data(
        self, text: str, media_path: Optional[str] = None, language: str = "en"
    ) -> Dict[str, Any]:
        """
        Extract structured incident details using Google Gemini API if configured,
        or the deterministic Demo Adapter otherwise.
        """
        # If live Gemini is configured, use it
        if self.is_live:
            try:
                return await self._extract_with_gemini(text, media_path)
            except Exception as e:
                logger.error(
                    f"Gemini API invocation failed: {e}. Falling back to demo extractor to preserve data."
                )
                # We do not fail silently; we record that demo fallback occurred
                result = self._extract_with_demo(text, language)
                result["_provider_error"] = str(e)
                result["_fallback_to_demo"] = True
                return result

        # Otherwise deterministic demo extraction
        return self._extract_with_demo(text, language)

    async def _extract_with_gemini(
        self, text: str, media_path: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt = f"""
You are an expert emergency incident extraction AI for Sahaayak AI during heavy urban rainfall and crises.
Analyze this community report (which may be in English, Hindi, or Marathi):
Report Content:
"{text}"

Extract and format the information as valid JSON matching this exact schema:
{{
  "hazard_type": "waterlogging" | "tree_fall" | "road_blocked" | "power_outage" | "unverified_rumor" | "other",
  "severity": "critical" | "high" | "medium" | "low",
  "water_depth_cm": integer or null,
  "location_name": "specific landmark, intersection, or street name",
  "approximate_lat": float or null,
  "approximate_lng": float or null,
  "has_grounded_coordinates": boolean,
  "affected_infrastructure": ["list of affected items"],
  "urgent_needs": ["pumps", "ambulances", "tree cutter", "etc"],
  "casualties_flag": boolean,
  "confidence_score": float between 0.1 and 1.0,
  "sentiment_urgency": "critical" | "urgent" | "moderate" | "low",
  "language_detected": "en" | "hi" | "mr" | "other",
  "summary": "Clear, objective single-sentence summary of the incident"
}}
Respond with ONLY raw JSON, no markdown formatting.
"""
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        parsed = json.loads(raw_text)
        # Validate against Pydantic schema
        validated = ExtractionResultSchema(**parsed)
        return validated.model_dump()

    def _extract_with_demo(self, text: str, language: str = "en") -> Dict[str, Any]:
        """
        Deterministic, reproducible extractor for demo testing.
        Matches keywords from the predefined test suite or builds an explainable fallback.
        """
        text_lower = text.lower()

        for entry in DEMO_KNOWLEDGE_BASE:
            keywords: list = entry["keywords"]  # type: ignore[assignment]
            if any(kw in text_lower for kw in keywords):
                result_data: Dict[str, Any] = entry["result"]  # type: ignore[assignment]
                res = dict(result_data)
                # Detect language if not specified
                if any(char in text for char in "अआइईउऊऋएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह"):
                    if "आहे" in text or "झाले" in text or "पाणी" in text:
                        res["language_detected"] = "mr"
                    else:
                        res["language_detected"] = "hi"
                return res

        # Fallback heuristic extraction
        hazard = (
            "waterlogging"
            if any(w in text_lower for w in ["water", "flood", "rain", "डूब", "जल"])
            else "road_blocked"
        )
        severity = (
            "high"
            if any(w in text_lower for w in ["urgent", "stuck", "danger", "critical", "फंसे"])
            else "medium"
        )

        return {
            "hazard_type": hazard,
            "severity": severity,
            "water_depth_cm": 45 if hazard == "waterlogging" else None,
            "location_name": "Reported Urban Location",
            "approximate_lat": 19.0760,
            "approximate_lng": 72.8777,
            "has_grounded_coordinates": False,
            "affected_infrastructure": ["Local thoroughfare"],
            "urgent_needs": ["Inspection Crew"],
            "casualties_flag": False,
            "confidence_score": 0.82,
            "sentiment_urgency": severity,
            "language_detected": language,
            "summary": f"Field observation of {hazard.replace('_', ' ')}: {text[:80]}...",
        }


ai_adapter = AIAdapter()
