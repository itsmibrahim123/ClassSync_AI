"""
GA Scheduler Configuration
Defines hyperparameters, constraints, and time slot rules.
"""

from typing import List, Tuple, Dict
from datetime import time
from dataclasses import dataclass, field


@dataclass
class GAConfig:
    """Genetic Algorithm hyperparameters and scheduling rules."""
    
    # ==================== GA PARAMETERS ====================
    population_size: int = 50
    generations: int = 150
    elitism_rate: float = 0.05  # Keep top 5% unchanged
    crossover_rate: float = 0.80  # 80% of offspring from crossover
    
    # Mutation rates (decay over time)
    mutation_rate_initial: float = 0.15  # 15% early generations
    mutation_rate_mid: float = 0.10      # 10% mid generations
    mutation_rate_final: float = 0.05    # 5% late generations
    mutation_decay_generation: int = 25  # Switch points
    
    # Selection
    tournament_size: int = 5
    
    # Early stopping
    max_stagnant_generations: int = 30  # Stop if no improvement
    min_acceptable_fitness: float = 850.0  # Out of 1000
    
    # Performance
    max_repair_attempts: int = 10
    parallel_fitness_evaluation: bool = True
    max_workers: int = 4
    
    # ==================== TIME SLOT CONFIGURATION ====================
    working_days: List[str] = field(default_factory=lambda: [
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'
    ])
    
    # Valid class start times (only these are allowed)
    allowed_start_times: List[str] = field(default_factory=lambda: [
        '08:00', '09:30', '11:00', '12:30', '14:00', '15:30', '17:00'
    ])
    
    # Valid class durations (in minutes)
    allowed_durations: List[int] = field(default_factory=lambda: [90, 120, 180])
    
    # Working hours
    day_start_time: str = '08:00'
    day_end_time: str = '18:30'
    
    # Slot granularity for internal tracking (30 min intervals)
    slot_duration_minutes: int = 30
    
    # ==================== BLOCKED TIME WINDOWS ====================
    # Format: {day: [(start_time, end_time), ...]}
    blocked_windows: Dict[str, List[Tuple[str, str]]] = field(default_factory=lambda: {
        'Friday': [('12:30', '14:00')],  # Jummah break
        'Monday': [('12:30', '14:00')],  # VC slot
        'Tuesday': [('12:30', '14:00')]  # VC slot
    })
    
    # ==================== HARD CONSTRAINTS ====================
    # These MUST be satisfied (violations = invalid chromosome)
    enforce_no_teacher_overlap: bool = True
    enforce_no_room_overlap: bool = True
    enforce_no_section_overlap: bool = True
    enforce_valid_time_slots: bool = True
    enforce_valid_durations: bool = True
    enforce_lab_contiguity: bool = True  # Labs must be 180 min continuous
    enforce_blocked_windows: bool = True
    enforce_full_coverage: bool = True  # All sessions must be scheduled
    
    # ==================== SOFT CONSTRAINT WEIGHTS ====================
    # Higher weight = more important
    # Weights are organized by priority tier:
    #   TIER 1 (Critical): 150-200 - Resource availability
    #   TIER 2 (Important): 100-149 - Schedule quality
    #   TIER 3 (Preference): 50-99 - Optimization preferences
    #   TIER 4 (Minor): 1-49 - Nice to have
    #
    # Total theoretical max fitness ~ 1000 (normalized)
    #
    # Priority Order (high to low):
    # 1. Teacher availability constraints (hard->soft)
    # 2. Room availability constraints (hard->soft)
    # 3. Schedule compactness and distribution
    # 4. Time preferences (early/late)
    # 5. Building/room optimization

    # TIER 1: Resource Availability (Critical - 150-200)
    weight_teacher_availability: float = 180.0    # Respect teacher soft constraints
    weight_room_availability: float = 160.0       # Respect room soft constraints

    # TIER 2: Schedule Quality (Important - 100-149)
    weight_even_distribution: float = 140.0       # Spread across days
    weight_minimize_gaps_students: float = 120.0  # Compact student schedules
    weight_compact_schedule: float = 110.0        # Minimal day span
    weight_minimize_gaps_teachers: float = 100.0  # Compact teacher schedules

    # TIER 3: Preferences (50-99)
    weight_teacher_preference: float = 90.0       # Time slot preferences
    weight_room_type_match: float = 80.0          # Labs in lab rooms
    weight_minimize_early_classes: float = 60.0   # Avoid before threshold
    weight_minimize_late_classes: float = 60.0    # Avoid after threshold

    # TIER 4: Minor Optimization (1-49)
    weight_minimize_building_changes: float = 40.0  # Same building preference
    weight_room_utilization: float = 30.0           # Efficient room usage

    # Penalty multiplier for soft constraint violations
    # User-specified weights (1-10) are multiplied by this
    soft_constraint_penalty_multiplier: float = 15.0
    
    # Thresholds for penalties
    early_class_threshold: str = '09:30'
    late_class_threshold: str = '15:30'
    max_acceptable_gap_minutes: int = 90  # More than 1.5 hrs = penalty
    
    # ==================== REPAIR STRATEGY ====================
    repair_order: List[str] = field(default_factory=lambda: [
        'blocked_windows',      # Move sessions out of blocked times
        'invalid_start_times',  # Snap to allowed starts
        'lab_contiguity',       # Fix lab sessions
        'teacher_conflicts',    # Resolve teacher overlaps
        'room_conflicts',       # Resolve room overlaps
        'section_conflicts'     # Resolve section overlaps
    ])
    
    # ==================== CROSSOVER STRATEGY ====================
    # Primary: day-based (inherit full days from parents)
    # Secondary: uniform (random session swap)
    day_based_crossover_ratio: float = 0.80  # 80% day-based, 20% uniform
    
    # ==================== LOGGING & PROGRESS ====================
    log_interval: int = 10  # Log every N generations
    progress_callback_enabled: bool = True
    detailed_conflict_reporting: bool = True
    
    def get_mutation_rate(self, generation: int) -> float:
        """Get mutation rate based on current generation."""
        if generation < self.mutation_decay_generation:
            return self.mutation_rate_initial
        elif generation < self.mutation_decay_generation * 3:
            return self.mutation_rate_mid
        else:
            return self.mutation_rate_final
    
    def is_valid_start_time(self, time_str: str) -> bool:
        """Check if time is an allowed start time."""
        return time_str in self.allowed_start_times
    
    def is_valid_duration(self, duration_minutes: int) -> bool:
        """Check if duration is allowed."""
        return duration_minutes in self.allowed_durations
    
    def is_blocked(self, day: str, start_time: str, end_time: str) -> bool:
        """Check if time slot overlaps with blocked window."""
        if day not in self.blocked_windows:
            return False
        
        from classsync_core.utils import slots_overlap
        
        for blocked_start, blocked_end in self.blocked_windows[day]:
            if slots_overlap(start_time, end_time, blocked_start, blocked_end):
                return True
        
        return False
    
    def get_allowed_slots(self) -> List[Tuple[str, str, str]]:
        """
        Generate all allowed time slots.
        Returns: List of (day, start_time, end_time) tuples.
        """
        from classsync_core.utils import calculate_slot_end_time
        
        slots = []
        for day in self.working_days:
            for start_time in self.allowed_start_times:
                # Calculate end based on slot_duration_minutes
                end_time = calculate_slot_end_time(
                    start_time, 
                    self.slot_duration_minutes
                )
                slots.append((day, start_time, end_time))
        
        return slots


# Default configuration instance
DEFAULT_GA_CONFIG = GAConfig()
