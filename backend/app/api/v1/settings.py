
from backend.app.core.config import settings
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["Settings"])


class AiStatusResponse(BaseModel):
    mode: str
    provider: str
    model: str
    api_key_configured: bool


@router.get("/ai-status", response_model=AiStatusResponse)
def get_ai_status() -> AiStatusResponse:
    """
    Returns non-sensitive AI operational status:
    - Mode: 'demo' or 'gemini'
    - Provider: 'deterministic-demo' or 'google-genai'
    - Model: configured model name
    - Whether an API key is configured (boolean flag only — never returns the actual key)
    """
    is_gemini = settings.AI_MODE == "gemini"
    has_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())

    return AiStatusResponse(
        mode=settings.AI_MODE,
        provider="google-genai" if is_gemini else "deterministic-demo",
        model=settings.GEMINI_MODEL,
        api_key_configured=has_key,
    )
