"""
Health and status check endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from classsync_api.config import settings
from classsync_api.database import get_db

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version
    }


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with system status."""

    # Check database connection
    db_status = "operational"
    db_message = None
    try:
        # Execute simple query to test connection
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        db_message = str(e)

    return {
        "status": "healthy" if db_status == "operational" else "degraded",
        "app": settings.app_name,
        "version": settings.version,
        "components": {
            "api": "operational",
            "database": db_status,
            "database_message": db_message,
            "storage": "pending",   # Will check in Phase 3
            "scheduler": "pending", # Will check in Phase 5
            "ai_agent": "pending"   # Will check in Phase 7
        }
    }