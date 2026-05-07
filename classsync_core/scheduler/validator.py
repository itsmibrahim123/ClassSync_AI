"""
Pre-GA Constraint Validator - Validates constraints before GA execution.
Detects hard conflicts that would make the problem infeasible.
"""

from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from classsync_core.scheduler.config import GAConfig
from classsync_core.utils import slots_overlap, time_to_minutes, calculate_slot_end_time


@dataclass
class ValidationError:
    """Represents a single validation error."""
    error_type: str
    severity: str  # 'hard' (blocks GA) or 'warning' (logged but allowed)
    message: str
    details: Dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of pre-GA validation."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def add_error(self, error: ValidationError):
        if error.severity == 'hard':
            self.errors.append(error)
            self.is_valid = False
        else:
            self.warnings.append(error)

    def to_dict(self) -> Dict:
        return {
            'is_valid': self.is_valid,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': [
                {
                    'type': e.error_type,
                    'severity': e.severity,
                    'message': e.message,
                    'details': e.details
                }
                for e in self.errors
            ],
            'warnings': [
                {
                    'type': w.error_type,
                    'severity': w.severity,
                    'message': w.message,
                    'details': w.details
                }
                for w in self.warnings
            ]
        }


class PreGAValidator:
    """
    Validates constraints before GA execution.

    Checks for:
    1. Locked assignment conflicts (same teacher/room at same time)
    2. Locked slots vs teacher day-off conflicts
    3. Locked times outside allowed time windows
    4. Room locked to overlapping sessions
    5. Instructor weekly load exceeded
    6. Locked slots in blocked institutional windows
    """

    def __init__(
        self,
        config: GAConfig,
        sessions_df,
        rooms_df,
        teacher_constraints: List[Dict] = None,
        room_constraints: List[Dict] = None,
        locked_assignments: List[Dict] = None
    ):
        self.config = config
        self.sessions_df = sessions_df
        self.rooms_df = rooms_df
        self.teacher_constraints = teacher_constraints or []
        self.room_constraints = room_constraints or []
        self.locked_assignments = locked_assignments or []

        # Build lookup indexes
        self._build_indexes()

    def _build_indexes(self):
        """Build lookup indexes for efficient validation."""
        # Teacher day-offs: teacher_id -> set of days
        self.teacher_day_offs = defaultdict(set)
        # Teacher blocked slots: teacher_id -> [(day, start, end)]
        self.teacher_blocked_slots = defaultdict(list)

        for tc in self.teacher_constraints:
            teacher_id = tc['teacher_id']
            constraint_type = tc.get('constraint_type')

            if constraint_type == 'day_off':
                days = tc.get('days', [tc.get('day')] if tc.get('day') else [])
                for day in days:
                    if day:
                        self.teacher_day_offs[teacher_id].add(day)

            elif constraint_type == 'blocked_slot':
                day = tc.get('day')
                start = tc.get('start_time')
                end = tc.get('end_time')
                if day and start and end:
                    self.teacher_blocked_slots[teacher_id].append((day, start, end))

        # Room blocked slots: room_id -> [(day, start, end)]
        self.room_blocked_slots = defaultdict(list)
        # Room day-offs: room_id -> set of days
        self.room_day_offs = defaultdict(set)

        for rc in self.room_constraints:
            room_id = rc.get('room_id')
            constraint_type = rc.get('constraint_type')

            if constraint_type == 'day_off':
                days = rc.get('days', [rc.get('day')] if rc.get('day') else [])
                for day in days:
                    if day:
                        self.room_day_offs[room_id].add(day)

            elif constraint_type == 'blocked_slot':
                day = rc.get('day')
                start = rc.get('start_time')
                end = rc.get('end_time')
                if day and start and end:
                    self.room_blocked_slots[room_id].append((day, start, end))

        # Session lookup: session_key -> session info
        self.session_lookup = {}
        for _, session in self.sessions_df.iterrows():
            self.session_lookup[session['Session_Key']] = session.to_dict()

        # Room capacity lookup
        self.room_capacities = {}
        for _, room in self.rooms_df.iterrows():
            self.room_capacities[room['Room_ID']] = room.get('Capacity', 50)

    def validate(self) -> ValidationResult:
        """
        Run all validation checks.

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult(is_valid=True)

        # 1. Validate locked assignments don't conflict with each other
        self._validate_locked_assignment_conflicts(result)

        # 2. Validate locked slots vs teacher constraints
        self._validate_locked_vs_teacher_constraints(result)

        # 3. Validate locked times are within allowed windows
        self._validate_locked_times_in_bounds(result)

        # 4. Validate room locks don't overlap
        self._validate_room_lock_conflicts(result)

        # 5. Validate instructor weekly load
        self._validate_instructor_weekly_load(result)

        # 6. Validate locked slots not in blocked institutional windows
        self._validate_locked_not_in_blocked_windows(result)

        # 7. Validate locked assignments reference valid sessions
        self._validate_locked_session_references(result)

        # 8. Validate room constraints
        self._validate_locked_vs_room_constraints(result)

        return result

    def _validate_locked_assignment_conflicts(self, result: ValidationResult):
        """Check if any locked assignments conflict with each other (same teacher at same time)."""
        # Group locked assignments by teacher
        teacher_locks = defaultdict(list)

        for lock in self.locked_assignments:
            session_key = lock.get('session_key')
            session = self.session_lookup.get(session_key)
            if not session:
                continue

            teacher_id = session.get('Teacher_ID') or lock.get('teacher_id')
            day = lock.get('day')
            start_time = lock.get('start_time')
            duration = session.get('Duration_Minutes', 90)
            end_time = calculate_slot_end_time(start_time, duration)

            teacher_locks[teacher_id].append({
                'session_key': session_key,
                'day': day,
                'start_time': start_time,
                'end_time': end_time
            })

        # Check for overlaps within each teacher's locks
        for teacher_id, locks in teacher_locks.items():
            for i in range(len(locks)):
                for j in range(i + 1, len(locks)):
                    lock1, lock2 = locks[i], locks[j]

                    if lock1['day'] == lock2['day']:
                        if slots_overlap(
                            lock1['start_time'], lock1['end_time'],
                            lock2['start_time'], lock2['end_time']
                        ):
                            result.add_error(ValidationError(
                                error_type='locked_teacher_conflict',
                                severity='hard',
                                message=f"Teacher {teacher_id} has overlapping locked assignments",
                                details={
                                    'teacher_id': teacher_id,
                                    'session_1': lock1['session_key'],
                                    'session_2': lock2['session_key'],
                                    'day': lock1['day'],
                                    'time_1': f"{lock1['start_time']}-{lock1['end_time']}",
                                    'time_2': f"{lock2['start_time']}-{lock2['end_time']}"
                                }
                            ))

    def _validate_locked_vs_teacher_constraints(self, result: ValidationResult):
        """Check if locked assignments conflict with teacher day-offs or blocked slots."""
        for lock in self.locked_assignments:
            session_key = lock.get('session_key')
            session = self.session_lookup.get(session_key)
            if not session:
                continue

            teacher_id = session.get('Teacher_ID') or lock.get('teacher_id')
            day = lock.get('day')
            start_time = lock.get('start_time')
            duration = session.get('Duration_Minutes', 90)
            end_time = calculate_slot_end_time(start_time, duration)

            # Check day-off conflicts
            if day in self.teacher_day_offs.get(teacher_id, set()):
                result.add_error(ValidationError(
                    error_type='locked_dayoff_conflict',
                    severity='hard',
                    message=f"Locked assignment conflicts with teacher day-off",
                    details={
                        'session_key': session_key,
                        'teacher_id': teacher_id,
                        'locked_day': day,
                        'teacher_day_off': day
                    }
                ))

            # Check blocked slot conflicts
            for blocked_day, blocked_start, blocked_end in self.teacher_blocked_slots.get(teacher_id, []):
                if day == blocked_day and slots_overlap(start_time, end_time, blocked_start, blocked_end):
                    result.add_error(ValidationError(
                        error_type='locked_blocked_slot_conflict',
                        severity='hard',
                        message=f"Locked assignment conflicts with teacher blocked slot",
                        details={
                            'session_key': session_key,
                            'teacher_id': teacher_id,
                            'locked_time': f"{day} {start_time}-{end_time}",
                            'blocked_time': f"{blocked_day} {blocked_start}-{blocked_end}"
                        }
                    ))

    def _validate_locked_times_in_bounds(self, result: ValidationResult):
        """Check if locked times are within allowed institutional time windows."""
        day_start_minutes = time_to_minutes(self.config.day_start_time)
        day_end_minutes = time_to_minutes(self.config.day_end_time)

        for lock in self.locked_assignments:
            session_key = lock.get('session_key')
            session = self.session_lookup.get(session_key)
            if not session:
                continue

            day = lock.get('day')
            start_time = lock.get('start_time')
            duration = session.get('Duration_Minutes', 90)
            end_time = calculate_slot_end_time(start_time, duration)

            start_minutes = time_to_minutes(start_time)
            end_minutes = time_to_minutes(end_time)

            # Check if day is valid
            if day not in self.config.working_days:
                result.add_error(ValidationError(
                    error_type='locked_invalid_day',
                    severity='hard',
                    message=f"Locked assignment on non-working day",
                    details={
                        'session_key': session_key,
                        'locked_day': day,
                        'working_days': self.config.working_days
                    }
                ))

            # Check if start time is too early
            if start_minutes < day_start_minutes:
                result.add_error(ValidationError(
                    error_type='locked_before_day_start',
                    severity='hard',
                    message=f"Locked assignment starts before institution day start",
                    details={
                        'session_key': session_key,
                        'locked_start': start_time,
                        'day_start': self.config.day_start_time
                    }
                ))

            # Check if end time is too late
            if end_minutes > day_end_minutes:
                result.add_error(ValidationError(
                    error_type='locked_after_day_end',
                    severity='hard',
                    message=f"Locked assignment ends after institution day end",
                    details={
                        'session_key': session_key,
                        'locked_end': end_time,
                        'day_end': self.config.day_end_time
                    }
                ))

            # Check if start time is in allowed start times
            if start_time not in self.config.allowed_start_times:
                result.add_error(ValidationError(
                    error_type='locked_invalid_start_time',
                    severity='hard',
                    message=f"Locked assignment has invalid start time",
                    details={
                        'session_key': session_key,
                        'locked_start': start_time,
                        'allowed_start_times': self.config.allowed_start_times
                    }
                ))

    def _validate_room_lock_conflicts(self, result: ValidationResult):
        """Check if any room is locked to overlapping sessions."""
        # Group locked assignments by room
        room_locks = defaultdict(list)

        for lock in self.locked_assignments:
            room_id = lock.get('room_id')
            if room_id is None:
                continue  # Room not specified in lock

            session_key = lock.get('session_key')
            session = self.session_lookup.get(session_key)
            if not session:
                continue

            day = lock.get('day')
            start_time = lock.get('start_time')
            duration = session.get('Duration_Minutes', 90)
            end_time = calculate_slot_end_time(start_time, duration)

            room_locks[room_id].append({
                'session_key': session_key,
                'day': day,
                'start_time': start_time,
                'end_time': end_time
            })

        # Check for overlaps within each room's locks
        for room_id, locks in room_locks.items():
            for i in range(len(locks)):
                for j in range(i + 1, len(locks)):
                    lock1, lock2 = locks[i], locks[j]

                    if lock1['day'] == lock2['day']:
                        if slots_overlap(
                            lock1['start_time'], lock1['end_time'],
                            lock2['start_time'], lock2['end_time']
                        ):
                            result.add_error(ValidationError(
                                error_type='locked_room_conflict',
                                severity='hard',
                                message=f"Room {room_id} has overlapping locked sessions",
                                details={
                                    'room_id': room_id,
                                    'session_1': lock1['session_key'],
                                    'session_2': lock2['session_key'],
                                    'day': lock1['day'],
                                    'time_1': f"{lock1['start_time']}-{lock1['end_time']}",
                                    'time_2': f"{lock2['start_time']}-{lock2['end_time']}"
                                }
                            ))

    def _validate_instructor_weekly_load(self, result: ValidationResult):
        """Check if locked assignments exceed instructor weekly load limits."""
        # Calculate locked hours per teacher
        teacher_locked_hours = defaultdict(float)

        for lock in self.locked_assignments:
            session_key = lock.get('session_key')
            session = self.session_lookup.get(session_key)
            if not session:
                continue

            teacher_id = session.get('Teacher_ID') or lock.get('teacher_id')
            duration = session.get('Duration_Minutes', 90)
            teacher_locked_hours[teacher_id] += duration / 60.0

        # Check against limits (default 40 hours/week)
        max_weekly_hours = getattr(self.config, 'max_teacher_weekly_hours', 40)

        for teacher_id, locked_hours in teacher_locked_hours.items():
            if locked_hours > max_weekly_hours:
                result.add_error(ValidationError(
                    error_type='locked_exceeds_weekly_load',
                    severity='hard',
                    message=f"Locked assignments exceed teacher weekly load limit",
                    details={
                        'teacher_id': teacher_id,
                        'locked_hours': round(locked_hours, 2),
                        'max_weekly_hours': max_weekly_hours
                    }
                ))
            elif locked_hours > max_weekly_hours * 0.8:
                # Warning if approaching limit
                result.add_error(ValidationError(
                    error_type='locked_approaching_weekly_load',
                    severity='warning',
                    message=f"Locked assignments approaching teacher weekly load limit",
                    details={
                        'teacher_id': teacher_id,
                        'locked_hours': round(locked_hours, 2),
                        'max_weekly_hours': max_weekly_hours
                    }
                ))

    def _validate_locked_not_in_blocked_windows(self, result: ValidationResult):
        """Check if locked assignments are in institutional blocked windows."""
        for lock in self.locked_assignments:
            session_key = lock.get('session_key')
            session = self.session_lookup.get(session_key)
            if not session:
                continue

            day = lock.get('day')
            start_time = lock.get('start_time')
            duration = session.get('Duration_Minutes', 90)
            end_time = calculate_slot_end_time(start_time, duration)

            if self.config.is_blocked(day, start_time, end_time):
                result.add_error(ValidationError(
                    error_type='locked_in_blocked_window',
                    severity='hard',
                    message=f"Locked assignment falls within institutional blocked window",
                    details={
                        'session_key': session_key,
                        'locked_time': f"{day} {start_time}-{end_time}",
                        'blocked_windows': self.config.blocked_windows
                    }
                ))

    def _validate_locked_session_references(self, result: ValidationResult):
        """Check if locked assignments reference valid sessions."""
        for lock in self.locked_assignments:
            session_key = lock.get('session_key')
            if session_key not in self.session_lookup:
                result.add_error(ValidationError(
                    error_type='locked_invalid_session',
                    severity='hard',
                    message=f"Locked assignment references non-existent session",
                    details={
                        'session_key': session_key,
                        'available_sessions': list(self.session_lookup.keys())[:10]  # First 10 for reference
                    }
                ))

    def _validate_locked_vs_room_constraints(self, result: ValidationResult):
        """Check if locked room assignments conflict with room constraints."""
        for lock in self.locked_assignments:
            room_id = lock.get('room_id')
            if room_id is None:
                continue

            session_key = lock.get('session_key')
            session = self.session_lookup.get(session_key)
            if not session:
                continue

            day = lock.get('day')
            start_time = lock.get('start_time')
            duration = session.get('Duration_Minutes', 90)
            end_time = calculate_slot_end_time(start_time, duration)

            # Check room day-off conflicts
            if day in self.room_day_offs.get(room_id, set()):
                result.add_error(ValidationError(
                    error_type='locked_room_dayoff_conflict',
                    severity='hard',
                    message=f"Locked room assignment conflicts with room day-off",
                    details={
                        'session_key': session_key,
                        'room_id': room_id,
                        'locked_day': day
                    }
                ))

            # Check room blocked slot conflicts
            for blocked_day, blocked_start, blocked_end in self.room_blocked_slots.get(room_id, []):
                if day == blocked_day and slots_overlap(start_time, end_time, blocked_start, blocked_end):
                    result.add_error(ValidationError(
                        error_type='locked_room_blocked_slot_conflict',
                        severity='hard',
                        message=f"Locked room assignment conflicts with room blocked slot",
                        details={
                            'session_key': session_key,
                            'room_id': room_id,
                            'locked_time': f"{day} {start_time}-{end_time}",
                            'blocked_time': f"{blocked_day} {blocked_start}-{blocked_end}"
                        }
                    ))
