"""
Chromosome - Represents one complete timetable solution.
Each gene is a session assignment (session_id → day, start_time, room).
"""

import pandas as pd
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class Gene:
    """
    One gene = one session assignment.

    Fixed attributes (from problem definition):
    - session_key: Unique identifier
    - course_id, section_id, teacher_id: Foreign keys
    - duration_minutes: How long the session lasts
    - is_lab: Whether this is a lab session
    - session_number: Which session of the course (1, 2, 3...)

    Mutable attributes (GA optimizes these):
    - day: Which weekday
    - start_time: When it starts (must be in allowed_start_times)
    - room_id: Which room

    Lock attributes (for pre-scheduled sessions):
    - is_locked: Whether this gene is locked (cannot be mutated)
    - lock_type: 'time_only' (room can change) or 'full_lock' (nothing changes)
    - locked_day, locked_start_time, locked_room_id: Original locked values
    """

    # Fixed attributes
    session_key: str
    course_id: int
    course_code: str
    course_name: str
    section_id: int
    section_code: str
    teacher_id: int
    teacher_name: str
    duration_minutes: int
    is_lab: bool
    session_number: int

    # Mutable attributes (what GA optimizes)
    day: str = None
    start_time: str = None
    room_id: Optional[int] = None
    room_code: Optional[str] = None

    # Computed attributes
    end_time: Optional[str] = None
    duration_slots: int = 0  # Number of 30-min slots

    # Lock attributes (for pre-scheduled sessions)
    is_locked: bool = False
    lock_type: Optional[str] = None  # 'time_only' or 'full_lock'
    locked_day: Optional[str] = None
    locked_start_time: Optional[str] = None
    locked_room_id: Optional[int] = None
    
    def __post_init__(self):
        """Calculate derived fields."""
        if self.start_time and self.duration_minutes:
            from classsync_core.utils import calculate_slot_end_time
            self.end_time = calculate_slot_end_time(
                self.start_time, 
                self.duration_minutes
            )
            self.duration_slots = self.duration_minutes // 30
    
    def update_time(self, day: str, start_time: str):
        """Update day and start time, recalculate end time."""
        self.day = day
        self.start_time = start_time
        
        from classsync_core.utils import calculate_slot_end_time
        self.end_time = calculate_slot_end_time(
            start_time, 
            self.duration_minutes
        )
        self.duration_slots = self.duration_minutes // 30
    
    def update_room(self, room_id: int, room_code: str):
        """Update room assignment."""
        self.room_id = room_id
        self.room_code = room_code

    def can_mutate_time(self) -> bool:
        """Check if this gene's time can be mutated."""
        return not self.is_locked

    def can_mutate_room(self) -> bool:
        """Check if this gene's room can be mutated."""
        return not self.is_locked or self.lock_type == 'time_only'

    def restore_lock(self):
        """Restore locked values if this gene was accidentally modified."""
        if not self.is_locked:
            return

        # Always restore time for locked genes
        self.day = self.locked_day
        self.start_time = self.locked_start_time

        # Recalculate end time
        from classsync_core.utils import calculate_slot_end_time
        self.end_time = calculate_slot_end_time(
            self.locked_start_time,
            self.duration_minutes
        )

        # For full locks, also restore room
        if self.lock_type == 'full_lock' and self.locked_room_id is not None:
            self.room_id = self.locked_room_id
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database persistence."""
        return {
            'Session_Key': self.session_key,
            'Course_ID': self.course_id,
            'Course_Code': self.course_code,
            'Course_Name': self.course_name,
            'Section_ID': self.section_id,
            'Section': self.section_code,
            'Teacher_ID': self.teacher_id,
            'Instructor': self.teacher_name,
            'Day': self.day,
            'Start_Time': self.start_time,
            'End_Time': self.end_time,
            'Room_ID': self.room_id,
            'Room': self.room_code,
            'Duration_Minutes': self.duration_minutes,
            'Duration_Slots': self.duration_slots,
            'Is_Lab': self.is_lab,
            'Session_Number': self.session_number
        }


class Chromosome:
    """
    Represents one complete timetable solution.
    Contains all session assignments (genes) for the institution.
    """
    
    def __init__(self, genes: List[Gene] = None):
        """
        Initialize chromosome with genes.
        
        Args:
            genes: List of Gene objects (session assignments)
        """
        self.genes: List[Gene] = genes if genes else []
        self.fitness: Optional[float] = None
        self.hard_violations: Dict[str, int] = {}
        self.soft_scores: Dict[str, float] = {}
        self.is_feasible: bool = False
        self.conflict_details: List[str] = []
        
    def __len__(self) -> int:
        """Number of sessions in this timetable."""
        return len(self.genes)
    
    def copy(self) -> 'Chromosome':
        """Create a deep copy of this chromosome."""
        new_genes = [
            Gene(
                session_key=g.session_key,
                course_id=g.course_id,
                course_code=g.course_code,
                course_name=g.course_name,
                section_id=g.section_id,
                section_code=g.section_code,
                teacher_id=g.teacher_id,
                teacher_name=g.teacher_name,
                duration_minutes=g.duration_minutes,
                is_lab=g.is_lab,
                session_number=g.session_number,
                day=g.day,
                start_time=g.start_time,
                room_id=g.room_id,
                room_code=g.room_code,
                # Copy lock attributes
                is_locked=g.is_locked,
                lock_type=g.lock_type,
                locked_day=g.locked_day,
                locked_start_time=g.locked_start_time,
                locked_room_id=g.locked_room_id
            )
            for g in self.genes
        ]

        new_chromosome = Chromosome(new_genes)
        new_chromosome.fitness = self.fitness
        new_chromosome.is_feasible = self.is_feasible

        return new_chromosome
    
    def get_gene_by_index(self, index: int) -> Gene:
        """Get gene at specific index."""
        return self.genes[index]
    
    def get_genes_by_section(self, section_id: int) -> List[Gene]:
        """Get all genes for a specific section."""
        return [g for g in self.genes if g.section_id == section_id]
    
    def get_genes_by_teacher(self, teacher_id: int) -> List[Gene]:
        """Get all genes for a specific teacher."""
        return [g for g in self.genes if g.teacher_id == teacher_id]
    
    def get_genes_by_day(self, day: str) -> List[Gene]:
        """Get all genes scheduled on a specific day."""
        return [g for g in self.genes if g.day == day]
    
    def get_genes_by_room(self, room_id: int) -> List[Gene]:
        """Get all genes in a specific room."""
        return [g for g in self.genes if g.room_id == room_id]
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert chromosome to pandas DataFrame for export."""
        return pd.DataFrame([g.to_dict() for g in self.genes])
    
    def to_schedule_dict(self) -> Dict:
        """
        Convert to schedule dictionary for API response.
        
        Returns:
            {
                'sessions': [...],
                'fitness': float,
                'is_feasible': bool,
                'statistics': {...}
            }
        """
        return {
            'sessions': [g.to_dict() for g in self.genes],
            'fitness': self.fitness,
            'is_feasible': self.is_feasible,
            'hard_violations': self.hard_violations,
            'soft_scores': self.soft_scores,
            'statistics': self.get_statistics()
        }
    
    def get_statistics(self) -> Dict:
        """Calculate timetable statistics."""
        if not self.genes:
            return {}
        
        # Count sessions per day
        day_counts = {}
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            day_counts[day] = len(self.get_genes_by_day(day))
        
        # Count lab vs theory
        lab_count = sum(1 for g in self.genes if g.is_lab)
        theory_count = len(self.genes) - lab_count
        
        # Count scheduled vs unscheduled
        scheduled = sum(1 for g in self.genes if g.day is not None)
        unscheduled = len(self.genes) - scheduled
        
        return {
            'total_sessions': len(self.genes),
            'scheduled_sessions': scheduled,
            'unscheduled_sessions': unscheduled,
            'lab_sessions': lab_count,
            'theory_sessions': theory_count,
            'sessions_per_day': day_counts,
            'coverage_percentage': (scheduled / len(self.genes) * 100) if self.genes else 0
        }
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Chromosome(sessions={len(self.genes)}, "
            f"fitness={self.fitness:.2f if self.fitness else 'N/A'}, "
            f"feasible={self.is_feasible})"
        )
