import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import settings
from backend.app.db.session import engine, Base
from backend.app.api.v1 import health, reports, incidents, evidence, tasks, audit, seed

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Sahaayak AI --- AI-assisted community incident-intelligence platform during heavy urban rainfall and crises.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows Vite dev server & test runners
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads static directory for viewing uploaded field images
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include API v1 Routers
app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["Health"])
app.include_router(reports.router, prefix=settings.API_V1_PREFIX, tags=["Reports"])
app.include_router(incidents.router, prefix=settings.API_V1_PREFIX, tags=["Incidents"])
app.include_router(evidence.router, prefix=settings.API_V1_PREFIX, tags=["Evidence"])
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX, tags=["Tasks"])
app.include_router(audit.router, prefix=settings.API_V1_PREFIX, tags=["Audit"])
app.include_router(seed.router, prefix=settings.API_V1_PREFIX, tags=["Demo Seed"])

@app.get("/")
def root():
    return {
        "app": "Sahaayak AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health"
    }
