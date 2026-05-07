"""
Utility functions for timetable optimization.
"""

from datetime import datetime, time, timedelta
from typing import List, Tuple, Set, Union


def parse_time(time_str: str) -> time:
    """Parse time string (HH:MM) to time object."""
    h, m = map(int, time_str.split(':'))
    return time(h, m)


def time_to_minutes(t: Union[time, str]) -> int:
    """Convert time to minutes since midnight."""
    if isinstance(t, str):
        t = parse_time(t)
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    """Convert minutes since midnight to time object."""
    return time((minutes // 60) % 24, minutes % 60)


def slots_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """
    Check if two time slots overlap.

    Args:
        start1, end1: First slot times (HH:MM format)
        start2, end2: Second slot times (HH:MM format)

    Returns:
        True if slots overlap
    """
    s1_min = time_to_minutes(parse_time(start1))
    e1_min = time_to_minutes(parse_time(end1))
    s2_min = time_to_minutes(parse_time(start2))
    e2_min = time_to_minutes(parse_time(end2))

    return not (e1_min <= s2_min or e2_min <= s1_min)


def find_consecutive_slots(
        day: str,
        required_slots: int,
        all_slots: List[Tuple[str, str, str]],
        used_slots: Set[Tuple]
) -> List[Tuple[str, str, str]]:
    """
    Find N consecutive available time slots on a given day.

    Args:
        day: Day name (e.g., 'Monday')
        required_slots: Number of consecutive slots needed
        all_slots: List of (day, start_time, end_time) tuples
        used_slots: Set of already used (day, start_time, end_time) tuples

    Returns:
        List of consecutive slots, or empty list if not found
    """
    day_slots = [s for s in all_slots if s[0] == day and s not in used_slots]

    if len(day_slots) < required_slots:
        return []

    # Check each possible starting position
    for i in range(len(day_slots) - required_slots + 1):
        consecutive = [day_slots[i]]

        for j in range(1, required_slots):
            # Check if next slot is consecutive (current end == next start)
            if day_slots[i + j][1] == consecutive[-1][2]:
                consecutive.append(day_slots[i + j])
            else:
                break

        if len(consecutive) == required_slots:
            return consecutive

    return []


def calculate_slot_end_time(start_time: str, duration_minutes: int) -> str:
    """
    Calculate end time given start time and duration.

    Args:
        start_time: Start time in HH:MM format
        duration_minutes: Duration in minutes

    Returns:
        End time in HH:MM format
    """
    start = parse_time(start_time)
    start_minutes = time_to_minutes(start)
    end_minutes = start_minutes + duration_minutes
    end = minutes_to_time(end_minutes)
    return f"{end.hour:02d}:{end.minute:02d}"


class ConflictChecker:
    """Fast conflict detection using index structures."""

    def __init__(self):
        # Index: (day, start_time, resource_type) -> set of resource_ids
        self.resource_index = {}

    def add_assignment(
            self,
            day: str,
            start_time: str,
            teacher_id: str,
            room_id: str,
            section_id: str
    ):
        """Register an assignment in the conflict index."""
        key = (day, start_time, 'teacher')
        if key not in self.resource_index:
            self.resource_index[key] = set()
        self.resource_index[key].add(teacher_id)

        key = (day, start_time, 'room')
        if key not in self.resource_index:
            self.resource_index[key] = set()
        self.resource_index[key].add(room_id)

        key = (day, start_time, 'section')
        if key not in self.resource_index:
            self.resource_index[key] = set()
        self.resource_index[key].add(section_id)

    def has_conflict(
            self,
            day: str,
            start_time: str,
            teacher_id: str,
            room_id: str,
            section_id: str
    ) -> bool:
        """Check if assignment would create a conflict."""
        # Check teacher
        key = (day, start_time, 'teacher')
        if key in self.resource_index and teacher_id in self.resource_index[key]:
            return True

        # Check room
        key = (day, start_time, 'room')
        if key in self.resource_index and room_id in self.resource_index[key]:
            return True

        # Check section
        key = (day, start_time, 'section')
        if key in self.resource_index and section_id in self.resource_index[key]:
            return True

        return False

    def clear(self):
        """Clear all indexes."""
        self.resource_index.clear()