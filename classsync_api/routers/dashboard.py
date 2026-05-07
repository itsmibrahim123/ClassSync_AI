from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from classsync_api.database import get_db
from classsync_api.dependencies import get_institution_id
from classsync_core.models import Timetable, Dataset, TimetableStatus

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    institution_id: str = Depends(get_institution_id)
):
    """
    Get aggregated statistics for the dashboard.
    """
    # 1. Total Timetables
    total_timetables = db.query(Timetable).filter(
        Timetable.institution_id == int(institution_id)
    ).count()

    # 2. Total Datasets
    total_datasets = db.query(Dataset).filter(
        Dataset.institution_id == int(institution_id)
    ).count()

    # 3. Active Schedules (Completed)
    active_schedules = db.query(Timetable).filter(
        Timetable.institution_id == int(institution_id),
        Timetable.status == TimetableStatus.COMPLETED
    ).count()

    # 4. Avg Generation Time (for completed only)
    avg_gen_time = db.query(func.avg(Timetable.generation_time_seconds)).filter(
        Timetable.institution_id == int(institution_id),
        Timetable.status == TimetableStatus.COMPLETED
    ).scalar() or 0.0

    # 5. Status Distribution
    status_counts = {
        "completed": active_schedules,
        "failed": db.query(Timetable).filter(
            Timetable.institution_id == int(institution_id),
            Timetable.status == TimetableStatus.FAILED
        ).count(),
        "pending": db.query(Timetable).filter(
            Timetable.institution_id == int(institution_id),
            Timetable.status.in_([TimetableStatus.PENDING, TimetableStatus.GENERATING])
        ).count()
    }

    return {
        "total_timetables": total_timetables,
        "total_datasets": total_datasets,
        "active_schedules": active_schedules,
        "avg_generation_time": round(avg_gen_time, 1),
        "status_distribution": status_counts
    }
