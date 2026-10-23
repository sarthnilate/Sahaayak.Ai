import enum
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncidentCategoryEnum(str, enum.Enum):
    WATERLOGGING = "waterlogging"
    TREE_FALL = "tree_fall"
    ROAD_DAMAGE = "road_damage"
    FIRE = "fire"
    MEDICAL = "medical"
    BUILDING_COLLAPSE = "building_collapse"
    POWER_OUTAGE = "power_outage"
    GAS_LEAK = "gas_leak"
    LANDSLIDE = "landslide"
    OTHER = "other"
    UNKNOWN = "unknown"


class LanguageEnum(str, enum.Enum):
    EN = "en"
    HI = "hi"
    MR = "mr"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class LocationPrecisionEnum(str, enum.Enum):
    EXACT_COORDINATES = "exact_coordinates"
    LANDMARK = "landmark"
    NEIGHBORHOOD = "neighborhood"
    CITY_LEVEL = "city_level"
    UNKNOWN = "unknown"


class LocationSourceEnum(str, enum.Enum):
    TEXT = "text"
    EXIF = "exif"
    METADATA = "metadata"
    UNKNOWN = "unknown"


class SeverityEnum(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


# Regex to reject invented placeholders like "N/A guess", "unknown guess", "road (guess)"
FORBIDDEN_PLACEHOLDER_REGEX = re.compile(r"\b(guess|n/a\s*guess|unknown\s*guess|placeholder|tbd\s*guess)\b", re.IGNORECASE)


def validate_no_invented_placeholders(v: Any) -> Any:
    """Rejects invented placeholders or ungrounded guesses."""
    if isinstance(v, str):
        if FORBIDDEN_PLACEHOLDER_REGEX.search(v):
            raise ValueError(f"Invented placeholder or ungrounded guess rejected: '{v}'. Use null or 'unknown'.")
    elif isinstance(v, list):
        for item in v:
            if isinstance(item, str) and FORBIDDEN_PLACEHOLDER_REGEX.search(item):
                raise ValueError(f"Invented placeholder in list item rejected: '{item}'.")
    return v


class ReportExtractionSchema(BaseModel):
    """
    Standardized, strictly-validated extraction schema for citizen disaster reports.
    Any unknown details remain null or 'unknown' — invented placeholders are rejected.
    """
    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    category: IncidentCategoryEnum = Field(
        default=IncidentCategoryEnum.UNKNOWN,
        description="Hazard classification. Must be 'unknown' if not clearly identified."
    )
    short_summary: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Objective, concise summary of the situation."
    )
    original_text_language: LanguageEnum = Field(
        default=LanguageEnum.UNKNOWN,
        description="Detected source language of the input text: en, hi, mr, mixed, unknown."
    )
    reported_location_text: Optional[str] = Field(
        default=None,
        description="Reported landmark, intersection, or street. Null if completely unmentioned."
    )
    location_precision: LocationPrecisionEnum = Field(
        default=LocationPrecisionEnum.UNKNOWN,
        description="Granularity of the extracted location."
    )
    location_source: LocationSourceEnum = Field(
        default=LocationSourceEnum.UNKNOWN,
        description="Information source for the location: text, exif, metadata, unknown."
    )
    incident_time: Optional[str] = Field(
        default=None,
        description="Reported time of occurrence (ISO string or relative text). Null if unmentioned."
    )
    claimed_severity: SeverityEnum = Field(
        default=SeverityEnum.UNKNOWN,
        description="Urgency claimed by the reporter: critical, high, medium, low, unknown."
    )
    safety_concern: bool = Field(
        default=False,
        description="True if imminent threat to human life or physical safety is indicated."
    )
    safety_concern_reason: Optional[str] = Field(
        default=None,
        description="Explicit rationale for the safety concern flag if True, otherwise null."
    )
    people_or_infrastructure_affected: List[str] = Field(
        default_factory=list,
        description="Only list people or infrastructure explicitly cited in the report."
    )
    source_attribution: Optional[str] = Field(
        default=None,
        description="Attribution (e.g. eye-witness, forwarded message, civic authority, news). Null if unknown."
    )
    is_forwarded_message: bool = Field(
        default=False,
        description="True if text exhibits hallmarks of forwarded/chain messages (e.g., 'FORWARDED AS RECEIVED')."
    )
    explicit_facts: List[str] = Field(
        default_factory=list,
        description="Uncontestable factual assertions directly expressed in the input."
    )
    model_inferences: List[str] = Field(
        default_factory=list,
        description="Logical deductions made by the model, clearly separated from explicit facts."
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Key gaps in the report needed for emergency dispatch."
    )
    ambiguities: List[str] = Field(
        default_factory=list,
        description="Vague or multiple conflicting interpretations in the input."
    )
    contradictions: List[str] = Field(
        default_factory=list,
        description="Direct internal contradictions identified within the report."
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Recommended clarifying questions for the intake officer to ask."
    )

    # Validators to enforce no invented placeholders
    @field_validator(
        "short_summary",
        "reported_location_text",
        "safety_concern_reason",
        "source_attribution",
        "incident_time",
        mode="after"
    )
    @classmethod
    def check_string_placeholders(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            validate_no_invented_placeholders(v)
        return v

    @field_validator(
        "people_or_infrastructure_affected",
        "explicit_facts",
        "model_inferences",
        "missing_information",
        "ambiguities",
        "contradictions",
        "follow_up_questions",
        mode="after"
    )
    @classmethod
    def check_list_placeholders(cls, v: List[str]) -> List[str]:
        validate_no_invented_placeholders(v)
        return v


class ExtractionMetadata(BaseModel):
    provider: str
    mode: str
    model: str
    latency_ms: int
    attempt_count: int = 1
    schema_version: str = "1.0.0"
    simulated: bool = False
    processed_at: datetime
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class ExtractionResult(BaseModel):
    extraction: Optional[ReportExtractionSchema] = None
    metadata: ExtractionMetadata


class CoordinatorCorrectionSchema(BaseModel):
    corrected_category: Optional[IncidentCategoryEnum] = None
    corrected_severity: Optional[SeverityEnum] = None
    corrected_location: Optional[str] = None
    correction_notes: str = Field(..., min_length=3, max_length=1000)
    additional_context: Optional[Dict[str, Any]] = None
