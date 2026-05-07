"""
Timetable generation and scheduling endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import joinedload

from classsync_api.database import get_db
from classsync_api.dependencies import get_institution_id
from classsync_api.schemas import MessageResponse, TimetableUpdate, GenerateRequest
from classsync_core.models import Timetable, ConstraintConfig, TimetableEntry, Section, Teacher, Room, Course
from classsync_core.optimizer import TimetableOptimizer, ValidationFailedError
from fastapi import Body

from fastapi.responses import FileResponse
import tempfile
import uuid

from classsync_core.exports import ExportManager
from classsync_core.exporters import XLSXExporter, CSVExporter, JSONExporter

router = APIRouter(
    prefix="/scheduler",
    tags=["Scheduler"]
)


def validate_dataset_integrity(db: Session, institution_id: int) -> Dict[str, Any]:
    """
    Validate that all required dataset entities exist and are consistent
    before allowing timetable generation.

    Returns:
        Dict with 'valid' boolean and 'errors' list
    """
    from sqlalchemy import text

    errors = []
    warnings = []

    # 1. Check for active sections with teachers
    try:
        # Check if teachers are assigned via courses
        result = db.execute(text("""
            SELECT s.id, s.code, c.code as course_code, c.teacher_id as course_teacher_id, s.teacher_id as section_teacher_id
            FROM sections s
            JOIN courses c ON s.course_id = c.id
            WHERE s.institution_id = :inst_id AND s.is_deleted = false AND c.is_deleted = false
        """), {"inst_id": institution_id})
        section_rows = result.fetchall()
    except Exception as e:
        print(f"[Validation] Error querying sections: {e}")
        section_rows = []

    if not section_rows:
        errors.append("No active sections found. Please upload a course dataset first.")
    else:
        # Check sections have valid teachers
        sections_without_teachers = []
        for row in section_rows:
            has_teacher = False
            teacher_id_to_check = None

            if hasattr(row, 'section_teacher_id') and row.section_teacher_id:
                 teacher_id_to_check = row.section_teacher_id
            elif hasattr(row, 'course_teacher_id') and row.course_teacher_id:
                teacher_id_to_check = row.course_teacher_id

            if teacher_id_to_check:
                teacher = db.query(Teacher).filter(
                    Teacher.id == teacher_id_to_check,
                    Teacher.is_deleted == False
                ).first()
                has_teacher = teacher is not None

            if not has_teacher:
                course_code = row.course_code if hasattr(row, 'course_code') else 'Unknown'
                sections_without_teachers.append(f"{course_code}-{row.code}")

        if sections_without_teachers:
            if len(sections_without_teachers) > 5:
                errors.append(
                    f"{len(sections_without_teachers)} sections have no valid teacher. "
                    f"Examples: {', '.join(sections_without_teachers[:5])}..."
                )
            else:
                errors.append(
                    f"Sections without valid teachers: {', '.join(sections_without_teachers)}"
                )

    # 2. Check for active rooms
    rooms = db.query(Room).filter(
        Room.institution_id == institution_id,
        Room.is_available == True,
        Room.is_deleted == False
    ).all()

    if not rooms:
        errors.append("No available rooms found. Please upload a room dataset or ensure rooms are marked as available.")
    else:
        # Check for lab rooms if we have lab courses
        lab_sections = db.query(Section).join(Course).filter(
            Section.institution_id == institution_id,
            Section.is_deleted == False,
            Course.is_deleted == False,
            Course.course_type == 'lab'
        ).count()

        lab_rooms = [r for r in rooms if r.room_type and r.room_type.value == 'lab']

        if lab_sections > 0 and not lab_rooms:
            warnings.append(f"No lab rooms available but {lab_sections} lab sections exist. Labs may be assigned to lecture rooms.")

    # 3. Check for active constraint config
    config = db.query(ConstraintConfig).filter(
        ConstraintConfig.institution_id == institution_id,
        ConstraintConfig.is_active == True
    ).first()

    if not config:
        # Check for default config
        default_config = db.query(ConstraintConfig).filter(
            ConstraintConfig.institution_id == institution_id,
            ConstraintConfig.is_default == True
        ).first()

        if not default_config:
            errors.append("No active constraint configuration found. Please configure scheduling constraints.")

    # 4. Check for active courses
    courses = db.query(Course).filter(
        Course.institution_id == institution_id,
        Course.is_deleted == False
    ).count()

    if courses == 0:
        errors.append("No active courses found. Please upload a course dataset.")

    # 5. Check for active teachers
    teachers = db.query(Teacher).filter(
        Teacher.institution_id == institution_id,
        Teacher.is_deleted == False
    ).count()

    if teachers == 0:
        errors.append("No active teachers found. Teachers are derived from the course dataset - please ensure the dataset includes instructor information.")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'stats': {
            'sections': len(section_rows) if section_rows else 0,
            'rooms': len(rooms) if rooms else 0,
            'courses': courses,
            'teachers': teachers
        }
    }


@router.post("/generate")
async def generate_timetable(
        request: GenerateRequest = Body(default=GenerateRequest()),
        db: Session = Depends(get_db),
        institution_id: str = Depends(get_institution_id)
):
    """
    Generate an optimized timetable using genetic algorithm.

    Args:
        request: Generation configuration including:
            - constraint_config_id: Which constraint profile to use
            - teacher_constraints: List of teacher availability constraints
            - room_constraints: List of room availability constraints
            - locked_assignments: Pre-scheduled sessions to respect
            - population_size: GA population size (10-100)
            - generations: Number of GA generations (50-300)
            - target_fitness: Target fitness score (50-100)
    """
    # Pre-generation validation - ensure dataset integrity
    validation = validate_dataset_integrity(db, 1)  # institution_id = 1

    if not validation['valid']:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Dataset integrity validation failed",
                "validation_errors": validation['errors'],
                "warnings": validation['warnings'],
                "stats": validation['stats'],
                "help": "Please ensure your dataset is properly uploaded before generating a timetable. "
                        "Teachers, courses, and sections must all be derived from the current dataset."
            }
        )

    # Log warnings if any
    if validation['warnings']:
        print(f"[Scheduler] Generation warnings: {validation['warnings']}")

    # Get constraint config
    if request.constraint_config_id:
        config = db.query(ConstraintConfig).get(request.constraint_config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Constraint config not found")
    else:
        # Use default config
        config = db.query(ConstraintConfig).filter(
            ConstraintConfig.institution_id == 1,
            ConstraintConfig.is_default == True
        ).first()

        if not config:
            raise HTTPException(status_code=404, detail="No default constraint config found")

    # Initialize optimizer
    optimizer = TimetableOptimizer(config)

    # Convert constraints to dict format for the optimizer
    teacher_constraints = [tc.model_dump() for tc in request.teacher_constraints]
    room_constraints = [rc.model_dump() for rc in request.room_constraints]
    locked_assignments = [la.model_dump() for la in request.locked_assignments]

    # Generate timetable
    try:
        result = optimizer.generate_timetable(
            db=db,
            institution_id=1,
            population_size=request.population_size,
            generations=request.generations,
            teacher_constraints=teacher_constraints,
            room_constraints=room_constraints,
            locked_assignments=locked_assignments,
            random_seed=request.random_seed
        )

        return {
            "message": "Timetable generated successfully",
            "timetable_id": result['timetable_id'],
            "generation_time": result['generation_time'],
            "sessions_scheduled": result['sessions_scheduled'],
            "sessions_total": result['sessions_total'],
            "fitness_score": result['fitness_score'],
            "is_feasible": result.get('is_feasible', True),
            "strategy": result.get('strategy', 'ga'),

            # Constraint application summary
            "constraints_applied": {
                "teacher_constraints": len(teacher_constraints),
                "room_constraints": len(room_constraints),
                "locked_assignments": len(locked_assignments)
            },

            # Explainable output - detailed constraint analysis
            "explanation": result.get('explanation', {}),

            # Legacy fields for backwards compatibility
            "hard_violations": result.get('hard_violations'),
            "soft_scores": result.get('soft_scores')
        }

    except ValidationFailedError as e:
        # Return validation errors with 422 status
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Pre-generation validation failed",
                "validation_errors": e.validation_result.to_dict()
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/validate")
async def validate_generation_readiness(
        db: Session = Depends(get_db),
        institution_id: str = Depends(get_institution_id)
):
    """
    Validate that the system is ready for timetable generation.

    Checks:
    - Active sections with teachers exist
    - Rooms are available
    - Constraint configuration exists
    - All data is derived from current dataset

    Returns:
        Validation result with errors, warnings, and statistics
    """
    validation = validate_dataset_integrity(db, 1)  # institution_id = 1

    return {
        "ready": validation['valid'],
        "errors": validation['errors'],
        "warnings": validation['warnings'],
        "statistics": validation['stats'],
        "message": "Ready for timetable generation" if validation['valid'] else "Dataset validation failed - please fix errors before generating"
    }


@router.get("/debug/database-state")
async def debug_database_state(
        db: Session = Depends(get_db),
        institution_id: str = Depends(get_institution_id)
):
    """
    DEBUG ENDPOINT: Check current state of teachers, courses, and sections in database.

    Shows both active and soft-deleted records to diagnose data persistence issues.
    """
    from sqlalchemy import text

    # Get all teachers (both active and deleted)
    all_teachers = db.execute(text("""
        SELECT id, name, code, is_deleted, created_at, deleted_at
        FROM teachers
        WHERE institution_id = 1
        ORDER BY is_deleted, created_at DESC
    """)).fetchall()

    # Get active teachers only
    active_teachers = [t for t in all_teachers if not t.is_deleted]
    deleted_teachers = [t for t in all_teachers if t.is_deleted]

    # Get all courses
    all_courses = db.execute(text("""
        SELECT id, code, name, is_deleted, created_at
        FROM courses
        WHERE institution_id = 1
        ORDER BY is_deleted, created_at DESC
    """)).fetchall()

    active_courses = [c for c in all_courses if not c.is_deleted]
    deleted_courses = [c for c in all_courses if c.is_deleted]

    # Get all sections
    all_sections = db.execute(text("""
        SELECT id, code, course_id, is_deleted, created_at
        FROM sections
        WHERE institution_id = 1
        ORDER BY is_deleted, created_at DESC
    """)).fetchall()

    active_sections = [s for s in all_sections if not s.is_deleted]
    deleted_sections = [s for s in all_sections if s.is_deleted]

    # Get datasets
    datasets = db.execute(text("""
        SELECT id, filename, status, created_at, s3_key
        FROM datasets
        WHERE institution_id = 1
        ORDER BY created_at DESC
        LIMIT 10
    """)).fetchall()

    return {
        "summary": {
            "active_teachers": len(active_teachers),
            "deleted_teachers": len(deleted_teachers),
            "active_courses": len(active_courses),
            "deleted_courses": len(deleted_courses),
            "active_sections": len(active_sections),
            "deleted_sections": len(deleted_sections),
            "total_datasets": len(datasets)
        },
        "active_teachers": [
            {"id": t.id, "name": t.name, "code": t.code, "created_at": str(t.created_at)}
            for t in active_teachers[:20]  # Limit to 20
        ],
        "deleted_teachers_sample": [
            {"id": t.id, "name": t.name, "code": t.code, "deleted_at": str(t.deleted_at)}
            for t in deleted_teachers[:10]  # Sample of 10
        ],
        "active_courses_sample": [
            {"id": c.id, "code": c.code, "name": c.name}
            for c in active_courses[:10]
        ],
        "recent_datasets": [
            {"id": d.id, "filename": d.filename, "status": d.status, "created_at": str(d.created_at)}
            for d in datasets
        ],
        "diagnosis": {
            "issue_detected": len(deleted_teachers) > 0 and len(active_teachers) > 0,
            "message": (
                f"Found {len(active_teachers)} active teachers and {len(deleted_teachers)} deleted teachers. "
                f"If active teachers are from an OLD dataset, the clear_data() may not be working properly."
            )
        }
    }


@router.get("/debug/diagnostics/download")
async def download_diagnostics(
        db: Session = Depends(get_db),
        institution_id: str = Depends(get_institution_id)
):
    """
    Download a comprehensive diagnostics report as a text file.
    Includes database stats, recent activity, and system health.
    """
    import io
    from fastapi.responses import StreamingResponse

    # Reuse debug logic to get stats
    state = await debug_database_state(db, institution_id)
    
    # Get recent timetables for performance stats
    timetables = db.query(Timetable).filter(
        Timetable.institution_id == 1
    ).order_by(Timetable.created_at.desc()).limit(5).all()

    # Build report
    report = []
    report.append("=" * 50)
    report.append(f"CLASSSYNC AI - SYSTEM DIAGNOSTICS REPORT")
    report.append(f"Generated: {datetime.utcnow().isoformat()}")
    report.append("=" * 50)
    report.append("\n[DATABASE STATE]")
    report.append(f"Active Teachers: {state['summary']['active_teachers']}")
    report.append(f"Active Courses: {state['summary']['active_courses']}")
    report.append(f"Active Sections: {state['summary']['active_sections']}")
    report.append(f"Total Datasets: {state['summary']['total_datasets']}")
    
    if state['diagnosis']['issue_detected']:
        report.append("\n[WARNINGS]")
        report.append(f"Issue Detected: {state['diagnosis']['message']}")

    report.append("\n[RECENT TIMETABLES]")
    if timetables:
        for t in timetables:
            report.append(f"- ID {t.id} ({t.created_at}): Score {t.constraint_score}, Time {t.generation_time_seconds}s, Status {t.status}")
    else:
        report.append("No timetables generated yet.")

    report.append("\n[RECENT DATASETS]")
    for d in state['recent_datasets']:
        report.append(f"- {d['filename']} ({d['status']}) - {d['created_at']}")

    # Create file stream
    content = "\n".join(report)
    stream = io.BytesIO(content.encode('utf-8'))
    
    return StreamingResponse(
        stream,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=classsync_diagnostics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"}
    )


@router.delete("/debug/hard-reset")
async def hard_reset_all_data(
        confirm: bool = False,
        db: Session = Depends(get_db),
        institution_id: str = Depends(get_institution_id)
):
    """
    DANGER: Hard delete ALL teachers, courses, sections, and timetable entries.

    This completely removes all data (not soft-delete) to allow a fresh start.
    Use this when soft-deleted data is causing issues.

    Args:
        confirm: Must be True to execute the reset
    """
    if not confirm:
        return {
            "warning": "This will PERMANENTLY DELETE all teachers, courses, sections, and timetable entries!",
            "instruction": "Add ?confirm=true to the URL to proceed",
            "affected": "All data for institution_id=1 will be deleted"
        }

    from sqlalchemy import text

    try:
        # Delete in correct order (children first, then parents)
        # 1. Delete timetable entries first
        entries_deleted = db.execute(text("DELETE FROM timetable_entries WHERE timetable_id IN (SELECT id FROM timetables WHERE institution_id = 1)"))

        # 2. Delete timetables
        timetables_deleted = db.execute(text("DELETE FROM timetables WHERE institution_id = 1"))

        # 3. Delete sections (reference courses)
        sections_deleted = db.execute(text("DELETE FROM sections WHERE institution_id = 1"))

        # 4. Delete courses (reference teachers)
        courses_deleted = db.execute(text("DELETE FROM courses WHERE institution_id = 1"))

        # 5. Delete teachers
        teachers_deleted = db.execute(text("DELETE FROM teachers WHERE institution_id = 1"))

        db.commit()

        return {
            "success": True,
            "message": "All data has been permanently deleted",
            "deleted": {
                "timetable_entries": entries_deleted.rowcount,
                "timetables": timetables_deleted.rowcount,
                "sections": sections_deleted.rowcount,
                "courses": courses_deleted.rowcount,
                "teachers": teachers_deleted.rowcount
            },
            "next_steps": [
                "Upload a new course dataset via /api/v1/datasets/upload",
                "The new dataset will be the SINGLE source of truth for teachers"
            ]
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Hard reset failed: {str(e)}")


@router.get("/timetables")
async def list_timetables(
    limit: int = 100,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """List all generated timetables for the institution."""

    timetables = db.query(Timetable).filter(
        Timetable.institution_id == 1
    ).order_by(Timetable.created_at.desc()).limit(limit).all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "semester": t.semester,
            "year": t.year,
            "status": t.status,
            "generation_time_seconds": t.generation_time_seconds,
            "constraint_score": t.constraint_score,
            "conflict_count": t.conflict_count,
            "created_at": t.created_at
        }
        for t in timetables
    ]


@router.get("/timetables/{timetable_id}")
async def get_timetable(
        timetable_id: int,
        db: Session = Depends(get_db),
        institution_id: str = Depends(get_institution_id)
):
    """Get a specific timetable with all entries."""
    timetable = db.query(Timetable).filter(
        Timetable.id == timetable_id,
        Timetable.institution_id == 1
    ).first()

    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")

    # Load entries with relationships
    entries = db.query(TimetableEntry).filter(
        TimetableEntry.timetable_id == timetable_id
    ).options(
        joinedload(TimetableEntry.course),
        joinedload(TimetableEntry.teacher),
        joinedload(TimetableEntry.room),
        joinedload(TimetableEntry.section)
    ).all()

    # Convert to dict with relationships
    timetable_dict = {
        "id": timetable.id,
        "name": timetable.name,
        "semester": timetable.semester,
        "year": timetable.year,
        "status": timetable.status,
        "generation_time_seconds": timetable.generation_time_seconds,
        "constraint_score": timetable.constraint_score,
        "conflict_count": timetable.conflict_count,
        "created_at": timetable.created_at.isoformat(),
        "entries": [
            {
                "id": entry.id,
                "day_of_week": entry.day_of_week,
                "start_time": entry.start_time,
                "end_time": entry.end_time,
                "course": {
                    "id": entry.course.id,
                    "name": entry.course.name,
                    "code": entry.course.code
                } if entry.course else None,
                "teacher": {
                    "id": entry.teacher.id,
                    "name": entry.teacher.name
                } if entry.teacher else None,
                "room": {
                    "id": entry.room.id,
                    "code": entry.room.code,
                    "name": entry.room.name
                } if entry.room else None,
                "section": {
                    "id": entry.section.id,
                    "code": entry.section.code,
                    "name": entry.section.name
                } if entry.section else None
            }
            for entry in entries
        ]
    }

    return timetable_dict


@router.delete("/timetables/{timetable_id}", response_model=MessageResponse)
async def delete_timetable(
    timetable_id: int,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """Delete a generated timetable."""

    timetable = db.query(Timetable).filter(
        Timetable.id == timetable_id,
        Timetable.institution_id == 1
    ).first()

    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")

    db.delete(timetable)  # Cascade will delete entries
    db.commit()

    return MessageResponse(
        message="Timetable deleted successfully",
        details={"timetable_id": timetable_id}
    )


@router.patch("/timetables/{timetable_id}", response_model=MessageResponse)
async def update_timetable(
    timetable_id: int,
    update_data: TimetableUpdate,
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """Update a generated timetable."""
    
    timetable = db.query(Timetable).filter(
        Timetable.id == timetable_id,
        Timetable.institution_id == 1
    ).first()

    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")

    timetable.name = update_data.name
    db.commit()

    return MessageResponse(
        message="Timetable updated successfully",
        details={"timetable_id": timetable_id, "name": timetable.name}
    )


@router.get("/timetables/{timetable_id}/export")
async def export_timetable(
        timetable_id: int,
        format: str = "xlsx",
        view_type: str = "master",
        db: Session = Depends(get_db),
        institution_id: str = Depends(get_institution_id)
):
    """
    Export timetable in specified format.

    Args:
        timetable_id: ID of timetable to export
        format: Export format (xlsx, csv, json)
        view_type: View type (master, section, teacher, room)

    Returns:
        File download
    """
    # Verify timetable exists and belongs to institution
    timetable = db.query(Timetable).filter(
        Timetable.id == timetable_id,
        Timetable.institution_id == 1
    ).first()

    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")

    # Validate format
    if format not in ['xlsx', 'csv', 'json']:
        raise HTTPException(status_code=400, detail="Invalid format. Use: xlsx, csv, or json")

    # Validate view_type
    if view_type not in ['master', 'section', 'teacher', 'room', 'program', 'free_slots']:
        raise HTTPException(status_code=400, detail="Invalid view_type. Use: master, section, teacher, room, program, or free_slots")

    # Create export manager
    export_manager = ExportManager(db)
    export_manager.register_exporter('xlsx', XLSXExporter(db))
    export_manager.register_exporter('csv', CSVExporter(db))
    export_manager.register_exporter('json', JSONExporter(db))

    # Create temporary file
    temp_dir = tempfile.gettempdir()
    file_id = str(uuid.uuid4())

    # Set file extension and media type
    extensions = {'xlsx': 'xlsx', 'csv': 'csv', 'json': 'json'}
    media_types = {
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'csv': 'text/csv',
        'json': 'application/json'
    }

    file_name = f"timetable_{timetable_id}_{view_type}_{file_id}.{extensions[format]}"
    output_path = f"{temp_dir}/{file_name}"

    try:
        # Export
        exported_path = export_manager.export_timetable(
            timetable_id=timetable_id,
            format=format,
            output_path=output_path,
            view_type=view_type
        )

        # For CSV with view_type (multiple files), return first file or zip
        if format == 'csv' and view_type != 'master':
            # Returns directory path - we'll just return info for now
            return {
                "message": "Export completed",
                "format": format,
                "view_type": view_type,
                "path": exported_path,
                "note": "Multiple CSV files generated. Use individual file download."
            }

        # Return file
        return FileResponse(
            path=exported_path,
            media_type=media_types[format],
            filename=file_name,
            headers={
                "Content-Disposition": f"attachment; filename={file_name}"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/timetables/{timetable_id}/export/formats")
async def get_available_export_formats(
        timetable_id: int,
        db: Session = Depends(get_db),
        institution_id: str = Depends(get_institution_id)
):
    """
    Get available export formats for a timetable.

    Returns:
        List of available formats and view types
    """
    # Verify timetable exists
    timetable = db.query(Timetable).filter(
        Timetable.id == timetable_id,
        Timetable.institution_id == 1
    ).first()

    if not timetable:
        raise HTTPException(status_code=404, detail="Timetable not found")

    return {
        "timetable_id": timetable_id,
        "available_formats": [
            {
                "format": "xlsx",
                "description": "Excel format with styling",
                "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
            {
                "format": "csv",
                "description": "Comma-separated values",
                "media_type": "text/csv"
            },
            {
                "format": "json",
                "description": "JSON format for APIs",
                "media_type": "application/json"
            }
        ],
        "available_views": [
            {
                "view_type": "master",
                "description": "Complete timetable in single file"
            },
            {
                "view_type": "section",
                "description": "Separate sheet/file for each section"
            },
            {
                "view_type": "teacher",
                "description": "Separate sheet/file for each teacher"
            },
            {
                "view_type": "room",
                "description": "Separate sheet/file for each room"
            },
            {
                "view_type": "program",
                "description": "Separate sheet/file for each program"
            },
            {
                "view_type": "free_slots",
                "description": "List of all unallocated time slots"
            }
        ]
    }