"""
Teachers API endpoints for listing and retrieving teachers.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from classsync_api.database import get_db
from classsync_api.dependencies import get_institution_id
from classsync_core.models import Teacher

router = APIRouter(
    prefix="/teachers",
    tags=["Teachers"]
)


@router.get("/")
async def list_teachers(
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
) -> List[Dict[str, Any]]:
    """
    List all teachers for the institution.

    Returns:
        List of teachers with their details and time preferences.
    """
    teachers = db.query(Teacher).filter(
        Teacher.institution_id == 1,
        Teacher.is_deleted == False
    ).order_by(Teacher.name).all()

    return [
        {
            "id": t.id,
            "code": t.code,
            "name": t.name,
            "email": t.email,
            "department": t.department,
            "time_preferences": t.time_preferences,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in teachers
    ]


@router.get("/{teacher_id}")
async def get_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
) -> Dict[str, Any]:
    """
    Get a specific teacher by ID.

    Args:
        teacher_id: The ID of the teacher to retrieve.

    Returns:
        Teacher details including time preferences.
    """
    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id,
        Teacher.institution_id == 1,
        Teacher.is_deleted == False
    ).first()

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    return {
        "id": teacher.id,
        "code": teacher.code,
        "name": teacher.name,
        "email": teacher.email,
        "department": teacher.department,
        "time_preferences": teacher.time_preferences,
        "created_at": teacher.created_at.isoformat() if teacher.created_at else None,
        "updated_at": teacher.updated_at.isoformat() if teacher.updated_at else None
    }


@router.patch("/{teacher_id}/preferences")
async def update_teacher_preferences(
    teacher_id: int,
    preferences: Dict[str, Any],
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
) -> Dict[str, Any]:
    """
    Update a teacher's time preferences.

    Args:
        teacher_id: The ID of the teacher to update.
        preferences: New time preferences to set.

    Returns:
        Updated teacher details.
    """
    teacher = db.query(Teacher).filter(
        Teacher.id == teacher_id,
        Teacher.institution_id == 1,
        Teacher.is_deleted == False
    ).first()

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    teacher.time_preferences = preferences
    db.commit()
    db.refresh(teacher)

    return {
        "id": teacher.id,
        "code": teacher.code,
        "name": teacher.name,
        "email": teacher.email,
        "department": teacher.department,
        "time_preferences": teacher.time_preferences,
        "message": "Preferences updated successfully"
    }
