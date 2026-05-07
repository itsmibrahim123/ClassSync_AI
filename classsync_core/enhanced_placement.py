"""
Enhanced placement strategies - CORRECTED VERSION.
Rules:
1. NEVER allow teacher overlaps (hard constraint)
2. NEVER allow room overlaps (hard constraint)
3. NEVER allow section overlaps (hard constraint)
4. Distribute evenly across all 5 days
5. 100% coverage target
"""

import pandas as pd
import random
from typing import List, Tuple, Dict, Any
from collections import defaultdict


class EnhancedPlacer:
    """
    Enhanced placement with proper constraint enforcement.
    """

    def __init__(self, working_days: List[str], slot_duration_minutes: int):
        self.working_days = working_days
        self.slot_duration_minutes = slot_duration_minutes
        self.forced_log = []
        self.missed_sessions = []

    def place_schedule(
        self,
        sessions_df: pd.DataFrame,
        slots: List[Tuple],
        rooms_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Place all sessions with even distribution across days.

        Args:
            sessions_df: Sessions to schedule
            slots: Available time slots
            rooms_df: Available rooms

        Returns:
            Schedule DataFrame
        """
        schedule = []

        # Conflict tracking - THESE ARE ALL HARD CONSTRAINTS
        teacher_schedule = defaultdict(lambda: defaultdict(list))  # teacher -> day -> [(start, end)]
        room_schedule = defaultdict(lambda: defaultdict(list))     # room -> day -> [(start, end)]
        section_schedule = defaultdict(lambda: defaultdict(list))  # section -> day -> [(start, end)]

        # Track sessions per day for even distribution
        day_counts = {day: 0 for day in self.working_days}

        # Get room lists
        lab_rooms = rooms_df[rooms_df['Room_Type'].str.lower() == 'lab']['Room_Code'].tolist()
        theory_rooms = rooms_df[rooms_df['Room_Type'].str.lower() == 'lecture_hall']['Room_Code'].tolist()
        all_rooms = rooms_df['Room_Code'].tolist()

        # Prioritize harder sessions (labs first)
        sessions_df = sessions_df.copy()
        sessions_df['Priority'] = sessions_df['Is_Lab'].apply(lambda x: 100 if x else 50)
        sessions_df = sessions_df.sort_values('Priority', ascending=False)

        # STRATEGY: Try to place each session, prefer days with fewer sessions
        for _, session in sessions_df.iterrows():
            placed = self._try_place_with_distribution(
                session, slots, lab_rooms, theory_rooms, all_rooms,
                teacher_schedule, room_schedule, section_schedule,
                schedule, day_counts
            )

            if not placed:
                # Log as missed
                self.missed_sessions.append({
                    'Course': session['Course_Name'],
                    'Section': session['Section_Code'],
                    'Instructor': session['Instructor'],
                    'Is_Lab': session['Is_Lab'],
                    'Reason': 'Could not find valid slot without violating hard constraints'
                })

        return pd.DataFrame(schedule)

    def _try_place_with_distribution(
        self, session, slots, lab_rooms, theory_rooms, all_rooms,
        teacher_schedule, room_schedule, section_schedule, schedule, day_counts
    ) -> bool:
        """
        Try to place session preferring days with fewer sessions.
        NEVER violate hard constraints (teacher/room/section overlaps).
        """

        is_lab = session['Is_Lab']
        duration_slots = int(session['Duration_Minutes'] // self.slot_duration_minutes)
        instructor = session['Instructor']
        section_code = session['Section_Code']

        # Choose appropriate rooms
        available_rooms = lab_rooms if is_lab else theory_rooms
        if not available_rooms:
            available_rooms = all_rooms

        # Sort days by current count (prefer days with fewer sessions)
        sorted_days = sorted(self.working_days, key=lambda d: day_counts[d])

        # Try each day in order of preference
        for day in sorted_days:
            # Get slots for this day
            day_slots = [s for s in slots if s[0] == day]

            # Try each possible consecutive slot combination
            for i in range(len(day_slots) - duration_slots + 1):
                consecutive = day_slots[i:i + duration_slots]
                start_time = consecutive[0][1]
                end_time = consecutive[-1][2]

                # Try each available room
                random.shuffle(available_rooms)  # Randomize for diversity

                for room in available_rooms:
                    # CHECK ALL THREE HARD CONSTRAINTS
                    if self._has_any_conflict(
                        day, start_time, end_time,
                        instructor, room, section_code,
                        teacher_schedule, room_schedule, section_schedule
                    ):
                        continue

                    # NO CONFLICTS - PLACE IT!
                    self._add_assignment(
                        session, day, start_time, end_time, room, duration_slots,
                        teacher_schedule, room_schedule, section_schedule, schedule
                    )

                    # Update day count
                    day_counts[day] += 1

                    return True

        # Could not place without violating constraints
        return False

    def _has_any_conflict(
        self, day, start_time, end_time,
        instructor, room, section,
        teacher_schedule, room_schedule, section_schedule
    ) -> bool:
        """
        Check if placement violates ANY hard constraint.
        Returns True if there's a conflict.
        """
        # Check teacher conflict
        if self._has_time_conflict(day, start_time, end_time, instructor, teacher_schedule):
            return True

        # Check room conflict
        if self._has_time_conflict(day, start_time, end_time, room, room_schedule):
            return True

        # Check section conflict
        if self._has_time_conflict(day, start_time, end_time, section, section_schedule):
            return True

        return False

    def _has_time_conflict(
        self, day, start_time, end_time, resource, schedule_dict
    ) -> bool:
        """
        Check if resource (teacher/room/section) has a time conflict on this day.
        """
        if day not in schedule_dict[resource]:
            return False

        for existing_start, existing_end in schedule_dict[resource][day]:
            if self._times_overlap(start_time, end_time, existing_start, existing_end):
                return True

        return False

    def _times_overlap(self, start1, end1, start2, end2) -> bool:
        """
        Check if two time ranges overlap.
        Returns True if they overlap.
        """
        # No overlap if one ends before the other starts
        return not (end1 <= start2 or end2 <= start1)

    def _add_assignment(
        self, session, day, start_time, end_time, room, duration_slots,
        teacher_schedule, room_schedule, section_schedule, schedule
    ):
        """
        Add assignment to schedule and update all conflict trackers.
        """

        instructor = session['Instructor']
        section_code = session['Section_Code']

        # Add to schedule
        schedule.append({
            'Session_Key': session['Session_Key'],
            'Section_ID': session['Section_ID'],
            'Course_ID': session['Course_ID'],
            'Teacher_ID': session['Teacher_ID'],
            'Course_Code': session['Course_Code'],
            'Course_Name': session['Course_Name'],
            'Instructor': instructor,
            'Section': section_code,
            'Room': room,
            'Weekday': day,
            'Start_Time': start_time,
            'End_Time': end_time,
            'Duration_Slots': duration_slots,
            'Session_Number': session['Session_Number'],
            'Is_Lab': session['Is_Lab']
        })

        # Update all trackers (HARD CONSTRAINTS)
        teacher_schedule[instructor][day].append((start_time, end_time))
        room_schedule[room][day].append((start_time, end_time))
        section_schedule[section_code][day].append((start_time, end_time))