"""
Fitness Evaluator - Scores chromosomes based on constraints.
Hard constraints must be satisfied (0 violations).
Soft constraints are weighted and summed for fitness score (0-1000).
"""

import pandas as pd
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from classsync_core.scheduler.chromosome import Chromosome, Gene
from classsync_core.scheduler.config import GAConfig
from classsync_core.utils import slots_overlap, time_to_minutes


class FitnessEvaluator:
    """
    Evaluates chromosome fitness based on hard and soft constraints.

    Fitness Score Range: 0-1000 (higher is better)
    - Hard constraints: Must be 0 violations (else chromosome is infeasible)
    - Soft constraints: Weighted sum of penalties
    """

    def __init__(
        self,
        config: GAConfig,
        rooms_df: pd.DataFrame,
        teacher_constraints: list = None,
        room_constraints: list = None
    ):
        """
        Initialize evaluator.

        Args:
            config: GA configuration with constraint weights
            rooms_df: DataFrame with room information (Room_Code, Room_Type, Capacity)
            teacher_constraints: List of teacher availability constraints
            room_constraints: List of room availability constraints
        """
        self.config = config
        self.rooms_df = rooms_df
        self.teacher_constraints = teacher_constraints or []
        self.room_constraints = room_constraints or []

        # Build constraint indexes for fast lookup
        self._build_constraint_indexes()

        # Create room lookup dictionaries
        self.room_types = dict(zip(
            rooms_df['Room_Code'],
            rooms_df['Room_Type']
        ))

        if 'Capacity' in rooms_df.columns:
            self.room_capacities = dict(zip(
                rooms_df['Room_Code'],
                rooms_df['Capacity']
            ))
        else:
            # Default capacities if not provided
            self.room_capacities = {
                room: 50 for room in rooms_df['Room_Code']
            }

        # Extract building names from room codes (e.g., "SB 003" -> "SB")
        self.room_buildings = {}
        for room in rooms_df['Room_Code']:
            building = room.split()[0] if ' ' in room else room[:2]
            self.room_buildings[room] = building

    def _build_constraint_indexes(self):
        """Build indexes for fast constraint lookup."""
        # Teacher constraints
        self.teacher_blocked_slots = defaultdict(list)  # teacher_id -> [(day, start, end, is_hard, weight)]
        self.teacher_day_offs = defaultdict(list)  # teacher_id -> [(day, is_hard, weight)]

        for tc in self.teacher_constraints:
            teacher_id = tc['teacher_id']
            constraint_type = tc['constraint_type']
            is_hard = tc.get('is_hard', False)
            weight = tc.get('weight', 5)

            if constraint_type == 'blocked_slot':
                self.teacher_blocked_slots[teacher_id].append(
                    (tc.get('day'), tc.get('start_time'), tc.get('end_time'), is_hard, weight)
                )
            elif constraint_type == 'day_off':
                days = tc.get('days', [tc.get('day')] if tc.get('day') else [])
                for day in days:
                    self.teacher_day_offs[teacher_id].append((day, is_hard, weight))

        # Room constraints (symmetric to teacher constraints)
        self.room_blocked_slots = defaultdict(list)  # room_id -> [(day, start, end, is_hard, weight)]
        self.room_day_offs = defaultdict(list)  # room_id -> [(day, is_hard, weight)]

        for rc in self.room_constraints:
            room_id = rc['room_id']
            constraint_type = rc['constraint_type']
            is_hard = rc.get('is_hard', False)
            weight = rc.get('weight', 5)

            if constraint_type == 'blocked_slot':
                self.room_blocked_slots[room_id].append(
                    (rc.get('day'), rc.get('start_time'), rc.get('end_time'), is_hard, weight)
                )
            elif constraint_type == 'day_off':
                days = rc.get('days', [rc.get('day')] if rc.get('day') else [])
                for day in days:
                    self.room_day_offs[room_id].append((day, is_hard, weight))
    
    def evaluate(self, chromosome: Chromosome) -> float:
        """
        Main evaluation function.
        
        Args:
            chromosome: Chromosome to evaluate
            
        Returns:
            Fitness score (0-1000, higher is better)
        """
        # Check hard constraints first
        hard_violations = self._check_hard_constraints(chromosome)
        
        chromosome.hard_violations = hard_violations
        chromosome.is_feasible = all(v == 0 for v in hard_violations.values())
        
        # If infeasible, return very low fitness
        if not chromosome.is_feasible:
            chromosome.fitness = 0.0
            return 0.0
        
        # Calculate soft constraint scores
        soft_scores = self._calculate_soft_scores(chromosome)
        chromosome.soft_scores = soft_scores
        
        # Total fitness = sum of all soft scores
        total_fitness = sum(soft_scores.values())
        
        chromosome.fitness = total_fitness
        return total_fitness
    
    def _check_hard_constraints(self, chromosome: Chromosome) -> Dict[str, int]:
        """
        Check all hard constraints.
        
        Returns:
            Dictionary of constraint -> violation count
        """
        violations = {
            'teacher_overlap': 0,
            'room_overlap': 0,
            'section_overlap': 0,
            'invalid_time_slots': 0,
            'invalid_durations': 0,
            'blocked_windows': 0,
            'lab_contiguity': 0,
            'missing_assignments': 0,
            'teacher_blocked_slots': 0,
            'teacher_day_offs': 0,
            'room_blocked_slots': 0,
            'room_day_offs': 0,
            'room_capacity': 0,
            'lock_violations': 0
        }
        
        # Check for unassigned sessions
        for gene in chromosome.genes:
            if gene.day is None or gene.start_time is None or gene.room_id is None:
                violations['missing_assignments'] += 1
        
        # If assignments are missing, other checks are meaningless
        if violations['missing_assignments'] > 0:
            chromosome.conflict_details.append(
                f"{violations['missing_assignments']} sessions not assigned"
            )
            return violations
        
        # Check invalid time slots and durations
        day_end_minutes = time_to_minutes(self.config.day_end_time)

        for gene in chromosome.genes:
            if not self.config.is_valid_start_time(gene.start_time):
                violations['invalid_time_slots'] += 1
                chromosome.conflict_details.append(
                    f"Invalid start time: {gene.session_key} at {gene.start_time}"
                )
            
            # Check if session extends beyond day end time
            if time_to_minutes(gene.end_time) > day_end_minutes:
                violations['invalid_time_slots'] += 1
                chromosome.conflict_details.append(
                    f"Session exceeds day end: {gene.session_key} ends at {gene.end_time} (max {self.config.day_end_time})"
                )
            
            if not self.config.is_valid_duration(gene.duration_minutes):
                violations['invalid_durations'] += 1
                chromosome.conflict_details.append(
                    f"Invalid duration: {gene.session_key} = {gene.duration_minutes} mins"
                )
            
            # Check blocked windows
            if self.config.is_blocked(gene.day, gene.start_time, gene.end_time):
                violations['blocked_windows'] += 1
                chromosome.conflict_details.append(
                    f"Blocked window violation: {gene.session_key} on {gene.day} {gene.start_time}-{gene.end_time}"
                )
        
        # Check overlaps (teacher, room, section)
        teacher_violations = self._check_resource_overlaps(chromosome, 'teacher')
        room_violations = self._check_resource_overlaps(chromosome, 'room')
        section_violations = self._check_resource_overlaps(chromosome, 'section')
        
        violations['teacher_overlap'] = teacher_violations
        violations['room_overlap'] = room_violations
        violations['section_overlap'] = section_violations
        
        # Check lab contiguity (labs must be 180 min continuous)
        lab_violations = self._check_lab_contiguity(chromosome)
        violations['lab_contiguity'] = lab_violations

        # Check teacher blocked slots (hard constraints only)
        teacher_blocked_violations = self._check_teacher_blocked_slots(chromosome)
        violations['teacher_blocked_slots'] = teacher_blocked_violations

        # Check teacher day-offs (hard constraints only)
        teacher_dayoff_violations = self._check_teacher_day_offs(chromosome)
        violations['teacher_day_offs'] = teacher_dayoff_violations

        # Check room blocked slots (hard constraints only)
        room_blocked_violations = self._check_room_blocked_slots(chromosome)
        violations['room_blocked_slots'] = room_blocked_violations

        # Check room day-offs (hard constraints only)
        room_dayoff_violations = self._check_room_day_offs(chromosome)
        violations['room_day_offs'] = room_dayoff_violations

        # Check room capacity violations
        room_capacity_violations = self._check_room_capacity(chromosome)
        violations['room_capacity'] = room_capacity_violations

        # Check lock violations (genes that were modified from their locked values)
        lock_violations = self._check_lock_violations(chromosome)
        violations['lock_violations'] = lock_violations

        return violations

    def _check_teacher_blocked_slots(self, chromosome: Chromosome) -> int:
        """Check for hard teacher blocked slot violations."""
        violations = 0

        for gene in chromosome.genes:
            teacher_id = gene.teacher_id
            if teacher_id not in self.teacher_blocked_slots:
                continue

            for day, start_time, end_time, is_hard, weight in self.teacher_blocked_slots[teacher_id]:
                if not is_hard:
                    continue  # Skip soft constraints here

                if gene.day == day and slots_overlap(gene.start_time, gene.end_time, start_time, end_time):
                    violations += 1
                    chromosome.conflict_details.append(
                        f"Teacher blocked slot violation: {gene.session_key} on {day} "
                        f"({gene.start_time}-{gene.end_time}) conflicts with blocked "
                        f"({start_time}-{end_time})"
                    )

        return violations

    def _check_teacher_day_offs(self, chromosome: Chromosome) -> int:
        """Check for hard teacher day-off violations."""
        violations = 0

        for gene in chromosome.genes:
            teacher_id = gene.teacher_id
            if teacher_id not in self.teacher_day_offs:
                continue

            for day, is_hard, weight in self.teacher_day_offs[teacher_id]:
                if not is_hard:
                    continue  # Skip soft constraints here

                if gene.day == day:
                    violations += 1
                    chromosome.conflict_details.append(
                        f"Teacher day-off violation: {gene.session_key} on {day} "
                        f"(teacher has hard day-off constraint)"
                    )

        return violations

    def _check_room_blocked_slots(self, chromosome: Chromosome) -> int:
        """Check for hard room blocked slot violations."""
        violations = 0

        for gene in chromosome.genes:
            room_id = gene.room_id
            if room_id not in self.room_blocked_slots:
                continue

            for day, start_time, end_time, is_hard, weight in self.room_blocked_slots[room_id]:
                if not is_hard:
                    continue  # Skip soft constraints here

                if gene.day == day and slots_overlap(gene.start_time, gene.end_time, start_time, end_time):
                    violations += 1
                    chromosome.conflict_details.append(
                        f"Room blocked slot violation: {gene.session_key} in room {gene.room_code} on {day} "
                        f"({gene.start_time}-{gene.end_time}) conflicts with blocked "
                        f"({start_time}-{end_time})"
                    )

        return violations

    def _check_room_day_offs(self, chromosome: Chromosome) -> int:
        """Check for hard room day-off violations."""
        violations = 0

        for gene in chromosome.genes:
            room_id = gene.room_id
            if room_id not in self.room_day_offs:
                continue

            for day, is_hard, weight in self.room_day_offs[room_id]:
                if not is_hard:
                    continue  # Skip soft constraints here

                if gene.day == day:
                    violations += 1
                    chromosome.conflict_details.append(
                        f"Room day-off violation: {gene.session_key} in room {gene.room_code} on {day} "
                        f"(room has hard day-off constraint)"
                    )

        return violations

    def _check_room_capacity(self, chromosome: Chromosome) -> int:
        """
        Check for room capacity violations.
        This is a hard constraint if section size exceeds room capacity.
        """
        violations = 0

        for gene in chromosome.genes:
            room_capacity = self.room_capacities.get(gene.room_code, 50)
            # For now, we don't have section sizes, so skip capacity check
            # This can be extended when section enrollment data is available
            # if gene.section_size > room_capacity:
            #     violations += 1

        return violations

    def _check_lock_violations(self, chromosome: Chromosome) -> int:
        """Check that locked genes maintain their locked values."""
        violations = 0

        for gene in chromosome.genes:
            if not gene.is_locked:
                continue

            if gene.day != gene.locked_day or gene.start_time != gene.locked_start_time:
                violations += 1
                chromosome.conflict_details.append(
                    f"Lock violation: {gene.session_key} should be at "
                    f"{gene.locked_day} {gene.locked_start_time} but is at "
                    f"{gene.day} {gene.start_time}"
                )

            if gene.lock_type == 'full_lock' and gene.locked_room_id is not None:
                if gene.room_id != gene.locked_room_id:
                    violations += 1
                    chromosome.conflict_details.append(
                        f"Lock violation: {gene.session_key} room should be "
                        f"{gene.locked_room_id} but is {gene.room_id}"
                    )

        return violations
    
    def _check_resource_overlaps(
        self, 
        chromosome: Chromosome, 
        resource_type: str
    ) -> int:
        """
        Check for time overlaps of a resource (teacher/room/section).
        
        Args:
            chromosome: Chromosome to check
            resource_type: 'teacher', 'room', or 'section'
            
        Returns:
            Number of overlap violations
        """
        violations = 0
        
        # Build schedule index: {resource_id: {day: [(start, end, gene)]}}
        schedule = defaultdict(lambda: defaultdict(list))
        
        for gene in chromosome.genes:
            if resource_type == 'teacher':
                resource_id = gene.teacher_id
            elif resource_type == 'room':
                resource_id = gene.room_id
            else:  # section
                resource_id = gene.section_id
            
            schedule[resource_id][gene.day].append(
                (gene.start_time, gene.end_time, gene)
            )
        
        # Check each resource's schedule for overlaps
        for resource_id, days in schedule.items():
            for day, sessions in days.items():
                # Check all pairs for overlaps
                for i in range(len(sessions)):
                    for j in range(i + 1, len(sessions)):
                        start1, end1, gene1 = sessions[i]
                        start2, end2, gene2 = sessions[j]
                        
                        if slots_overlap(start1, end1, start2, end2):
                            violations += 1
                            chromosome.conflict_details.append(
                                f"{resource_type.capitalize()} overlap: "
                                f"{gene1.session_key} and {gene2.session_key} "
                                f"on {day} ({start1}-{end1} vs {start2}-{end2})"
                            )
        
        return violations
    
    def _check_lab_contiguity(self, chromosome: Chromosome) -> int:
        """
        Check that lab sessions are exactly 180 minutes continuous.
        
        Returns:
            Number of violations
        """
        violations = 0
        
        for gene in chromosome.genes:
            if gene.is_lab:
                # Lab must be exactly 180 minutes
                if gene.duration_minutes != 180:
                    violations += 1
                    chromosome.conflict_details.append(
                        f"Lab duration violation: {gene.session_key} "
                        f"is {gene.duration_minutes} mins (should be 180)"
                    )
        
        return violations
    
    def _calculate_soft_scores(self, chromosome: Chromosome) -> Dict[str, float]:
        """
        Calculate scores for soft constraints.

        Scoring is organized by priority tier:
        - TIER 1 (Critical): Resource availability - highest impact
        - TIER 2 (Important): Schedule quality
        - TIER 3 (Preference): Time/room preferences
        - TIER 4 (Minor): Optimization nice-to-haves

        Each constraint contributes to total fitness.
        Higher score = better. Normalized to ~1000 max.

        Returns:
            Dictionary of constraint -> score
        """
        scores = {}

        # TIER 1: Resource Availability (Critical)
        scores['teacher_availability'] = self._score_teacher_availability(chromosome)
        scores['room_availability'] = self._score_room_availability(chromosome)

        # TIER 2: Schedule Quality (Important)
        scores['even_distribution'] = self._score_even_distribution(chromosome)
        scores['minimize_student_gaps'] = self._score_minimize_gaps(chromosome, 'section')
        scores['compact_schedule'] = self._score_compactness(chromosome)
        scores['minimize_teacher_gaps'] = self._score_minimize_gaps(chromosome, 'teacher')

        # TIER 3: Preferences
        scores['room_type_match'] = self._score_room_type_match(chromosome)
        scores['minimize_early_classes'] = self._score_time_preference(
            chromosome, 'early', self.config.early_class_threshold
        )
        scores['minimize_late_classes'] = self._score_time_preference(
            chromosome, 'late', self.config.late_class_threshold
        )

        # TIER 4: Minor Optimization
        scores['minimize_building_changes'] = self._score_building_changes(chromosome)
        scores['room_utilization'] = self._score_room_utilization(chromosome)

        return scores

    def _score_teacher_availability(self, chromosome: Chromosome) -> float:
        """
        Score based on respecting soft teacher availability constraints.
        Penalizes sessions scheduled during teacher blocked slots or day-offs
        when those constraints are marked as soft (not hard).

        Returns:
            Score (higher = better, 0 = max violations)
        """
        if not self.teacher_constraints:
            # No constraints, full score
            return self.config.weight_teacher_availability

        total_penalty = 0
        violation_count = 0
        max_violations = len(chromosome.genes)  # Theoretical max

        for gene in chromosome.genes:
            teacher_id = gene.teacher_id

            # Check soft blocked slots
            for day, start_time, end_time, is_hard, weight in self.teacher_blocked_slots.get(teacher_id, []):
                if is_hard:
                    continue  # Hard constraints handled elsewhere

                if gene.day == day and slots_overlap(gene.start_time, gene.end_time, start_time, end_time):
                    # Apply weighted penalty (weight is 1-10, multiply by penalty factor)
                    total_penalty += weight * self.config.soft_constraint_penalty_multiplier
                    violation_count += 1

            # Check soft day-offs
            for day, is_hard, weight in self.teacher_day_offs.get(teacher_id, []):
                if is_hard:
                    continue

                if gene.day == day:
                    total_penalty += weight * self.config.soft_constraint_penalty_multiplier
                    violation_count += 1

        # Normalize: no violations = full weight, max violations = 0
        if max_violations == 0:
            return self.config.weight_teacher_availability

        # Calculate score: higher penalty = lower score
        max_penalty = max_violations * 10 * self.config.soft_constraint_penalty_multiplier
        penalty_ratio = min(total_penalty / max_penalty, 1.0) if max_penalty > 0 else 0
        score = (1.0 - penalty_ratio) * self.config.weight_teacher_availability

        return max(0, score)

    def _score_room_availability(self, chromosome: Chromosome) -> float:
        """
        Score based on respecting soft room availability constraints.
        Symmetric to teacher availability scoring.

        Returns:
            Score (higher = better)
        """
        if not self.room_constraints:
            return self.config.weight_room_availability

        total_penalty = 0
        violation_count = 0
        max_violations = len(chromosome.genes)

        for gene in chromosome.genes:
            room_id = gene.room_id

            # Check soft blocked slots
            for day, start_time, end_time, is_hard, weight in self.room_blocked_slots.get(room_id, []):
                if is_hard:
                    continue

                if gene.day == day and slots_overlap(gene.start_time, gene.end_time, start_time, end_time):
                    total_penalty += weight * self.config.soft_constraint_penalty_multiplier
                    violation_count += 1

            # Check soft day-offs
            for day, is_hard, weight in self.room_day_offs.get(room_id, []):
                if is_hard:
                    continue

                if gene.day == day:
                    total_penalty += weight * self.config.soft_constraint_penalty_multiplier
                    violation_count += 1

        if max_violations == 0:
            return self.config.weight_room_availability

        max_penalty = max_violations * 10 * self.config.soft_constraint_penalty_multiplier
        penalty_ratio = min(total_penalty / max_penalty, 1.0) if max_penalty > 0 else 0
        score = (1.0 - penalty_ratio) * self.config.weight_room_availability

        return max(0, score)
    
    def _score_even_distribution(self, chromosome: Chromosome) -> float:
        """
        Score based on how evenly sessions are distributed across days.
        Perfect distribution = max score.
        """
        day_counts = defaultdict(int)
        for gene in chromosome.genes:
            day_counts[gene.day] += 1
        
        counts = list(day_counts.values())
        if not counts:
            return 0.0
        
        # Calculate standard deviation (lower is better)
        avg = sum(counts) / len(counts)
        variance = sum((c - avg) ** 2 for c in counts) / len(counts)
        std_dev = variance ** 0.5
        
        # Normalize: std_dev of 0 = perfect, std_dev of avg = very bad
        # Score: high when std_dev is low
        if avg == 0:
            return 0.0
        
        normalized_std = std_dev / avg
        score = max(0, 1 - normalized_std)  # 0 to 1
        
        return score * self.config.weight_even_distribution
    
    def _score_minimize_gaps(
        self, 
        chromosome: Chromosome, 
        resource_type: str
    ) -> float:
        """
        Score based on minimizing gaps in schedules.
        
        Args:
            resource_type: 'section' for students, 'teacher' for instructors
        """
        total_gap_penalty = 0
        resource_count = 0
        
        # Group by resource and day
        schedule = defaultdict(lambda: defaultdict(list))
        
        for gene in chromosome.genes:
            resource_id = gene.section_id if resource_type == 'section' else gene.teacher_id
            schedule[resource_id][gene.day].append(gene)
        
        # For each resource, check gaps on each day
        for resource_id, days in schedule.items():
            resource_count += 1
            
            for day, genes in days.items():
                if len(genes) < 2:
                    continue  # No gaps if only 1 session
                
                # Sort by start time
                genes = sorted(genes, key=lambda g: time_to_minutes(g.start_time))
                
                # Calculate gaps
                for i in range(len(genes) - 1):
                    gap_minutes = (
                        time_to_minutes(genes[i + 1].start_time) - 
                        time_to_minutes(genes[i].end_time)
                    )
                    
                    # Penalize gaps > threshold
                    if gap_minutes > self.config.max_acceptable_gap_minutes:
                        penalty = (gap_minutes - self.config.max_acceptable_gap_minutes) / 60.0
                        total_gap_penalty += penalty
        
        # Normalize by resource count
        if resource_count == 0:
            return 0.0
        
        avg_penalty = total_gap_penalty / resource_count
        
        # Score: lower penalty = higher score
        # Assume worst case is 3 hours of gaps per resource per day
        max_penalty = 3.0
        normalized_penalty = min(avg_penalty / max_penalty, 1.0)
        score = 1.0 - normalized_penalty
        
        weight = (
            self.config.weight_minimize_gaps_students 
            if resource_type == 'section' 
            else self.config.weight_minimize_gaps_teachers
        )
        
        return score * weight
    
    def _score_time_preference(
        self, 
        chromosome: Chromosome, 
        preference_type: str,
        threshold: str
    ) -> float:
        """
        Score based on avoiding early/late classes.
        
        Args:
            preference_type: 'early' or 'late'
            threshold: Time threshold (e.g., '09:30' for early, '15:30' for late)
        """
        threshold_minutes = time_to_minutes(threshold)
        violation_count = 0
        
        for gene in chromosome.genes:
            start_minutes = time_to_minutes(gene.start_time)
            
            if preference_type == 'early':
                if start_minutes < threshold_minutes:
                    violation_count += 1
            else:  # late
                if start_minutes >= threshold_minutes:
                    violation_count += 1
        
        # Normalize by total sessions
        if len(chromosome.genes) == 0:
            return 0.0
        
        violation_ratio = violation_count / len(chromosome.genes)
        score = 1.0 - violation_ratio
        
        weight = (
            self.config.weight_minimize_early_classes 
            if preference_type == 'early' 
            else self.config.weight_minimize_late_classes
        )
        
        return score * weight
    
    def _score_room_type_match(self, chromosome: Chromosome) -> float:
        """
        Score based on matching lab sessions to lab rooms.
        """
        matches = 0
        mismatches = 0
        
        for gene in chromosome.genes:
            if gene.room_code not in self.room_types:
                continue  # Skip if room info not available
            
            room_type = self.room_types[gene.room_code].lower()
            
            if gene.is_lab:
                if 'lab' in room_type:
                    matches += 1
                else:
                    mismatches += 1
            else:
                if 'lab' not in room_type:
                    matches += 1
                else:
                    mismatches += 1
        
        total = matches + mismatches
        if total == 0:
            return 0.0
        
        score = matches / total
        return score * self.config.weight_room_type_match
    
    def _score_building_changes(self, chromosome: Chromosome) -> float:
        """
        Score based on minimizing building changes for sections.
        Students prefer staying in same building.
        """
        total_changes = 0
        section_count = 0
        
        # Group by section and day
        schedule = defaultdict(lambda: defaultdict(list))
        for gene in chromosome.genes:
            schedule[gene.section_id][gene.day].append(gene)
        
        for section_id, days in schedule.items():
            section_count += 1
            
            for day, genes in days.items():
                if len(genes) < 2:
                    continue
                
                # Sort by time
                genes = sorted(genes, key=lambda g: time_to_minutes(g.start_time))
                
                # Count building changes
                for i in range(len(genes) - 1):
                    building1 = self.room_buildings.get(genes[i].room_code, '')
                    building2 = self.room_buildings.get(genes[i + 1].room_code, '')
                    
                    if building1 != building2:
                        total_changes += 1
        
        if section_count == 0:
            return 0.0
        
        # Normalize: assume worst case is 3 building changes per section per week
        avg_changes = total_changes / section_count
        max_changes = 15.0  # 3 per day * 5 days
        normalized = min(avg_changes / max_changes, 1.0)
        score = 1.0 - normalized
        
        return score * self.config.weight_minimize_building_changes
    
    def _score_compactness(self, chromosome: Chromosome) -> float:
        """
        Score based on schedule compactness (minimize span of day).
        """
        total_span = 0
        section_day_count = 0
        
        # Group by section and day
        schedule = defaultdict(lambda: defaultdict(list))
        for gene in chromosome.genes:
            schedule[gene.section_id][gene.day].append(gene)
        
        for section_id, days in schedule.items():
            for day, genes in days.items():
                if not genes:
                    continue
                
                section_day_count += 1
                
                # Find earliest start and latest end
                earliest = min(time_to_minutes(g.start_time) for g in genes)
                latest = max(time_to_minutes(g.end_time) for g in genes)
                
                span_minutes = latest - earliest
                total_span += span_minutes
        
        if section_day_count == 0:
            return 0.0
        
        # Average span per section per day
        avg_span = total_span / section_day_count
        
        # Normalize: ideal is 3 hours (180 min), worst is 10 hours (600 min)
        ideal_span = 180.0
        max_span = 600.0
        
        if avg_span <= ideal_span:
            score = 1.0
        else:
            normalized = (avg_span - ideal_span) / (max_span - ideal_span)
            score = max(0, 1.0 - normalized)
        
        return score * self.config.weight_compact_schedule
    
    def _score_room_utilization(self, chromosome: Chromosome) -> float:
        """
        Score based on efficient room usage.
        Prefer using fewer rooms more efficiently.
        """
        room_usage = defaultdict(int)
        
        for gene in chromosome.genes:
            room_usage[gene.room_id] += 1
        
        if not room_usage:
            return 0.0
        
        # Calculate utilization variance
        usage_counts = list(room_usage.values())
        avg_usage = sum(usage_counts) / len(usage_counts)
        variance = sum((u - avg_usage) ** 2 for u in usage_counts) / len(usage_counts)
        std_dev = variance ** 0.5
        
        # Lower variance = better (rooms used evenly)
        if avg_usage == 0:
            return 0.0
        
        normalized_std = std_dev / avg_usage
        score = max(0, 1 - normalized_std)
        
        return score * self.config.weight_room_utilization
