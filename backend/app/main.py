import os

from backend.app.api.v1 import audit, auth, evidence, health, incidents, reports, seed, tasks
from backend.app.api.v1 import settings as settings_api
from backend.app.core.config import settings
from backend.app.core.errors import (
    RequestIdMiddleware,
    SahaayakException,
    global_exception_handler,
    http_exception_handler,
    sahaayak_exception_handler,
    validation_exception_handler,
)
from backend.app.core.limiter import limiter
from backend.app.core.security import CsrfProtectionMiddleware, SecurityHeadersMiddleware
from backend.app.db.session import Base, engine
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

# Ensure local tables exist
Base.metadata.create_all(bind=engine)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Sahaayak AI - AI-assisted community incident intelligence platform during heavy urban rainfall and crises.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Attach slowapi rate limiter to app state
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    req_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down.",
                "details": {"retry_after": getattr(exc, "detail", "60s")},
                "request_id": req_id,
            }
        },
    )


# 1. Request ID Middleware (must be outer so request_id is attached first)
app.add_middleware(RequestIdMiddleware)

# 2. Security Headers Middleware (CSP, X-Content-Type-Options, Frame protection, Referrer)
app.add_middleware(SecurityHeadersMiddleware)

# 3. Double-Submit CSRF Protection Middleware
app.add_middleware(CsrfProtectionMiddleware)

# 4. CORS Middleware with configured allowlist
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# 5. Exception Handlers (Standard Error Envelope, no stack traces leaked)
app.add_exception_handler(SahaayakException, sahaayak_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# 6. Include API Routers (No static /uploads mount: files served ONLY via authorized endpoint)
app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["Health & Readiness"])
app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["Authentication & RBAC"])
app.include_router(reports.router, prefix=settings.API_V1_PREFIX, tags=["Reports"])
app.include_router(incidents.router, prefix=settings.API_V1_PREFIX, tags=["Incidents"])
app.include_router(evidence.router, prefix=settings.API_V1_PREFIX, tags=["Evidence"])
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX, tags=["Tasks"])
app.include_router(audit.router, prefix=settings.API_V1_PREFIX, tags=["Audit"])
app.include_router(seed.router, prefix=settings.API_V1_PREFIX, tags=["Demo Seed"])
app.include_router(settings_api.router, prefix=settings.API_V1_PREFIX, tags=["Settings"])


@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
        "ready": f"{settings.API_V1_PREFIX}/ready",
        "auth": f"{settings.API_V1_PREFIX}/auth/me",
    }
