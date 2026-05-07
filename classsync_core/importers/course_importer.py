"""
Course importer - creates Teacher, Course, and Section records from validated CSV data.
"""

import pandas as pd
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from classsync_core.importers.base_importer import BaseImporter, ImportResult
from classsync_core.models import Course, Teacher, Section, CourseType


class CourseImporter(BaseImporter):
    """Import courses, teachers, and sections from validated dataset."""

    def __init__(self, db: Session, institution_id: int = 1):
        super().__init__(db, institution_id)
        self.teacher_cache: Dict[str, int] = {}  # name -> teacher_id
        self.course_cache: Dict[str, int] = {}  # course_name -> course_id

    def import_from_dataframe(self, df: pd.DataFrame) -> ImportResult:
        """
        Import courses from DataFrame.

        Expected columns: course_name, instructor, section, program, type, hours_per_week
        Optional: course_code, duration_minutes, sessions_per_week

        Args:
            df: DataFrame with validated course data

        Returns:
            ImportResult with statistics
        """
        print(f"[CourseImporter] Starting import from DataFrame with {len(df)} rows")
        df = self.normalize_dataframe(df)
        print(f"[CourseImporter] Columns after normalization: {list(df.columns)}")

        # Validate required columns
        required = ['course_name', 'instructor', 'section', 'program', 'type', 'hours_per_week']
        missing = [col for col in required if col not in df.columns]
        if missing:
            error_msg = f"Missing columns: {missing}. Available: {list(df.columns)}"
            print(f"[CourseImporter] ERROR: {error_msg}")
            self.result.errors.append(error_msg)
            return self.result

        try:
            # Step 0: Clear existing data for this institution (Single Source of Truth)
            print("[CourseImporter] Step 0: Clearing existing data...")
            self.clear_data()

            # Step 1: Import all unique teachers
            print("[CourseImporter] Step 1: Importing teachers...")
            self._import_teachers(df)

            # Step 2: Import courses and sections
            print("[CourseImporter] Step 2: Importing courses and sections...")
            self._import_courses_and_sections(df)

            # Commit if successful
            if self.result.success:
                print(f"[CourseImporter] Import successful! Committing... (created: {self.result.created_count})")
                self.commit()
                print("[CourseImporter] Commit complete!")
            else:
                print(f"[CourseImporter] Import had errors, rolling back: {self.result.errors}")
                self.rollback()

        except Exception as e:
            import traceback
            error_msg = f"Import failed: {str(e)}"
            print(f"[CourseImporter] EXCEPTION: {error_msg}")
            print(f"[CourseImporter] Traceback: {traceback.format_exc()}")
            self.rollback()
            self.result.errors.append(error_msg)

        print(f"[CourseImporter] Final result: created={self.result.created_count}, errors={self.result.errors}")
        return self.result

    def clear_data(self):
        """Soft delete all existing courses, sections, and teachers for this institution.

        This is called BEFORE importing new data to ensure the uploaded dataset
        is the SINGLE SOURCE OF TRUTH for teachers, courses, and sections.

        NOTE: Does NOT commit - the caller is responsible for committing after
        all operations (clear + import) succeed to maintain atomicity.
        """
        now = datetime.utcnow()

        # Count existing records before clearing (for logging)
        existing_sections = self.db.query(Section).filter(
            Section.institution_id == self.institution_id,
            Section.is_deleted == False
        ).count()
        existing_courses = self.db.query(Course).filter(
            Course.institution_id == self.institution_id,
            Course.is_deleted == False
        ).count()
        existing_teachers = self.db.query(Teacher).filter(
            Teacher.institution_id == self.institution_id,
            Teacher.is_deleted == False
        ).count()

        print(f"[CourseImporter] Clearing existing data for institution {self.institution_id}:")
        print(f"  - {existing_sections} sections to soft-delete")
        print(f"  - {existing_courses} courses to soft-delete")
        print(f"  - {existing_teachers} teachers to soft-delete")

        # Soft delete sections FIRST (they reference courses)
        sections_deleted = self.db.query(Section).filter(
            Section.institution_id == self.institution_id,
            Section.is_deleted == False
        ).update({Section.is_deleted: True, Section.deleted_at: now}, synchronize_session='fetch')
        print(f"[CourseImporter] Soft-deleted {sections_deleted} sections")

        # Soft delete courses (they reference teachers)
        courses_deleted = self.db.query(Course).filter(
            Course.institution_id == self.institution_id,
            Course.is_deleted == False
        ).update({Course.is_deleted: True, Course.deleted_at: now}, synchronize_session='fetch')
        print(f"[CourseImporter] Soft-deleted {courses_deleted} courses")

        # Soft delete teachers LAST
        teachers_deleted = self.db.query(Teacher).filter(
            Teacher.institution_id == self.institution_id,
            Teacher.is_deleted == False
        ).update({Teacher.is_deleted: True, Teacher.deleted_at: now}, synchronize_session='fetch')
        print(f"[CourseImporter] Soft-deleted {teachers_deleted} teachers")

        # Flush to ensure the deletes are visible within this transaction
        # but DON'T commit - let the full import complete first
        self.db.flush()
        print(f"[CourseImporter] Clear flushed. Old data marked as deleted (pending commit).")

    def _import_teachers(self, df: pd.DataFrame):
        """Import all unique teachers from the instructor column."""
        unique_teachers = df['instructor'].unique()
        print(f"[CourseImporter] Found {len(unique_teachers)} unique instructors in dataset")

        created_teachers = []
        skipped_teachers = []

        for teacher_name in unique_teachers:
            teacher_name = str(teacher_name).strip()

            if not teacher_name or teacher_name.lower() == 'nan':
                teacher_name = "TBD"

            # Check if teacher exists (Active only - should be NONE after clear_data)
            existing = self.db.query(Teacher).filter(
                Teacher.name == teacher_name,
                Teacher.institution_id == self.institution_id,
                Teacher.is_deleted == False
            ).first()

            if existing:
                # This should NOT happen after clear_data!
                self.teacher_cache[teacher_name] = existing.id
                self.result.skipped_count += 1
                skipped_teachers.append(f"{teacher_name} (id={existing.id})")
            else:
                # Generate teacher code
                name_parts = teacher_name.split()
                # Ensure we have at least 3 chars for base if possible
                if len(name_parts) >= 3:
                    code_base = ''.join([p[0].upper() for p in name_parts[:3]])
                else:
                    code_base = ''.join([p[0].upper() for p in name_parts])
                    if len(code_base) < 3:
                        code_base = (code_base + "XX")[:3]

                teacher_code = f"{code_base}{abs(hash(teacher_name)) % 100:02d}"

                # Create NEW teacher from dataset
                teacher = Teacher(
                    institution_id=self.institution_id,
                    code=teacher_code,
                    name=teacher_name,
                    email=f"{teacher_name.lower().replace(' ', '.')}@university.edu"
                )
                self.db.add(teacher)
                self.db.flush()

                self.teacher_cache[teacher_name] = teacher.id
                self.result.created_count += 1
                created_teachers.append(f"{teacher_name} (id={teacher.id})")

        print(f"[CourseImporter] Created {len(created_teachers)} new teachers from dataset")
        if created_teachers[:5]:
            print(f"  Examples: {', '.join(created_teachers[:5])}")
        if skipped_teachers:
            print(f"[CourseImporter] WARNING: Skipped {len(skipped_teachers)} teachers (already existed - this shouldn't happen!)")
            print(f"  Skipped: {', '.join(skipped_teachers[:5])}")

    def _import_courses_and_sections(self, df: pd.DataFrame):
        """Import courses and their sections."""
        
        # Track counts of (course_name, section_code) encountered in this batch
        # to handle duplicate section codes by appending a suffix
        section_counts = {}

        for index, row in df.iterrows():
            row_num = index + 2

            try:
                # Get or create course
                course_id = self._get_or_create_course(row, row_num)

                if course_id:
                    # Determine unique section code for this row
                    course_name = str(row['course_name']).strip()
                    original_section_code = str(row['section']).strip()
                    
                    # Handle missing section
                    if not original_section_code or original_section_code.lower() == 'nan':
                        original_section_code = "A"
                    
                    key = (course_name, original_section_code)
                    
                    if key in section_counts:
                        section_counts[key] += 1
                        # Append suffix for duplicates within this file
                        # e.g., "A" -> "A-1", "A-2"
                        section_code = f"{original_section_code}-{section_counts[key]}"
                    else:
                        section_counts[key] = 0
                        section_code = original_section_code

                    # Create section with potentially modified code
                    self._create_section(course_id, section_code, row, row_num)

            except Exception as e:
                self.log_error(row_num, f"Failed to import course/section: {str(e)}")

    def _get_or_create_course(self, row: pd.Series, row_num: int) -> int:
        """Get existing course or create new one."""
        course_name = str(row['course_name']).strip()
        course_type_str = str(row['type']).strip().lower()
        hours_per_week = int(row.get('hours_per_week', 3))

        # Generate course code from course name (not including section)
        # PRIORITIZE DATASET VALUE
        if 'course_code' in row and pd.notna(row['course_code']) and str(row['course_code']).strip():
            course_code = str(row['course_code']).strip()
        else:
            # Only generate if absolutely necessary (shouldn't happen with valid dataset)
            code_parts = ''.join([word[0].upper() for word in course_name.split()[:3]])
            course_code = f"{code_parts}{abs(hash(course_name)) % 1000:03d}"

        # Check cache by course_name (NOT course_name + section)
        if course_name in self.course_cache:
            return self.course_cache[course_name]

        # Map course type
        course_type = CourseType.LAB if course_type_str == 'lab' else CourseType.LECTURE

        # Check if course exists (by name OR code, not section)
        # Only check active courses (we just cleared old ones, so this should only return
        # courses created in THIS session if cache missed for some reason)
        existing = self.db.query(Course).filter(
            Course.name == course_name,
            Course.institution_id == self.institution_id,
            Course.is_deleted == False
        ).first()

        if existing:
            self.course_cache[course_name] = existing.id
            return existing.id

        # For courses with multiple instructors (sections A, B with different teachers),
        # we'll use the first instructor we encounter as the "primary" teacher
        # (The real relationship is Section -> Teacher, not Course -> Teacher)
        instructor_name = str(row['instructor']).strip()
        if not instructor_name or instructor_name.lower() == 'nan':
            instructor_name = "TBD"
            
        teacher_id = self.teacher_cache.get(instructor_name)
        
        # Fallback if teacher still not found (shouldn't happen if _import_teachers works)
        if not teacher_id:
            # Try to find TBD in cache
            teacher_id = self.teacher_cache.get("TBD")
            if not teacher_id:
                # Last resort: Create TBD teacher on the fly
                print("[CourseImporter] WARNING: TBD teacher missing, creating on the fly")
                tbd_teacher = Teacher(
                    institution_id=self.institution_id,
                    code="TBD00",
                    name="TBD",
                    email="tbd@university.edu"
                )
                self.db.add(tbd_teacher)
                self.db.flush()
                self.teacher_cache["TBD"] = tbd_teacher.id
                teacher_id = tbd_teacher.id

        # Determine duration and sessions based on type and hours
        if course_type == CourseType.LAB:
            duration_minutes = 180  # 3 hours for labs
            sessions_per_week = 1
        else:
            if hours_per_week == 2:
                duration_minutes = 120  # 2 hours
                sessions_per_week = 1
            elif hours_per_week == 3:
                duration_minutes = 90  # 1.5 hours
                sessions_per_week = 2
            else:
                duration_minutes = 90
                sessions_per_week = max(1, hours_per_week // 2)

        # Create course
        course = Course(
            institution_id=self.institution_id,
            teacher_id=teacher_id,  # Primary teacher (may be overridden by sections)
            code=course_code,
            name=course_name,
            course_type=course_type,
            credit_hours=hours_per_week,
            duration_minutes=duration_minutes,
            sessions_per_week=sessions_per_week
        )
        self.db.add(course)
        self.db.flush()

        self.course_cache[course_name] = course.id
        self.result.created_count += 1

        return course.id

    def _create_section(self, course_id: int, section_code: str, row: pd.Series, row_num: int):
        """Create a section for a course."""
        # section_code is passed in now, potentially modified
        program = str(row.get('program', section_code)).strip()

        # Check if section exists
        existing = self.db.query(Section).filter(
            Section.code == section_code,
            Section.course_id == course_id,
            Section.institution_id == self.institution_id,
            Section.is_deleted == False
        ).first()

        if existing:
            self.result.skipped_count += 1
            return

        # Get section-specific teacher
        instructor_name = str(row['instructor']).strip()
        if not instructor_name or instructor_name.lower() == 'nan':
            instructor_name = "TBD"
            
        teacher_id = self.teacher_cache.get(instructor_name)
        
        # Create section
        section = Section(
            institution_id=self.institution_id,
            course_id=course_id,
            teacher_id=teacher_id,
            code=section_code,
            name=program,
            semester="Fall",
            year=2025,
            student_count=50  # Default
        )
        self.db.add(section)
        self.db.flush()

        self.result.created_count += 1