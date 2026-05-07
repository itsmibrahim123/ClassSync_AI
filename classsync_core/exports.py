"""
Export utilities for timetables.
Supports multiple export formats: XLSX, CSV, JSON, PDF, PNG.
"""

import pandas as pd
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from datetime import datetime
import os

from classsync_core.models import Timetable, TimetableEntry, Course, Teacher, Room, Section


class BaseExporter(ABC):
    """Base class for all exporters."""

    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    def export(self, timetable_id: int, output_path: str, **kwargs) -> str:
        """
        Export timetable to file.

        Args:
            timetable_id: ID of timetable to export
            output_path: Path where file should be saved
            **kwargs: Additional export options

        Returns:
            Path to exported file
        """
        pass

    def load_timetable_data(self, timetable_id: int) -> pd.DataFrame:
        """
        Load timetable data as DataFrame with all related information.

        Teacher data comes from TimetableEntry.teacher_id, which is the
        section-specific teacher assigned during scheduling (not from Course).

        Args:
            timetable_id: ID of timetable to load

        Returns:
            DataFrame with complete timetable data
        """
        from sqlalchemy.orm import joinedload

        # Get timetable
        timetable = self.db.query(Timetable).filter(
            Timetable.id == timetable_id
        ).first()

        if not timetable:
            raise ValueError(f"Timetable {timetable_id} not found")

        # Get all entries with eager loading for efficiency
        entries = self.db.query(TimetableEntry).options(
            joinedload(TimetableEntry.course),
            joinedload(TimetableEntry.teacher),
            joinedload(TimetableEntry.room),
            joinedload(TimetableEntry.section)
        ).filter(
            TimetableEntry.timetable_id == timetable_id
        ).all()

        # Build DataFrame with full details
        data = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for entry in entries:
            # Use eager-loaded relationships (already loaded via joinedload)
            course = entry.course
            teacher = entry.teacher  # Section-specific teacher from TimetableEntry
            room = entry.room
            section = entry.section

            # Safely get course code - prioritize dataset value
            course_code = 'Unknown'
            if course:
                course_code = course.code if course.code else 'Unknown'

            # Safely get teacher info
            instructor_name = 'Unknown'
            teacher_code = 'Unknown'
            if teacher:
                instructor_name = teacher.name if teacher.name else 'Unknown'
                teacher_code = teacher.code if teacher.code else 'Unknown'

            # Safely get room info
            room_code = 'Unknown'
            room_type = 'Unknown'
            building = 'Unknown'
            if room:
                room_code = room.code if room.code else 'Unknown'
                room_type = room.room_type.value if room.room_type else 'Unknown'
                building = room.building if room.building else 'N/A'

            # Safely get section/program info
            section_code = 'Unknown'
            program = 'Unknown'
            if section:
                section_code = section.code if section.code else 'Unknown'
                program = section.name if section.name else section_code

            data.append({
                'Timetable_ID': timetable_id,
                'Entry_ID': entry.id,
                'Course_Code': course_code,
                'Course_Name': course.name if course else 'Unknown',
                'Section': section_code,
                'Program': program,
                'Instructor': instructor_name,
                'Teacher_Code': teacher_code,
                'Room': room_code,
                'Room_Type': room_type,
                'Building': building,
                'Weekday': day_names[entry.day_of_week] if 0 <= entry.day_of_week < len(day_names) else 'Unknown',
                'Start_Time': entry.start_time,
                'End_Time': entry.end_time,
                'Duration_Minutes': self._calculate_duration(entry.start_time, entry.end_time),
                'Semester': timetable.semester,
                'Year': timetable.year
            })

        return pd.DataFrame(data)

    def _calculate_duration(self, start_time: str, end_time: str) -> int:
        """Calculate duration in minutes between two times."""
        from classsync_core.utils import parse_time, time_to_minutes

        start_min = time_to_minutes(parse_time(start_time))
        end_min = time_to_minutes(parse_time(end_time))

        return end_min - start_min


class ExportManager:
    """Manager class to handle all export operations."""

    def __init__(self, db: Session):
        self.db = db
        self.exporters = {}

    def register_exporter(self, format_name: str, exporter: BaseExporter):
        """Register an exporter for a specific format."""
        self.exporters[format_name] = exporter

    def export_timetable(
            self,
            timetable_id: int,
            format: str,
            output_path: str,
            **kwargs
    ) -> str:
        """
        Export timetable in specified format.

        Args:
            timetable_id: ID of timetable to export
            format: Export format (xlsx, csv, json, pdf, png)
            output_path: Path where file should be saved
            **kwargs: Additional format-specific options

        Returns:
            Path to exported file
        """
        if format not in self.exporters:
            raise ValueError(f"Unsupported export format: {format}")

        exporter = self.exporters[format]
        return exporter.export(timetable_id, output_path, **kwargs)