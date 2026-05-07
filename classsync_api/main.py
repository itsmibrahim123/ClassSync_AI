"""
FastAPI application entry point for ClassSync AI.
"""

import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from classsync_api.config import settings
from classsync_api.database import SessionLocal
from classsync_api.bootstrap import bootstrap_database
from classsync_api.routers import health, datasets, constraints, scheduler, teachers, dashboard


# Create FastAPI app instance
app = FastAPI(
    title=settings.app_name,
    description="AI-assisted university timetabling system",
    version=settings.version,
    debug=settings.debug
)


@app.on_event("startup")
def startup_bootstrap():
    """Bootstrap required database entities on application startup."""
    db = SessionLocal()
    try:
        bootstrap_database(db)
    finally:
        db.close()


# Configure CORS - allow all origins in demo mode for Railway deployment
origins = settings.allowed_origins.split(",")

# In production/demo, we want to allow same-origin requests
# When serving frontend from FastAPI, CORS isn't needed for same-origin
# But we keep it configured for flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(datasets.router, prefix=settings.api_prefix)
app.include_router(constraints.router, prefix=settings.api_prefix)
app.include_router(scheduler.router, prefix=settings.api_prefix)
app.include_router(teachers.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)

@app.get("/")
async def root():
    """Root endpoint - serves React app if built, otherwise API welcome message."""
    # Check if frontend is built
    frontend_index = Path(__file__).parent.parent / "classsync-frontend" / "dist" / "index.html"
    if frontend_index.exists():
        return FileResponse(frontend_index)

    # Fallback to API welcome message if no frontend
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": settings.version,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version
    }


@app.get(f"{settings.api_prefix}/status")
async def api_status():
    """API status endpoint with configuration info (non-sensitive)."""
    return {
        "api_version": settings.version,
        "debug_mode": settings.debug,
        "max_upload_size_mb": settings.max_upload_size_mb,
        "max_optimization_time": settings.max_optimization_time_seconds,
        "database_configured": bool(settings.database_url != "postgresql://user:password@localhost:5432/classsync_db")
    }


# Static file serving for React frontend in production
# The frontend build is expected at classsync-frontend/dist
FRONTEND_DIR = Path(__file__).parent.parent / "classsync-frontend" / "dist"

if FRONTEND_DIR.exists():
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    # Catch-all route for React SPA - must be after all API routes
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve React SPA for all non-API routes."""
        # Don't serve SPA for API routes
        if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json"]:
            return JSONResponse({"detail": "Not found"}, status_code=404)

        # Serve index.html for all other routes (React Router handles client-side routing)
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return JSONResponse({"detail": "Frontend not built"}, status_code=404)


# This will be used for running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "classsync_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )