"""
SQLAlchemy database models for ClassSync AI.
All core data structures and relationships.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Text, Float, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from classsync_api.database import Base
import enum


# ============================================================================
# MIXINS
# ============================================================================

class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """Mixin to add soft delete capability."""
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, enum.Enum):
    """User roles for access control."""
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    VIEWER = "viewer"


class SubscriptionTier(str, enum.Enum):
    """Subscription tiers for institutions."""
    FREE_TRIAL = "free_trial"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class RoomType(str, enum.Enum):
    """Room types for scheduling."""
    LECTURE_HALL = "lecture_hall"
    LAB = "lab"
    TUTORIAL_ROOM = "tutorial_room"
    SEMINAR_ROOM = "seminar_room"


class CourseType(str, enum.Enum):
    """Course types."""
    LECTURE = "lecture"
    LAB = "lab"
    TUTORIAL = "tutorial"


class DatasetStatus(str, enum.Enum):
    """Status of uploaded datasets."""
    PENDING = "pending"
    VALIDATED = "validated"
    INVALID = "invalid"
    PROCESSING = "processing"


class TimetableStatus(str, enum.Enum):
    """Status of timetable generation."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# CORE MODELS
# ============================================================================

class Institution(Base, TimestampMixin, SoftDeleteMixin):
    """Institution/University model for multi-tenancy."""
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)

    # Subscription
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE_TRIAL)
    subscription_expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    users = relationship("User", back_populates="institution")
    rooms = relationship("Room", back_populates="institution")
    teachers = relationship("Teacher", back_populates="institution")
    courses = relationship("Course", back_populates="institution")
    sections = relationship("Section", back_populates="institution")
    datasets = relationship("Dataset", back_populates="institution")
    timetables = relationship("Timetable", back_populates="institution")
    constraint_configs = relationship("ConstraintConfig", back_populates="institution")


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)

    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime)

    # Relationships
    institution = relationship("Institution", back_populates="users")


class Room(Base, TimestampMixin, SoftDeleteMixin):
    """Room/Venue model."""
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)

    code = Column(String(50), nullable=False)
    name = Column(String(255))
    room_type = Column(SQLEnum(RoomType), default=RoomType.LECTURE_HALL)
    capacity = Column(Integer)
    building = Column(String(100))
    floor = Column(String(20))

    # Constraints
    is_available = Column(Boolean, default=True, nullable=False)

    # Relationships
    institution = relationship("Institution", back_populates="rooms")
    timetable_entries = relationship("TimetableEntry", back_populates="room")


class Teacher(Base, TimestampMixin, SoftDeleteMixin):
    """Teacher/Faculty model."""
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)

    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    department = Column(String(100))

    # Preferences (stored as JSON)
    time_preferences = Column(JSON)  # e.g., {"avoid_early": true, "prefer_afternoon": false}

    # Relationships
    institution = relationship("Institution", back_populates="teachers")
    courses = relationship("Course", back_populates="teacher")
    timetable_entries = relationship("TimetableEntry", back_populates="teacher")


class Course(Base, TimestampMixin, SoftDeleteMixin):
    """Course model."""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)

    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    program = Column(String(100))
    course_type = Column(SQLEnum(CourseType), default=CourseType.LECTURE)
    credit_hours = Column(Integer)

    # Duration in minutes
    duration_minutes = Column(Integer, default=60)

    # How many sessions per week
    sessions_per_week = Column(Integer, default=1)

    # Relationships
    institution = relationship("Institution", back_populates="courses")
    teacher = relationship("Teacher", back_populates="courses")
    sections = relationship("Section", back_populates="course")


class Section(Base, TimestampMixin, SoftDeleteMixin):
    """Section/Class model - groups of students taking a course."""
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)

    code = Column(String(50), nullable=False)
    name = Column(String(255))
    semester = Column(String(50))
    year = Column(Integer)
    student_count = Column(Integer)

    # Relationships
    institution = relationship("Institution", back_populates="sections")
    course = relationship("Course", back_populates="sections")
    teacher = relationship("Teacher")
    timetable_entries = relationship("TimetableEntry", back_populates="section")


class Dataset(Base, TimestampMixin):
    """Dataset upload history and validation."""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)

    filename = Column(String(255), nullable=False)
    file_type = Column(String(50))  # csv, xlsx
    s3_key = Column(String(500))  # S3 storage key

    status = Column(SQLEnum(DatasetStatus), default=DatasetStatus.PENDING)
    validation_errors = Column(JSON)  # Store validation issues

    # Metadata
    row_count = Column(Integer)
    uploaded_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    institution = relationship("Institution", back_populates="datasets")


class Timetable(Base, TimestampMixin):
    """Generated timetable metadata."""
    __tablename__ = "timetables"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)

    name = Column(String(255))
    semester = Column(String(50))
    year = Column(Integer)

    status = Column(SQLEnum(TimetableStatus), default=TimetableStatus.PENDING)

    # Generation metadata
    generation_time_seconds = Column(Float)
    constraint_score = Column(Float)
    conflict_count = Column(Integer, default=0)

    # Configuration snapshot
    constraint_config = Column(JSON)

    generated_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    institution = relationship("Institution", back_populates="timetables")
    entries = relationship("TimetableEntry", back_populates="timetable", cascade="all, delete-orphan")


class TimetableEntry(Base, TimestampMixin):
    """Individual timetable slot assignment."""
    __tablename__ = "timetable_entries"

    id = Column(Integer, primary_key=True, index=True)
    timetable_id = Column(Integer, ForeignKey("timetables.id"), nullable=False, index=True)

    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)

    # Time slot
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(String(10), nullable=False)  # e.g., "09:00"
    end_time = Column(String(10), nullable=False)  # e.g., "10:30"

    # Relationships
    timetable = relationship("Timetable", back_populates="entries")
    section = relationship("Section", back_populates="timetable_entries")
    course = relationship("Course")
    teacher = relationship("Teacher", back_populates="timetable_entries")
    room = relationship("Room", back_populates="timetable_entries")


class ConstraintConfig(Base, TimestampMixin):
    """Constraint configuration for timetable generation."""
    __tablename__ = "constraint_configs"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)  # e.g., "Default Configuration", "Spring 2024"
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Timeslot configuration
    timeslot_duration_minutes = Column(Integer, default=60)  # 60, 90, or 120
    days_per_week = Column(Integer, default=5)  # Usually 5 or 6
    start_time = Column(String(10), default="08:00")  # e.g., "08:00"
    end_time = Column(String(10), default="17:00")  # e.g., "17:00"

    # Hard constraints (always enforced, stored as JSON for flexibility)
    hard_constraints = Column(JSON, default={
        "no_teacher_overlap": True,
        "no_room_overlap": True,
        "no_section_overlap": True,
        "respect_timeslot_duration": True,
        "valid_timeslots_only": True
    })

    # Soft constraints (scored/weighted, stored as JSON)
    soft_constraints = Column(JSON, default={
        "minimize_early_morning": {"enabled": True, "weight": 5, "threshold": "09:00"},
        "minimize_late_evening": {"enabled": True, "weight": 5, "threshold": "16:00"},
        "minimize_teacher_gaps": {"enabled": True, "weight": 8},
        "compact_student_schedules": {"enabled": True, "weight": 7},
        "room_type_preference": {"enabled": True, "weight": 6},
        "teacher_time_preferences": {"enabled": True, "weight": 9}
    })

    # Optional constraints (toggleable)
    optional_constraints = Column(JSON, default={
        "check_room_capacity": {"enabled": False, "enforce": False},
        "avoid_scheduling_after": {"enabled": False, "time": "18:00"},
        "group_labs_same_day": {"enabled": False},
        "avoid_building_changes": {"enabled": False},
        "minimize_fragmentation": {"enabled": True}
    })

    # Optimization settings
    max_optimization_time_seconds = Column(Integer, default=60)
    min_acceptable_score = Column(Float, default=70.0)

    # Relationships
    institution = relationship("Institution", back_populates="constraint_configs")


class TeacherConstraintProfile(Base, TimestampMixin):
    """Profile for storing sets of teacher constraints."""
    __tablename__ = "teacher_constraint_profiles"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    
    # Relationships
    items = relationship("TeacherConstraintItem", back_populates="profile", cascade="all, delete-orphan")


class TeacherConstraintItem(Base):
    """Individual constraint within a profile."""
    __tablename__ = "teacher_constraint_items"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("teacher_constraint_profiles.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    
    day = Column(String(10), nullable=False)
    start_time = Column(String(10), nullable=False)
    end_time = Column(String(10), nullable=False)
    
    constraint_type = Column(String(50), nullable=False)
    priority = Column(String(20), default="hard")

    # Relationships
    profile = relationship("TeacherConstraintProfile", back_populates="items")
    teacher = relationship("Teacher")