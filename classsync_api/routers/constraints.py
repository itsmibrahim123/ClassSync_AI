"""
Constraint configuration endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from classsync_api.database import get_db
from classsync_api.dependencies import get_institution_id, get_current_user
from classsync_api.schemas import (
    ConstraintConfigCreate, ConstraintConfigUpdate,
    ConstraintConfigResponse, ConstraintConfigListItem,
    MessageResponse,
    TeacherConstraintProfileCreate, TeacherConstraintProfileUpdate,
    TeacherConstraintProfileResponse, TeacherConstraintProfileSummary
)
from classsync_core.models import ConstraintConfig, TeacherConstraintProfile, TeacherConstraintItem

router = APIRouter(
    prefix="/constraints",
    tags=["Constraints"]
)


# ============================================================================
# TEACHER CONSTRAINT PROFILES
# ============================================================================

@router.get("/teacher-profiles", response_model=List[TeacherConstraintProfileSummary])
async def list_teacher_profiles(
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """List all teacher constraint profiles."""
    profiles = db.query(TeacherConstraintProfile).filter(
        TeacherConstraintProfile.institution_id == 1
    ).order_by(TeacherConstraintProfile.is_default.desc(), TeacherConstraintProfile.created_at.desc()).all()

    return [
        TeacherConstraintProfileSummary(
            id=p.id,
            institution_id=p.institution_id,
            name=p.name,
            description=p.description,
            is_default=p.is_default,
            created_at=p.created_at,
            updated_at=p.updated_at,
            item_count=len(p.items)
        )
        for p in profiles
    ]

@router.post("/teacher-profiles", response_model=TeacherConstraintProfileResponse)
async def create_teacher_profile(
    profile_data: TeacherConstraintProfileCreate,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """Create a new teacher constraint profile."""
    # Handle default toggle
    if profile_data.is_default:
        db.query(TeacherConstraintProfile).filter(
            TeacherConstraintProfile.institution_id == 1,
            TeacherConstraintProfile.is_default == True
        ).update({"is_default": False})

    # Create profile
    profile = TeacherConstraintProfile(
        institution_id=1,
        name=profile_data.name,
        description=profile_data.description,
        is_default=profile_data.is_default
    )
    db.add(profile)
    db.flush() # Get ID

    # Create items
    for item in profile_data.items:
        db_item = TeacherConstraintItem(
            profile_id=profile.id,
            teacher_id=item.teacher_id,
            day=item.day,
            start_time=item.start_time,
            end_time=item.end_time,
            constraint_type=item.constraint_type,
            priority=item.priority
        )
        db.add(db_item)

    db.commit()
    db.refresh(profile)
    return profile

@router.get("/teacher-profiles/{profile_id}", response_model=TeacherConstraintProfileResponse)
async def get_teacher_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """Get full details of a teacher constraint profile."""
    profile = db.query(TeacherConstraintProfile).filter(
        TeacherConstraintProfile.id == profile_id,
        TeacherConstraintProfile.institution_id == 1
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return profile

@router.put("/teacher-profiles/{profile_id}", response_model=TeacherConstraintProfileResponse)
async def update_teacher_profile(
    profile_id: int,
    profile_data: TeacherConstraintProfileUpdate,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """Update a teacher constraint profile."""
    profile = db.query(TeacherConstraintProfile).filter(
        TeacherConstraintProfile.id == profile_id,
        TeacherConstraintProfile.institution_id == 1
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Update metadata
    if profile_data.name is not None:
        profile.name = profile_data.name
    if profile_data.description is not None:
        profile.description = profile_data.description
    
    # Handle default toggle
    if profile_data.is_default is not None:
        if profile_data.is_default and not profile.is_default:
            db.query(TeacherConstraintProfile).filter(
                TeacherConstraintProfile.institution_id == 1,
                TeacherConstraintProfile.is_default == True
            ).update({"is_default": False})
        profile.is_default = profile_data.is_default

    # Replace items if provided
    if profile_data.items is not None:
        # Delete existing items
        db.query(TeacherConstraintItem).filter(TeacherConstraintItem.profile_id == profile.id).delete()
        
        # Add new items
        for item in profile_data.items:
            db_item = TeacherConstraintItem(
                profile_id=profile.id,
                teacher_id=item.teacher_id,
                day=item.day,
                start_time=item.start_time,
                end_time=item.end_time,
                constraint_type=item.constraint_type,
                priority=item.priority
            )
            db.add(db_item)

    db.commit()
    db.refresh(profile)
    return profile

@router.delete("/teacher-profiles/{profile_id}", response_model=MessageResponse)
async def delete_teacher_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """Delete a teacher constraint profile."""
    profile = db.query(TeacherConstraintProfile).filter(
        TeacherConstraintProfile.id == profile_id,
        TeacherConstraintProfile.institution_id == 1
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(profile)
    db.commit()
    return MessageResponse(message="Profile deleted successfully", details={"id": profile_id})

@router.post("/teacher-profiles/{profile_id}/set-default", response_model=MessageResponse)
async def set_default_teacher_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """Set a profile as default."""
    profile = db.query(TeacherConstraintProfile).filter(
        TeacherConstraintProfile.id == profile_id,
        TeacherConstraintProfile.institution_id == 1
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Unset others
    db.query(TeacherConstraintProfile).filter(
        TeacherConstraintProfile.institution_id == 1,
        TeacherConstraintProfile.is_default == True
    ).update({"is_default": False})

    profile.is_default = True
    db.commit()
    
    return MessageResponse(message=f"Profile '{profile.name}' set as default", details={"id": profile_id})


# ============================================================================
# CONSTRAINT CONFIGURATIONS (GLOBAL)
# ============================================================================

@router.get("/configs", response_model=List[ConstraintConfigListItem])
async def list_constraint_configs(
    include_inactive: bool = Query(False, description="Include inactive configurations"),
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    List all constraint configurations for the institution.
    """
    query = db.query(ConstraintConfig).filter(
        ConstraintConfig.institution_id == 1  # TODO: Use actual institution_id in Phase 9
    )

    if not include_inactive:
        query = query.filter(ConstraintConfig.is_active == True)

    configs = query.order_by(ConstraintConfig.is_default.desc(), ConstraintConfig.created_at.desc()).all()

    return [
        ConstraintConfigListItem(
            id=config.id,
            name=config.name,
            is_active=config.is_active,
            is_default=config.is_default,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        for config in configs
    ]


@router.get("/configs/default", response_model=ConstraintConfigResponse)
async def get_default_constraint_config(
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    Get the default constraint configuration for the institution.
    If none exists, create one with default values.
    """
    config = db.query(ConstraintConfig).filter(
        ConstraintConfig.institution_id == 1,  # TODO: Use actual institution_id in Phase 9
        ConstraintConfig.is_default == True
    ).first()

    # If no default exists, create one
    if not config:
        config = ConstraintConfig(
            institution_id=1,
            name="Default Configuration",
            is_active=True,
            is_default=True
        )
        db.add(config)
        db.commit()
        db.refresh(config)

    return ConstraintConfigResponse(
        id=config.id,
        institution_id=config.institution_id,
        name=config.name,
        is_active=config.is_active,
        is_default=config.is_default,
        timeslot_duration_minutes=config.timeslot_duration_minutes,
        days_per_week=config.days_per_week,
        start_time=config.start_time,
        end_time=config.end_time,
        hard_constraints=config.hard_constraints,
        soft_constraints=config.soft_constraints,
        optional_constraints=config.optional_constraints,
        max_optimization_time_seconds=config.max_optimization_time_seconds,
        min_acceptable_score=config.min_acceptable_score,
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@router.get("/configs/{config_id}", response_model=ConstraintConfigResponse)
async def get_constraint_config(
    config_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    Get a specific constraint configuration by ID.
    """
    config = db.query(ConstraintConfig).filter(
        ConstraintConfig.id == config_id,
        ConstraintConfig.institution_id == 1  # TODO: Use actual institution_id in Phase 9
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Constraint configuration not found")

    return ConstraintConfigResponse(
        id=config.id,
        institution_id=config.institution_id,
        name=config.name,
        is_active=config.is_active,
        is_default=config.is_default,
        timeslot_duration_minutes=config.timeslot_duration_minutes,
        days_per_week=config.days_per_week,
        start_time=config.start_time,
        end_time=config.end_time,
        hard_constraints=config.hard_constraints,
        soft_constraints=config.soft_constraints,
        optional_constraints=config.optional_constraints,
        max_optimization_time_seconds=config.max_optimization_time_seconds,
        min_acceptable_score=config.min_acceptable_score,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.post("/configs", response_model=ConstraintConfigResponse, status_code=201)
async def create_constraint_config(
    config_data: ConstraintConfigCreate,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    Create a new constraint configuration.
    """
    # If this is set as default, unset other defaults
    if config_data.is_default:
        db.query(ConstraintConfig).filter(
            ConstraintConfig.institution_id == 1,
            ConstraintConfig.is_default == True
        ).update({"is_default": False})

    # Create new config - build dict dynamically to use database defaults
    config_dict = {
        "institution_id": 1,  # TODO: Use actual institution_id in Phase 9
        "name": config_data.name,
        "is_active": True,
        "is_default": config_data.is_default,
        "timeslot_duration_minutes": config_data.timeslot_duration_minutes,
        "days_per_week": config_data.days_per_week,
        "start_time": config_data.start_time,
        "end_time": config_data.end_time,
        "max_optimization_time_seconds": config_data.max_optimization_time_seconds,
        "min_acceptable_score": config_data.min_acceptable_score
    }

    # Only set constraints if provided (otherwise use database defaults)
    if config_data.hard_constraints:
        config_dict["hard_constraints"] = config_data.hard_constraints.model_dump()
    if config_data.soft_constraints:
        config_dict["soft_constraints"] = config_data.soft_constraints.model_dump()
    if config_data.optional_constraints:
        config_dict["optional_constraints"] = config_data.optional_constraints.model_dump()

    config = ConstraintConfig(**config_dict)

    db.add(config)
    db.commit()
    db.refresh(config)

    return ConstraintConfigResponse(
        id=config.id,
        institution_id=config.institution_id,
        name=config.name,
        is_active=config.is_active,
        is_default=config.is_default,
        timeslot_duration_minutes=config.timeslot_duration_minutes,
        days_per_week=config.days_per_week,
        start_time=config.start_time,
        end_time=config.end_time,
        hard_constraints=config.hard_constraints,
        soft_constraints=config.soft_constraints,
        optional_constraints=config.optional_constraints,
        max_optimization_time_seconds=config.max_optimization_time_seconds,
        min_acceptable_score=config.min_acceptable_score,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.put("/configs/{config_id}", response_model=ConstraintConfigResponse)
async def update_constraint_config(
    config_id: int,
    config_data: ConstraintConfigUpdate,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    Update an existing constraint configuration.
    """
    config = db.query(ConstraintConfig).filter(
        ConstraintConfig.id == config_id,
        ConstraintConfig.institution_id == 1  # TODO: Use actual institution_id in Phase 9
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Constraint configuration not found")

    # If setting as default, unset other defaults
    if config_data.is_default and not config.is_default:
        db.query(ConstraintConfig).filter(
            ConstraintConfig.institution_id == 1,
            ConstraintConfig.is_default == True,
            ConstraintConfig.id != config_id
        ).update({"is_default": False})

    # Update fields
    update_data = config_data.model_dump(exclude_unset=True)

    # Convert Pydantic models to dicts for JSON fields
    if 'hard_constraints' in update_data and update_data['hard_constraints']:
        update_data['hard_constraints'] = config_data.hard_constraints.model_dump()
    if 'soft_constraints' in update_data and update_data['soft_constraints']:
        update_data['soft_constraints'] = config_data.soft_constraints.model_dump()
    if 'optional_constraints' in update_data and update_data['optional_constraints']:
        update_data['optional_constraints'] = config_data.optional_constraints.model_dump()

    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)

    return ConstraintConfigResponse(
        id=config.id,
        institution_id=config.institution_id,
        name=config.name,
        is_active=config.is_active,
        is_default=config.is_default,
        timeslot_duration_minutes=config.timeslot_duration_minutes,
        days_per_week=config.days_per_week,
        start_time=config.start_time,
        end_time=config.end_time,
        hard_constraints=config.hard_constraints,
        soft_constraints=config.soft_constraints,
        optional_constraints=config.optional_constraints,
        max_optimization_time_seconds=config.max_optimization_time_seconds,
        min_acceptable_score=config.min_acceptable_score,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.delete("/configs/{config_id}", response_model=MessageResponse)
async def delete_constraint_config(
    config_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    Delete a constraint configuration.
    Cannot delete the default configuration.
    """
    config = db.query(ConstraintConfig).filter(
        ConstraintConfig.id == config_id,
        ConstraintConfig.institution_id == 1  # TODO: Use actual institution_id in Phase 9
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Constraint configuration not found")

    if config.is_default:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the default configuration. Set another configuration as default first."
        )

    db.delete(config)
    db.commit()

    return MessageResponse(
        message="Constraint configuration deleted successfully",
        details={"config_id": config_id, "name": config.name}
    )


@router.post("/configs/{config_id}/set-default", response_model=MessageResponse)
async def set_default_config(
    config_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    Set a configuration as the default for the institution.
    """
    config = db.query(ConstraintConfig).filter(
        ConstraintConfig.id == config_id,
        ConstraintConfig.institution_id == 1  # TODO: Use actual institution_id in Phase 9
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Constraint configuration not found")

    # Unset all other defaults
    db.query(ConstraintConfig).filter(
        ConstraintConfig.institution_id == 1,
        ConstraintConfig.is_default == True
    ).update({"is_default": False})

    # Set this one as default
    config.is_default = True
    db.commit()

    return MessageResponse(
        message=f"Configuration '{config.name}' set as default",
        details={"config_id": config_id}
    )