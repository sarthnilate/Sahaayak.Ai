from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.services.ai.adapter import ai_adapter
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
def liveness():
    """
    Liveness probe: verifies that the HTTP server is alive and responding.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "ai_mode": settings.AI_MODE,
        "ai_provider": ai_adapter.provider_mode,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness(db: Session = Depends(get_db)):
    """
    Readiness probe: validates database connectivity and transaction readiness.
    Fails fast with 503 Service Unavailable if database is unreachable.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "dialect": db.bind.dialect.name if db.bind else "unknown",
            "live_sources_enabled": settings.LIVE_SOURCES_ENABLED,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database readiness probe failed: {str(e)}",
        )
