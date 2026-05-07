"""
Timetable Optimizer - Strategy wrapper for multiple scheduling algorithms.
Supports: GA (genetic algorithm), Heuristic, Hybrid.
"""

import pandas as pd
import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from classsync_core.scheduler import GAEngine, GAConfig, DEFAULT_GA_CONFIG
from classsync_core.scheduler.validator import PreGAValidator, ValidationResult
from classsync_core.models import (
    Timetable, TimetableEntry, Course, Teacher, Room, Section, ConstraintConfig, TimetableStatus, CourseType
)


class ValidationFailedError(Exception):
    """Raised when pre-GA validation fails with hard errors."""
    def __init__(self, validation_result: ValidationResult):
        self.validation_result = validation_result
        super().__init__(f"Pre-GA validation failed with {len(validation_result.errors)} errors")


class TimetableOptimizer:
    """
    Strategy-based optimizer supporting multiple scheduling algorithms.

    Strategies:
    - 'ga': Full genetic algorithm (production default)
    - 'heuristic': Greedy heuristic (fast, lower quality)
    - 'hybrid': GA seeded with heuristic
    """

    def __init__(self, constraint_config: ConstraintConfig, strategy: str = 'ga'):
        """
        Initialize optimizer with constraint configuration.

        Args:
            constraint_config: Database constraint configuration
            strategy: 'ga', 'heuristic', or 'hybrid'
        """
        self.constraint_config = constraint_config
        self.strategy = strategy

        # Convert ConstraintConfig to GAConfig
        self.ga_config = self._build_ga_config(constraint_config)

    def _build_ga_config(self, cc: ConstraintConfig) -> GAConfig:
        """Convert database ConstraintConfig to GAConfig."""
        from classsync_core.utils import calculate_slot_end_time, time_to_minutes

        # Start with defaults
        config = GAConfig()

        # Override from database config
        config.working_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        config.day_start_time = cc.start_time
        config.day_end_time = cc.end_time
        config.slot_duration_minutes = cc.timeslot_duration_minutes

        # Calculate allowed start times based on slot duration
        allowed_starts = []
        current_time = cc.start_time
        day_end_minutes = time_to_minutes(cc.end_time)
        
        while time_to_minutes(current_time) < day_end_minutes:
            allowed_starts.append(current_time)
            # Move to next slot
            current_time = calculate_slot_end_time(current_time, cc.timeslot_duration_minutes)
        
        config.allowed_start_times = allowed_starts

        # Parse blocked windows from JSON if present
        if cc.optional_constraints and isinstance(cc.optional_constraints, dict):
            blocked_windows = cc.optional_constraints.get('blocked_windows', {})
            if blocked_windows:
                config.blocked_windows = blocked_windows

        # Parse Soft Constraints
        if cc.soft_constraints and isinstance(cc.soft_constraints, dict):
            sc = cc.soft_constraints

            # Helper to safely get weight and apply scaling (x10)
            def apply_weight(config_attr, sc_key, default_weight):
                if sc_key in sc:
                    item = sc[sc_key]
                    if item.get('enabled', True):
                        # Use provided weight or default, then scale
                        weight = item.get('weight', default_weight)
                        setattr(config, config_attr, float(weight * 10.0))
                    else:
                        # If disabled, set weight to 0
                        setattr(config, config_attr, 0.0)

            # Map DB keys to GAConfig attributes
            # Defaults in DB are typically 5-9, GA expects ~50-100, so x10 is appropriate
            apply_weight('weight_minimize_early_classes', 'minimize_early_morning', 6)
            apply_weight('weight_minimize_late_classes', 'minimize_late_evening', 6)
            apply_weight('weight_minimize_gaps_teachers', 'minimize_teacher_gaps', 8)
            apply_weight('weight_minimize_gaps_students', 'compact_student_schedules', 7) # Maps to student gaps
            apply_weight('weight_room_type_match', 'room_type_preference', 8)
            apply_weight('weight_teacher_preference', 'teacher_time_preferences', 9)

            # Update thresholds
            if 'minimize_early_morning' in sc:
                config.early_class_threshold = sc['minimize_early_morning'].get('threshold', config.early_class_threshold)
            
            if 'minimize_late_evening' in sc:
                config.late_class_threshold = sc['minimize_late_evening'].get('threshold', config.late_class_threshold)

        # Optimization settings
        config.generations = int(cc.max_optimization_time_seconds * 1.5)  # Rough estimate
        config.min_acceptable_fitness = cc.min_acceptable_score * 10  # Scale to 0-1000

        return config

    def generate_timetable(
        self,
        db: Session,
        institution_id: int,
        population_size: int = 50,
        generations: int = 150,
        teacher_constraints: Optional[list] = None,
        room_constraints: Optional[list] = None,
        locked_assignments: Optional[list] = None,
        progress_callback: Optional[callable] = None,
        random_seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate optimized timetable.

        Args:
            db: Database session
            institution_id: Institution ID
            population_size: GA population size
            generations: Number of GA generations
            teacher_constraints: List of teacher availability constraints
            room_constraints: List of room availability constraints
            locked_assignments: Pre-scheduled sessions to respect
            progress_callback: Optional progress update function
            random_seed: Optional seed for reproducible generation

        Returns:
            Dictionary with timetable results
        """
        start_time = time.time()

        # 1. Fetch data from database
        sessions_df = self._prepare_sessions_data(db, institution_id)
        rooms_df = self._prepare_rooms_data(db, institution_id)

        print(f"[Optimizer] Loaded {len(sessions_df)} sessions and {len(rooms_df)} rooms")
        if teacher_constraints:
            print(f"[Optimizer] Teacher constraints: {len(teacher_constraints)}")
        if room_constraints:
            print(f"[Optimizer] Room constraints: {len(room_constraints)}")
        if locked_assignments:
            print(f"[Optimizer] Locked assignments: {len(locked_assignments)}")

        # 2. Pre-GA Validation (fail fast)
        print("[Optimizer] Running pre-GA validation...")
        validator = PreGAValidator(
            config=self.ga_config,
            sessions_df=sessions_df,
            rooms_df=rooms_df,
            teacher_constraints=teacher_constraints or [],
            room_constraints=room_constraints or [],
            locked_assignments=locked_assignments or []
        )
        validation_result = validator.validate()

        if not validation_result.is_valid:
            print(f"[Optimizer] Validation FAILED with {len(validation_result.errors)} errors")
            for error in validation_result.errors:
                print(f"  - {error.error_type}: {error.message}")
            raise ValidationFailedError(validation_result)

        if validation_result.warnings:
            print(f"[Optimizer] Validation passed with {len(validation_result.warnings)} warnings")
            for warning in validation_result.warnings:
                print(f"  - {warning.error_type}: {warning.message}")

        # 3. Run appropriate strategy
        if self.strategy == 'ga':
            result = self._run_ga(
                sessions_df, rooms_df, population_size, generations,
                teacher_constraints, room_constraints, locked_assignments,
                progress_callback, random_seed
            )
        elif self.strategy == 'heuristic':
            result = self._run_heuristic(sessions_df, rooms_df)
        elif self.strategy == 'hybrid':
            result = self._run_hybrid(
                sessions_df, rooms_df, population_size, generations, progress_callback
            )
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

        # 4. Save to database
        timetable_id = self._save_to_database(
            db=db,
            institution_id=institution_id,
            result=result,
            generation_time=time.time() - start_time
        )

        # 5. Build explainable output
        best_chromosome = result['best_chromosome']

        # Collect locked slots
        locked_slots = []
        for gene in best_chromosome.genes:
            if gene.is_locked:
                locked_slots.append({
                    'session_key': gene.session_key,
                    'course_code': gene.course_code,
                    'section_code': gene.section_code,
                    'day': gene.day,
                    'start_time': gene.start_time,
                    'end_time': gene.end_time,
                    'room_code': gene.room_code,
                    'lock_type': gene.lock_type
                })

        # Calculate constraint summary
        soft_scores = best_chromosome.soft_scores or {}
        hard_violations = best_chromosome.hard_violations or {}

        # Identify violated soft constraints (score < max weight)
        soft_constraint_violations = []
        for constraint_name, score in soft_scores.items():
            max_weight = getattr(self.ga_config, f'weight_{constraint_name}', 100)
            if score < max_weight * 0.9:  # Less than 90% of max
                penalty = max_weight - score
                soft_constraint_violations.append({
                    'constraint': constraint_name,
                    'score': round(score, 2),
                    'max_score': round(max_weight, 2),
                    'penalty': round(penalty, 2),
                    'satisfaction_percent': round((score / max_weight) * 100, 1) if max_weight > 0 else 100
                })

        # Sort violations by penalty (highest first)
        soft_constraint_violations.sort(key=lambda x: x['penalty'], reverse=True)

        # Build enforced constraints list
        enforced_hard_constraints = []
        for constraint_name, violation_count in hard_violations.items():
            enforced_hard_constraints.append({
                'constraint': constraint_name,
                'violations': violation_count,
                'status': 'satisfied' if violation_count == 0 else 'violated'
            })

        # Calculate fitness breakdown
        fitness_breakdown = {
            'total_fitness': round(result['best_fitness'], 2),
            'max_possible': round(sum(getattr(self.ga_config, f'weight_{k}', 0) for k in soft_scores.keys()), 2),
            'soft_scores': {k: round(v, 2) for k, v in soft_scores.items()},
            'fitness_percentage': round(
                (result['best_fitness'] / sum(getattr(self.ga_config, f'weight_{k}', 100) for k in soft_scores.keys())) * 100, 1
            ) if soft_scores else 0
        }

        # 6. Return enhanced summary
        return {
            'timetable_id': timetable_id,
            'generation_time': time.time() - start_time,
            'sessions_scheduled': len(best_chromosome.genes),
            'sessions_total': len(sessions_df),
            'fitness_score': result['best_fitness'],
            'is_feasible': result['is_feasible'],
            'strategy': self.strategy,

            # Explainable output
            'explanation': {
                'hard_constraints': enforced_hard_constraints,
                'soft_constraint_violations': soft_constraint_violations,
                'fitness_breakdown': fitness_breakdown,
                'locked_slots': locked_slots,
                'locked_count': len(locked_slots),
                'conflict_details': best_chromosome.conflict_details[:20]  # First 20 details
            },

            # Legacy fields
            'hard_violations': hard_violations,
            'soft_scores': soft_scores
        }

    def _run_ga(
        self,
        sessions_df: pd.DataFrame,
        rooms_df: pd.DataFrame,
        population_size: int,
        generations: int,
        teacher_constraints: Optional[list],
        room_constraints: Optional[list],
        locked_assignments: Optional[list],
        progress_callback: Optional[callable],
        random_seed: Optional[int] = None
    ) -> Dict:
        """Run full genetic algorithm."""

        engine = GAEngine(
            config=self.ga_config,
            sessions_df=sessions_df,
            rooms_df=rooms_df,
            teacher_constraints=teacher_constraints or [],
            room_constraints=room_constraints or [],
            locked_assignments=locked_assignments or [],
            progress_callback=progress_callback,
            random_seed=random_seed
        )

        result = engine.run(
            population_size=population_size,
            generations=generations
        )

        return result

    def _run_heuristic(
        self,
        sessions_df: pd.DataFrame,
        rooms_df: pd.DataFrame
    ) -> Dict:
        """Run greedy heuristic (uses initializer's heuristic method)."""

        from classsync_core.scheduler import PopulationInitializer

        initializer = PopulationInitializer(
            config=self.ga_config,
            sessions_df=sessions_df,
            rooms_df=rooms_df
        )

        # Create single heuristic chromosome
        chromosome = initializer._create_heuristic_chromosome()

        # Evaluate
        from classsync_core.scheduler import FitnessEvaluator
        evaluator = FitnessEvaluator(self.ga_config, rooms_df)
        evaluator.evaluate(chromosome)

        return {
            'best_chromosome': chromosome,
            'best_fitness': chromosome.fitness,
            'generation': 0,
            'total_time': 0,
            'is_feasible': chromosome.is_feasible,
            'hard_violations': chromosome.hard_violations,
            'statistics': {}
        }

    def _run_hybrid(
        self,
        sessions_df: pd.DataFrame,
        rooms_df: pd.DataFrame,
        population_size: int,
        generations: int,
        progress_callback: Optional[callable]
    ) -> Dict:
        """Run GA seeded with heuristic (more heuristic individuals in initial pop)."""

        # Create GA engine with higher heuristic seed ratio
        engine = GAEngine(
            config=self.ga_config,
            sessions_df=sessions_df,
            rooms_df=rooms_df,
            progress_callback=progress_callback
        )

        # Override initializer to use 50% heuristic seeding
        engine.initializer = engine.initializer.__class__(
            config=self.ga_config,
            sessions_df=sessions_df,
            rooms_df=rooms_df
        )

        # Modify create_population to use higher ratio
        original_create = engine.initializer.create_population
        def create_with_more_heuristic(pop_size, heuristic_seed_ratio=0.5):
            return original_create(pop_size, heuristic_seed_ratio)

        engine.initializer.create_population = create_with_more_heuristic

        result = engine.run(
            population_size=population_size,
            generations=generations
        )

        return result

    def _prepare_sessions_data(self, db: Session, institution_id: int) -> pd.DataFrame:
        """
        Fetch and prepare sessions data from database.

        Expected DataFrame columns:
        - Session_Key
        - Course_ID, Course_Code, Course_Name
        - Section_ID, Section_Code
        - Teacher_ID, Instructor (teacher name)
        - Duration_Minutes
        - Is_Lab
        - Session_Number

        Uses Course's teacher_id for instructor assignment.
        """
        print(f"[Optimizer] Preparing sessions for Institution ID: {institution_id}")

        # Get courses with their teachers (only active, non-deleted)
        courses = db.query(Course).join(Teacher).filter(
            Course.institution_id == institution_id,
            Course.is_deleted == False,
            Teacher.is_deleted == False
        ).all()

        print(f"[Optimizer] Found {len(courses)} active courses with active teachers.")

        valid_sections = []
        for course in courses:
            # Get sections for this course, eager load teacher
            from sqlalchemy.orm import joinedload
            course_sections = db.query(Section).options(joinedload(Section.teacher)).filter(
                Section.course_id == course.id,
                Section.is_deleted == False
            ).all()

            for section in course_sections:
                # Use section teacher if available, else course teacher
                teacher_to_use = section.teacher if (section.teacher and not section.teacher.is_deleted) else course.teacher
                
                if teacher_to_use and not teacher_to_use.is_deleted:
                    valid_sections.append((section, teacher_to_use))
                else:
                    print(f"[Optimizer] Warning: Section {section.code} of {course.code} has no valid teacher. Skipping.")

        print(f"[Optimizer] Found {len(valid_sections)} valid sections with teachers.")

        sessions = []
        lab_count = 0
        theory_count = 0

        for section, teacher in valid_sections:
            course = section.course

            # Determine session breakdown
            # Strict lab check: explicit type OR "lab" as a distinct word in name
            is_lab = (course.course_type == 'lab') or ('lab' in course.name.lower().split())

            if is_lab:
                # Labs: single 180-min session
                sessions.append({
                    'Session_Key': f"{course.code}-{section.code}-LAB-1",
                    'Course_ID': course.id,
                    'Course_Code': course.code,
                    'Course_Name': course.name,
                    'Section_ID': section.id,
                    'Section_Code': section.code,
                    'Teacher_ID': teacher.id,  # Use section-specific teacher
                    'Instructor': teacher.name,  # Use section-specific teacher name
                    'Duration_Minutes': 180,
                    'Is_Lab': True,
                    'Session_Number': 1
                })
                lab_count += 1
            else:
                # Theory: Multiple sessions based on credit hours
                credit_hours = int(course.credit_hours) if course.credit_hours else 3

                if credit_hours == 2:
                    num_sessions = 1
                    duration = 120
                elif credit_hours == 3:
                    num_sessions = 2
                    duration = 90
                else:
                    num_sessions = credit_hours
                    duration = 90

                for i in range(num_sessions):
                    sessions.append({
                        'Session_Key': f"{course.code}-{section.code}-T-{i+1}",
                        'Course_ID': course.id,
                        'Course_Code': course.code,
                        'Course_Name': course.name,
                        'Section_ID': section.id,
                        'Section_Code': section.code,
                        'Teacher_ID': teacher.id,  # Use section-specific teacher
                        'Instructor': teacher.name,  # Use section-specific teacher name
                        'Duration_Minutes': duration,
                        'Is_Lab': False,
                        'Session_Number': i + 1
                    })
                    theory_count += 1

        print(f"[Optimizer] Prepared {len(sessions)} total sessions (Theory: {theory_count}, Lab: {lab_count})")
        return pd.DataFrame(sessions)

    def _prepare_rooms_data(self, db: Session, institution_id: int) -> pd.DataFrame:
        """
        Fetch and prepare rooms data from database.

        Expected DataFrame columns:
        - Room_ID
        - Room_Code
        - Room_Type ('Lab' or 'Theory')
        - Capacity (optional)
        """

        rooms = db.query(Room).filter(
            Room.institution_id == institution_id,
            Room.is_deleted == False,  # Exclude deleted rooms
            Room.is_available == True   # Exclude unavailable rooms
        ).all()

        rooms_data = []
        for room in rooms:
            rooms_data.append({
                'Room_ID': room.id,
                'Room_Code': room.code,
                'Room_Type': room.room_type,
                'Capacity': room.capacity if hasattr(room, 'capacity') else 50
            })

        return pd.DataFrame(rooms_data)

    def _constraint_config_to_dict(self) -> Dict:
        """Convert ConstraintConfig model to dictionary."""
        return {
            'id': self.constraint_config.id,
            'name': self.constraint_config.name,
            'timeslot_duration_minutes': self.constraint_config.timeslot_duration_minutes,
            'days_per_week': self.constraint_config.days_per_week,
            'start_time': self.constraint_config.start_time,
            'end_time': self.constraint_config.end_time,
            'hard_constraints': self.constraint_config.hard_constraints,
            'soft_constraints': self.constraint_config.soft_constraints,
            'optional_constraints': self.constraint_config.optional_constraints,
            'max_optimization_time_seconds': self.constraint_config.max_optimization_time_seconds,
            'min_acceptable_score': self.constraint_config.min_acceptable_score
        }

    def _save_to_database(
        self,
        db: Session,
        institution_id: int,
        result: Dict,
        generation_time: float
    ) -> int:
        """
        Save generated timetable to database.

        Returns:
            Timetable ID
        """

        # Create Timetable record
        timetable = Timetable(
            institution_id=institution_id,
            name=f"GA Timetable {int(time.time())}",
            semester="Fall",  # TODO: Get from config
            year=2024,  # TODO: Get from config
            status=TimetableStatus.COMPLETED,
            generation_time_seconds=generation_time,
            constraint_score=result['best_fitness'],
            conflict_count=sum(result.get('hard_violations', {}).values()),
            constraint_config=self._constraint_config_to_dict()
        )

        db.add(timetable)
        db.flush()

        # Create TimetableEntry records
        chromosome = result['best_chromosome']

        for gene in chromosome.genes:
            # Map day name to integer (Monday=0)
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            try:
                day_index = days.index(gene.day)
            except (ValueError, IndexError):
                day_index = 0

            entry = TimetableEntry(
                timetable_id=timetable.id,
                course_id=int(gene.course_id),
                section_id=int(gene.section_id),
                teacher_id=int(gene.teacher_id),
                room_id=int(gene.room_id),
                day_of_week=day_index,
                start_time=gene.start_time,
                end_time=gene.end_time
            )
            db.add(entry)

        db.commit()

        print(f"[Optimizer] Saved timetable ID: {timetable.id}")

        return timetable.id