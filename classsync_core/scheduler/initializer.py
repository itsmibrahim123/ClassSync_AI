"""
Population Initializer - Creates initial population of chromosomes.
Uses both random and heuristic-seeded initialization.
"""
import pandas as pd
import random
from typing import List
from classsync_core.scheduler.chromosome import Chromosome, Gene
from classsync_core.scheduler.config import GAConfig
from classsync_core.utils import calculate_slot_end_time, time_to_minutes, slots_overlap


class PopulationInitializer:

    def __init__(
        self,
        config: GAConfig,
        sessions_df: pd.DataFrame,
        rooms_df: pd.DataFrame,
        locked_assignments: list = None
    ):
        self.config = config
        self.sessions_df = sessions_df
        self.rooms_df = rooms_df
        self.locked_assignments = locked_assignments or []

        # Build locked assignments map for quick lookup
        self.locked_map = {la['session_key']: la for la in self.locked_assignments}

        # Separate lab and theory rooms
        self.lab_rooms = rooms_df[
            rooms_df['Room_Type'].str.lower().str.contains('lab')
        ]['Room_Code'].tolist()

        self.theory_rooms = rooms_df[
            ~rooms_df['Room_Type'].str.lower().str.contains('lab')
        ]['Room_Code'].tolist()

        # All allowed time slots
        self.time_slots = self._generate_time_slots()


    def _generate_time_slots(self) -> List[tuple]:
        """Generate all valid (day, start_time) combinations."""
        slots = []
        for day in self.config.working_days:
            for start_time in self.config.allowed_start_times:
                # Skip if blocked
                end_time = calculate_slot_end_time(start_time, 30)  # Temporary end
                if not self.config.is_blocked(day, start_time, end_time):
                    slots.append((day, start_time))
        return slots


    def create_population(
            self,
            population_size: int,
            heuristic_seed_ratio: float = 0.20
    ) -> List[Chromosome]:
        """
        Create initial population.

        Args:
            population_size: Number of chromosomes to create
            heuristic_seed_ratio: Fraction to seed with heuristic (rest random)

        Returns:
            List of chromosomes
        """
        population = []

        # Number of heuristic-seeded individuals
        heuristic_count = int(population_size * heuristic_seed_ratio)
        random_count = population_size - heuristic_count

        # Create heuristic-seeded chromosomes
        for i in range(heuristic_count):
            chromosome = self._create_heuristic_chromosome()
            population.append(chromosome)

        # Create random chromosomes
        for i in range(random_count):
            chromosome = self._create_random_chromosome()
            population.append(chromosome)

        return population


    def _create_random_chromosome(self) -> Chromosome:
        """Create chromosome with completely random assignments (respecting locks)."""
        genes = []
        day_end_minutes = time_to_minutes(self.config.day_end_time)

        for _, session in self.sessions_df.iterrows():
            session_key = session['Session_Key']
            duration = session['Duration_Minutes']

            # Check if this session has a locked assignment
            if session_key in self.locked_map:
                gene = self._create_locked_gene(session, self.locked_map[session_key])
                genes.append(gene)
                continue

            # Filter valid slots for this duration
            valid_slots = []
            for day, start in self.time_slots:
                end_time = calculate_slot_end_time(start, duration)
                if time_to_minutes(end_time) <= day_end_minutes:
                    valid_slots.append((day, start))

            # If no valid slots (unlikely but possible for very long sessions), fall back to all
            if not valid_slots:
                valid_slots = self.time_slots

            # Random day and time
            day, start_time = random.choice(valid_slots)

            # Random room (appropriate type)
            if session['Is_Lab']:
                room_code = random.choice(self.lab_rooms) if self.lab_rooms else random.choice(
                    self.rooms_df['Room_Code'].tolist())
            else:
                room_code = random.choice(self.theory_rooms) if self.theory_rooms else random.choice(
                    self.rooms_df['Room_Code'].tolist())

            # Find room ID
            room_row = self.rooms_df[self.rooms_df['Room_Code'] == room_code].iloc[0]
            room_id = room_row.get('Room_ID', hash(room_code) % 10000)

            # Create gene
            gene = Gene(
                session_key=session['Session_Key'],
                course_id=session['Course_ID'],
                course_code=session['Course_Code'],
                course_name=session['Course_Name'],
                section_id=session['Section_ID'],
                section_code=session['Section_Code'],
                teacher_id=session['Teacher_ID'],
                teacher_name=session['Instructor'],
                duration_minutes=session['Duration_Minutes'],
                is_lab=session['Is_Lab'],
                session_number=session['Session_Number'],
                day=day,
                start_time=start_time,
                room_id=room_id,
                room_code=room_code
            )

            genes.append(gene)

        return Chromosome(genes)

    def _create_locked_gene(self, session, lock: dict) -> Gene:
        """Create a gene with locked attributes from a lock assignment."""
        day = lock['day']
        start_time = lock['start_time']
        lock_type = lock.get('lock_type', 'time_only')
        room_id = lock.get('room_id')
        room_code = None

        # If room is specified in lock, use it
        if room_id is not None:
            room_rows = self.rooms_df[self.rooms_df['Room_ID'] == room_id]
            if not room_rows.empty:
                room_code = room_rows.iloc[0]['Room_Code']

        # If no room specified or not found, assign appropriate room type
        if room_code is None:
            if session['Is_Lab']:
                room_code = random.choice(self.lab_rooms) if self.lab_rooms else \
                    random.choice(self.rooms_df['Room_Code'].tolist())
            else:
                room_code = random.choice(self.theory_rooms) if self.theory_rooms else \
                    random.choice(self.rooms_df['Room_Code'].tolist())
            room_row = self.rooms_df[self.rooms_df['Room_Code'] == room_code].iloc[0]
            room_id = room_row.get('Room_ID', hash(room_code) % 10000)

        return Gene(
            session_key=session['Session_Key'],
            course_id=session['Course_ID'],
            course_code=session['Course_Code'],
            course_name=session['Course_Name'],
            section_id=session['Section_ID'],
            section_code=session['Section_Code'],
            teacher_id=session['Teacher_ID'],
            teacher_name=session['Instructor'],
            duration_minutes=session['Duration_Minutes'],
            is_lab=session['Is_Lab'],
            session_number=session['Session_Number'],
            day=day,
            start_time=start_time,
            room_id=room_id,
            room_code=room_code,
            # Lock attributes
            is_locked=True,
            lock_type=lock_type,
            locked_day=day,
            locked_start_time=start_time,
            locked_room_id=room_id if lock_type == 'full_lock' else None
        )


    def _create_heuristic_chromosome(self) -> Chromosome:
        """
        Create chromosome using greedy heuristic.
        Places sessions one-by-one avoiding conflicts.
        Locked assignments are placed first with their fixed values.
        """
        genes = []
        day_end_minutes = time_to_minutes(self.config.day_end_time)

        # Track used resources with time ranges
        # Structure: {id: {day: [(start, end)]}}
        teacher_schedule = {}
        section_schedule = {}
        room_schedule = {}  # Added room schedule tracking

        # STEP 1: Place locked assignments first
        for _, session in self.sessions_df.iterrows():
            session_key = session['Session_Key']
            if session_key in self.locked_map:
                lock = self.locked_map[session_key]
                gene = self._create_locked_gene(session, lock)
                genes.append(gene)

                # Register locked slots as occupied
                self._add_booking(teacher_schedule, session['Teacher_ID'], gene.day, gene.start_time, gene.end_time)
                self._add_booking(section_schedule, session['Section_ID'], gene.day, gene.start_time, gene.end_time)
                if gene.room_id:
                    self._add_booking(room_schedule, gene.room_code, gene.day, gene.start_time, gene.end_time)

        # Sort remaining (non-locked) sessions by constraint difficulty (labs first, then longer durations)
        locked_keys = set(self.locked_map.keys())
        remaining_sessions = self.sessions_df[~self.sessions_df['Session_Key'].isin(locked_keys)]
        sessions = remaining_sessions.sort_values(
            by=['Is_Lab', 'Duration_Minutes'],
            ascending=[False, False]
        )

        # STEP 2: Place remaining sessions avoiding conflicts
        for _, session in sessions.iterrows():
            duration = session['Duration_Minutes']
            
            # Filter valid slots for this duration
            valid_slots = []
            for day, start in self.time_slots:
                end_time = calculate_slot_end_time(start, duration)
                if time_to_minutes(end_time) <= day_end_minutes:
                    valid_slots.append((day, start, end_time))
            
            if not valid_slots:
                # Fallback
                valid_slots = [
                    (d, s, calculate_slot_end_time(s, duration)) 
                    for d, s in self.time_slots
                ]

            # Try to find valid slot
            valid_slot_found = False
            attempts = 0
            max_attempts = 50

            # Get available rooms
            available_rooms = self.lab_rooms if session['Is_Lab'] else self.theory_rooms
            if not available_rooms:
                available_rooms = self.rooms_df['Room_Code'].tolist()

            random.shuffle(available_rooms)

            while not valid_slot_found and attempts < max_attempts:
                attempts += 1

                # Pick random day and time
                day, start_time, end_time = random.choice(valid_slots)

                # Check if blocked
                if self.config.is_blocked(day, start_time, end_time):
                    continue

                # Try each room
                for room_code in available_rooms:
                    room_row = self.rooms_df[self.rooms_df['Room_Code'] == room_code].iloc[0]
                    room_id = room_row.get('Room_ID', hash(room_code) % 10000)

                    # 1. Check Room Conflict
                    if self._has_overlap(room_schedule, room_code, day, start_time, end_time):
                        continue

                    # 2. Check Teacher Conflict
                    teacher_id = session['Teacher_ID']
                    if self._has_overlap(teacher_schedule, teacher_id, day, start_time, end_time):
                        continue

                    # 3. Check Section Conflict
                    section_id = session['Section_ID']
                    if self._has_overlap(section_schedule, section_id, day, start_time, end_time):
                        continue

                    # Valid placement found!
                    gene = Gene(
                        session_key=session['Session_Key'],
                        course_id=session['Course_ID'],
                        course_code=session['Course_Code'],
                        course_name=session['Course_Name'],
                        section_id=session['Section_ID'],
                        section_code=session['Section_Code'],
                        teacher_id=teacher_id,
                        teacher_name=session['Instructor'],
                        duration_minutes=session['Duration_Minutes'],
                        is_lab=session['Is_Lab'],
                        session_number=session['Session_Number'],
                        day=day,
                        start_time=start_time,
                        room_id=room_id,
                        room_code=room_code
                    )

                    genes.append(gene)

                    # Update schedules
                    self._add_booking(teacher_schedule, teacher_id, day, start_time, end_time)
                    self._add_booking(section_schedule, section_id, day, start_time, end_time)
                    self._add_booking(room_schedule, room_code, day, start_time, end_time)

                    valid_slot_found = True
                    break

                if valid_slot_found:
                    break

            # If no valid slot found after max attempts, add with random assignment
            if not valid_slot_found:
                day, start_time, end_time = random.choice(valid_slots)
                room_code = random.choice(available_rooms)
                room_row = self.rooms_df[self.rooms_df['Room_Code'] == room_code].iloc[0]
                room_id = room_row.get('Room_ID', hash(room_code) % 10000)

                gene = Gene(
                    session_key=session['Session_Key'],
                    course_id=session['Course_ID'],
                    course_code=session['Course_Code'],
                    course_name=session['Course_Name'],
                    section_id=session['Section_ID'],
                    section_code=session['Section_Code'],
                    teacher_id=session['Teacher_ID'],
                    teacher_name=session['Instructor'],
                    duration_minutes=session['Duration_Minutes'],
                    is_lab=session['Is_Lab'],
                    session_number=session['Session_Number'],
                    day=day,
                    start_time=start_time,
                    room_id=room_id,
                    room_code=room_code
                )
                genes.append(gene)

        return Chromosome(genes)

    def _has_overlap(self, schedule_dict, resource_id, day, start, end):
        """Check if resource has overlap in schedule."""
        if resource_id not in schedule_dict:
            return False
        if day not in schedule_dict[resource_id]:
            return False
        
        for booked_start, booked_end in schedule_dict[resource_id][day]:
            if slots_overlap(start, end, booked_start, booked_end):
                return True
        return False

    def _add_booking(self, schedule_dict, resource_id, day, start, end):
        """Add booking to schedule."""
        if resource_id not in schedule_dict:
            schedule_dict[resource_id] = {}
        if day not in schedule_dict[resource_id]:
            schedule_dict[resource_id][day] = []
        
        schedule_dict[resource_id][day].append((start, end))