"""
Dependency injection for FastAPI endpoints.
Provides reusable dependencies like database sessions, auth, etc.
"""

from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from classsync_api.database import get_db  # Import from database.py
from classsync_api.config import settings


# Database session dependency is now imported from database.py
# Use: db: Session = Depends(get_db)


# API Key validation (basic version)
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """
    Verify API key from request headers.
    This is a placeholder - we'll implement JWT auth in Phase 9.
    """
    # For now, we'll allow all requests
    # TODO: Implement proper JWT authentication in Phase 9
    return True


# User authentication dependency (placeholder)
async def get_current_user(token: Optional[str] = Header(None, alias="Authorization")):
    """
    Get current authenticated user from JWT token.
    This is a placeholder - we'll implement in Phase 9.
    """
    # TODO: Implement JWT token validation in Phase 9
    # For now, return a mock user
    return {
        "user_id": "dev_user",
        "institution_id": "1",
        "role": "admin"
    }


# Institution ID dependency
async def get_institution_id(current_user: dict = Depends(get_current_user)) -> str:
    """
    Extract institution_id from current user for multi-tenancy.
    This is a placeholder - we'll implement properly in Phase 9.
    """
    if current_user:
        return current_user.get("institution_id", "1")
    return "1"