"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field, EmailStr, validator, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS (matching database enums)
# ============================================================================

class UserRoleSchema(str, Enum):
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    VIEWER = "viewer"


class DatasetStatusSchema(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    INVALID = "invalid"
    PROCESSING = "processing"


class DatasetTypeSchema(str, Enum):
    COURSES = "courses"
    TEACHERS = "teachers"
    ROOMS = "rooms"
    SECTIONS = "sections"


# ============================================================================
# DATASET SCHEMAS
# ============================================================================

class DatasetUploadResponse(BaseModel):
    """Response after uploading a dataset."""
    id: int
    filename: str
    file_type: str
    status: DatasetStatusSchema
    s3_key: str
    row_count: Optional[int] = None
    validation_errors: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetImportStats(BaseModel):
    """Statistics from dataset import."""
    created: int
    updated: int
    skipped: int
    total_processed: int
    errors: List[str]
    created_ids: List[int]


class DatasetUploadWithImportResponse(BaseModel):
    """Response for dataset upload with import statistics."""
    id: int
    filename: str
    file_type: str
    status: DatasetStatusSchema
    s3_key: str
    row_count: int
    created_at: datetime
    message: str
    validation: Dict[str, Any]
    import_stats: Optional[DatasetImportStats] = None

    class Config:
        from_attributes = True


class DatasetPreviewResponse(BaseModel):
    """Response for dataset preview with pagination."""
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_rows: int
    offset: int
    limit: int


class DatasetListItem(BaseModel):
    """Dataset item in list view."""
    id: int
    filename: str
    file_type: str
    status: DatasetStatusSchema
    row_count: Optional[int]
    created_at: datetime
    uploaded_by: Optional[int]

    class Config:
        from_attributes = True


class DatasetValidationError(BaseModel):
    """Validation error details."""
    row: Optional[int] = None
    column: Optional[str] = None
    error_type: str
    message: str
    suggestion: Optional[str] = None


class DatasetValidationResult(BaseModel):
    """Complete validation result."""
    is_valid: bool
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: List[DatasetValidationError]
    warnings: Optional[List[str]] = []


# ============================================================================
# COURSE DATASET SCHEMA
# ============================================================================

class CourseDataRow(BaseModel):
    """Schema for course data validation."""

    course_name: str = Field(..., min_length=1, max_length=200)
    course_code: Optional[str] = Field(None, max_length=50)
    instructor: Optional[str] = Field(None, min_length=1, max_length=100)
    section: Optional[str] = Field(None, min_length=1, max_length=50)
    program: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(Theory|Lab)$")
    hours_per_week: int = Field(default=3, ge=0, le=10)
    duration_minutes: Optional[int] = Field(None, ge=30, le=300)
    sessions_per_week: Optional[int] = Field(None, ge=1, le=6)

    @field_validator('course_code', mode='before')
    @classmethod
    def generate_course_code(cls, v, info):
        """Auto-generate course code if not provided."""
        if v is None or v == '':
            # Generate from course_name
            course_name = info.data.get('course_name', 'UNKNOWN')
            # Take first letters and make uppercase
            code = ''.join([word[0] for word in course_name.split()[:3]]).upper()
            return f"{code}-{abs(hash(course_name)) % 1000:03d}"
        return v

    class Config:
        populate_by_name = True


# ============================================================================
# TEACHER DATASET SCHEMA
# ============================================================================

class TeacherDataRow(BaseModel):
    """Expected structure for teacher CSV/XLSX rows."""
    teacher_code: str = Field(..., min_length=1, max_length=50)
    teacher_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(None, max_length=100)


# ============================================================================
# ROOM DATASET SCHEMA
# ============================================================================

class RoomDataRow(BaseModel):
    """Schema for room data validation."""

    rooms: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(Lab|Theory)$", description="Must be 'Lab' or 'Theory'")
    capacity: int = Field(default=50, ge=1, le=500)

    class Config:
        populate_by_name = True


# ============================================================================
# SECTION DATASET SCHEMA
# ============================================================================

class SectionDataRow(BaseModel):
    """Expected structure for section CSV/XLSX rows."""
    section_code: str = Field(..., min_length=1, max_length=50)
    section_name: Optional[str] = Field(None, max_length=255)
    course_code: str = Field(..., min_length=1, max_length=50)
    semester: str = Field(..., max_length=50)
    year: int = Field(..., ge=2020, le=2030)
    student_count: int = Field(default=30, ge=1, le=500)


# ============================================================================
# GENERAL RESPONSE SCHEMAS
# ============================================================================

class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    details: Optional[str] = None


# ============================================================================
# CONSTRAINT CONFIGURATION SCHEMAS
# ============================================================================

class HardConstraints(BaseModel):
    """Hard constraints that must never be violated."""
    no_teacher_overlap: bool = True
    no_room_overlap: bool = True
    no_section_overlap: bool = True
    respect_timeslot_duration: bool = True
    valid_timeslots_only: bool = True


class SoftConstraintItem(BaseModel):
    """Individual soft constraint with weight."""
    enabled: bool = True
    weight: int = Field(ge=1, le=10, default=5)
    threshold: Optional[str] = None  # For time-based constraints like "09:00"


class SoftConstraints(BaseModel):
    """Soft constraints that are scored and weighted."""
    minimize_early_morning: SoftConstraintItem = SoftConstraintItem(
        enabled=True, weight=5, threshold="09:00"
    )
    minimize_late_evening: SoftConstraintItem = SoftConstraintItem(
        enabled=True, weight=5, threshold="16:00"
    )
    minimize_teacher_gaps: SoftConstraintItem = SoftConstraintItem(
        enabled=True, weight=8
    )
    compact_student_schedules: SoftConstraintItem = SoftConstraintItem(
        enabled=True, weight=7
    )
    room_type_preference: SoftConstraintItem = SoftConstraintItem(
        enabled=True, weight=6
    )
    teacher_time_preferences: SoftConstraintItem = SoftConstraintItem(
        enabled=True, weight=9
    )


class OptionalConstraintItem(BaseModel):
    """Individual optional constraint."""
    enabled: bool = False
    enforce: Optional[bool] = None  # Whether to enforce or just warn
    time: Optional[str] = None  # For time-based constraints


class OptionalConstraints(BaseModel):
    """Optional constraints that can be toggled."""
    check_room_capacity: OptionalConstraintItem = OptionalConstraintItem(
        enabled=False, enforce=False
    )
    avoid_scheduling_after: OptionalConstraintItem = OptionalConstraintItem(
        enabled=False, time="18:00"
    )
    group_labs_same_day: OptionalConstraintItem = OptionalConstraintItem(
        enabled=False
    )
    avoid_building_changes: OptionalConstraintItem = OptionalConstraintItem(
        enabled=False
    )
    minimize_fragmentation: OptionalConstraintItem = OptionalConstraintItem(
        enabled=True
    )


class ConstraintConfigCreate(BaseModel):
    """Schema for creating a new constraint configuration."""
    name: str = Field(..., min_length=1, max_length=255)
    is_default: bool = False

    # Timeslot settings
    timeslot_duration_minutes: int = Field(default=60, ge=30, le=240)
    days_per_week: int = Field(default=5, ge=1, le=7)
    start_time: str = Field(default="08:00", pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(default="17:00", pattern=r"^\d{2}:\d{2}$")

    # Constraints
    hard_constraints: Optional[HardConstraints] = None
    soft_constraints: Optional[SoftConstraints] = None
    optional_constraints: Optional[OptionalConstraints] = None

    # Optimization settings
    max_optimization_time_seconds: int = Field(default=60, ge=10, le=300)
    min_acceptable_score: float = Field(default=70.0, ge=0.0, le=100.0)


class ConstraintConfigUpdate(BaseModel):
    """Schema for updating an existing constraint configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None

    # Timeslot settings
    timeslot_duration_minutes: Optional[int] = Field(None, ge=30, le=240)
    days_per_week: Optional[int] = Field(None, ge=1, le=7)
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")

    # Constraints
    hard_constraints: Optional[HardConstraints] = None
    soft_constraints: Optional[SoftConstraints] = None
    optional_constraints: Optional[OptionalConstraints] = None

    # Optimization settings
    max_optimization_time_seconds: Optional[int] = Field(None, ge=10, le=300)
    min_acceptable_score: Optional[float] = Field(None, ge=0.0, le=100.0)


class ConstraintConfigResponse(BaseModel):
    """Schema for constraint configuration response."""
    id: int
    institution_id: int
    name: str
    is_active: bool
    is_default: bool

    # Timeslot settings
    timeslot_duration_minutes: int
    days_per_week: int
    start_time: str
    end_time: str

    # Constraints - MAKE THESE OPTIONAL
    hard_constraints: Optional[Dict[str, Any]] = None
    soft_constraints: Optional[Dict[str, Any]] = None
    optional_constraints: Optional[Dict[str, Any]] = None

    # Optimization settings
    max_optimization_time_seconds: int
    min_acceptable_score: float

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConstraintConfigListItem(BaseModel):
    """Schema for constraint configuration list item."""
    id: int
    name: str
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TimetableUpdate(BaseModel):
    """Schema for updating a timetable."""
    name: str = Field(..., min_length=1, max_length=255)


# ============================================================================
# TEACHER CONSTRAINT SCHEMAS (for Generate Timetable)
# ============================================================================

class ConstraintTypeEnum(str, Enum):
    """Types of teacher/room constraints."""
    BLOCKED_SLOT = "blocked_slot"
    DAY_OFF = "day_off"
    AVAILABLE_WINDOW = "available_window"
    PREFERRED_SLOT = "preferred_slot"


class TeacherConstraint(BaseModel):
    """
    Constraint for a specific teacher's availability.

    Examples:
    - blocked_slot: Teacher unavailable on Monday 9:00-12:00 (hard constraint)
    - day_off: Teacher wants Fridays off (soft constraint with weight)
    - available_window: Teacher only available 10:00-16:00 (hard constraint)
    - preferred_slot: Teacher prefers afternoons (soft constraint with weight)
    """
    teacher_id: int
    constraint_type: ConstraintTypeEnum
    is_hard: bool = False  # Hard = must enforce, Soft = penalize violations
    weight: int = Field(default=5, ge=1, le=10)  # Weight for soft constraints
    day: Optional[str] = None  # For single-day constraints: "Monday", "Tuesday", etc.
    days: Optional[List[str]] = None  # For multi-day constraints like day_off: ["Friday", "Saturday"]
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")  # "09:00"
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")  # "12:00"


class RoomConstraint(BaseModel):
    """
    Constraint for a specific room's availability.
    """
    room_id: int
    constraint_type: ConstraintTypeEnum
    is_hard: bool = True  # Room constraints are usually hard
    day: Optional[str] = None
    days: Optional[List[str]] = None
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    reason: Optional[str] = None  # Optional reason for the constraint


class LockTypeEnum(str, Enum):
    """Types of locked assignments."""
    TIME_ONLY = "time_only"  # Only day/time is locked, room can be assigned
    FULL_LOCK = "full_lock"  # Day, time, and room are all locked


class LockedAssignment(BaseModel):
    """
    Pre-scheduled session that must be respected during generation.

    A locked assignment fixes a session to a specific day and time.
    If lock_type is 'time_only', the optimizer will assign an appropriate room.
    If lock_type is 'full_lock', the room is also fixed.
    """
    session_key: str  # Format: "COURSE_CODE-SECTION-T/L-SESSION_NUM"
    course_id: int
    section_id: int
    teacher_id: int
    day: str  # "Monday", "Tuesday", etc.
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # "09:00"
    room_id: Optional[int] = None  # Required if lock_type is 'full_lock'
    lock_type: LockTypeEnum = LockTypeEnum.TIME_ONLY


class GenerateRequest(BaseModel):
    """
    Request body for timetable generation with constraints.

    This allows users to specify teacher/room constraints and locked
    assignments before generating a new timetable.
    """
    constraint_config_id: Optional[int] = None  # Which constraint profile to use
    teacher_constraints: List[TeacherConstraint] = []
    room_constraints: List[RoomConstraint] = []
    locked_assignments: List[LockedAssignment] = []
    population_size: int = Field(default=30, ge=10, le=100)
    generations: int = Field(default=100, ge=50, le=300)
    target_fitness: float = Field(default=85.0, ge=50.0, le=100.0)

    # Reproducibility: Optional random seed for deterministic generation
    # If provided, the same seed with same inputs will produce the same result
    random_seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducible generation. Same seed + inputs = same result."
    )


class GenerateResponse(BaseModel):
    """Response after successful timetable generation."""
    message: str
    timetable_id: int
    generation_time: float
    sessions_scheduled: int
    sessions_total: int
    fitness_score: float
    hard_violations: Optional[Dict[str, int]] = None
    soft_scores: Optional[Dict[str, float]] = None
    constraints_applied: Optional[Dict[str, Any]] = None


# ============================================================================
# TEACHER CONSTRAINT PROFILES
# ============================================================================

class TeacherConstraintItemBase(BaseModel):
    teacher_id: Optional[int] = None
    day: str  # "Mon", "Tue" etc.
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    constraint_type: str = Field(..., description="Blocked Slot or Preferred Slot")
    priority: str = Field(default="hard", pattern="^(hard|soft)$")

class TeacherConstraintItemCreate(TeacherConstraintItemBase):
    pass

class TeacherConstraintItemResponse(TeacherConstraintItemBase):
    id: int
    profile_id: int

    class Config:
        from_attributes = True

class TeacherConstraintProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_default: bool = False

class TeacherConstraintProfileCreate(TeacherConstraintProfileBase):
    items: List[TeacherConstraintItemCreate]

class TeacherConstraintProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    items: Optional[List[TeacherConstraintItemCreate]] = None

class TeacherConstraintProfileResponse(TeacherConstraintProfileBase):
    id: int
    institution_id: int
    created_at: datetime
    updated_at: datetime
    items: List[TeacherConstraintItemResponse]

    class Config:
        from_attributes = True

class TeacherConstraintProfileSummary(TeacherConstraintProfileBase):
    id: int
    institution_id: int
    created_at: datetime
    updated_at: datetime
    item_count: int

    class Config:
        from_attributes = True