"""
Repair Mechanism - Fixes constraint violations in chromosomes.

Repair Strategy:
1. Restore locked genes first (immutable)
2. Fix structural issues (blocked windows, invalid times, lab contiguity)
3. Resolve resource conflicts in priority order: teacher > room > section
4. Use maximum pass limits to prevent infinite loops
5. Track repair attempts to avoid repetition
"""
import random
from typing import List, Set, Dict, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from classsync_core.scheduler.chromosome import Chromosome, Gene
from classsync_core.scheduler.config import GAConfig
from classsync_core.utils import slots_overlap, calculate_slot_end_time, time_to_minutes


@dataclass
class RepairStats:
    """Statistics for repair operation."""
    total_attempts: int = 0
    successful_repairs: int = 0
    failed_repairs: int = 0
    locked_conflicts_skipped: int = 0
    pass_count: int = 0


class RepairMechanism:
    """
    Repairs chromosome constraint violations.

    Design Decisions:
    - Locked genes are NEVER modified (restored at start of each repair)
    - Global pass limit prevents infinite loops
    - Priority order: teacher conflicts > room conflicts > section conflicts
    - Conflict resolution uses randomized slot search with attempt tracking
    """

    # Maximum number of complete repair passes
    MAX_REPAIR_PASSES = 3

    # Maximum total attempts across all repair passes
    MAX_TOTAL_ATTEMPTS = 500

    def __init__(self, config: GAConfig, rooms_df):
        self.config = config
        self.rooms_df = rooms_df

        # Room lists
        self.lab_rooms = rooms_df[
            rooms_df['Room_Type'].str.lower().str.contains('lab')
        ]['Room_Code'].tolist()

        self.theory_rooms = rooms_df[
            ~rooms_df['Room_Type'].str.lower().str.contains('lab')
        ]['Room_Code'].tolist()

        self.all_rooms = rooms_df['Room_Code'].tolist()

        # Pre-compute valid slots for faster lookup
        self._precompute_valid_slots()

    def _precompute_valid_slots(self):
        """Pre-compute all valid (day, start_time) combinations not in blocked windows."""
        self.valid_slots = []
        day_end_minutes = time_to_minutes(self.config.day_end_time)

        for day in self.config.working_days:
            for start_time in self.config.allowed_start_times:
                # Check against all common durations
                for duration in [90, 120, 180]:
                    end_time = calculate_slot_end_time(start_time, duration)
                    if time_to_minutes(end_time) <= day_end_minutes:
                        if not self.config.is_blocked(day, start_time, end_time):
                            self.valid_slots.append((day, start_time, duration))

    def repair(self, chromosome: Chromosome) -> bool:
        """
        Repair chromosome to fix hard constraint violations.

        Uses multiple passes with global attempt limits to prevent infinite loops.

        Args:
            chromosome: Chromosome to repair (modified in-place)

        Returns:
            True if successfully repaired, False if unrepairable
        """
        stats = RepairStats()

        # ALWAYS restore locked genes first
        self._restore_all_locked_genes(chromosome)

        # Multiple repair passes with global limit
        for pass_num in range(self.MAX_REPAIR_PASSES):
            stats.pass_count = pass_num + 1

            if stats.total_attempts >= self.MAX_TOTAL_ATTEMPTS:
                break

            # Run repair sequence
            all_repaired = self._run_repair_pass(chromosome, stats)

            if all_repaired:
                stats.successful_repairs += 1
                return True

            # Restore locks before next pass (safety)
            self._restore_all_locked_genes(chromosome)

        # Failed after all passes
        stats.failed_repairs += 1
        return False

    def _restore_all_locked_genes(self, chromosome: Chromosome):
        """Restore all locked genes to their fixed values."""
        for gene in chromosome.genes:
            if gene.is_locked:
                gene.restore_lock()

    def _run_repair_pass(self, chromosome: Chromosome, stats: RepairStats) -> bool:
        """
        Run a single repair pass through all constraint types.

        Returns:
            True if all constraints repaired successfully
        """
        # Priority-ordered repair sequence
        repair_sequence = [
            ('blocked_windows', self._repair_blocked_windows),
            ('invalid_start_times', self._repair_invalid_start_times),
            ('lab_contiguity', self._repair_lab_contiguity),
            ('teacher_conflicts', lambda c: self._repair_resource_conflicts(c, 'teacher', stats)),
            ('room_conflicts', lambda c: self._repair_resource_conflicts(c, 'room', stats)),
            ('section_conflicts', lambda c: self._repair_resource_conflicts(c, 'section', stats)),
        ]

        for constraint_name, repair_func in repair_sequence:
            if stats.total_attempts >= self.MAX_TOTAL_ATTEMPTS:
                return False

            if not repair_func(chromosome):
                return False

        return True

    def _repair_blocked_windows(self, chromosome: Chromosome) -> bool:
        """Move sessions out of blocked time windows."""
        for gene in chromosome.genes:
            # Skip locked genes - they cannot be moved
            if gene.is_locked:
                continue

            if self.config.is_blocked(gene.day, gene.start_time, gene.end_time):
                # Try to find nearby valid slot
                repaired = self._find_alternative_slot(gene, chromosome)
                if not repaired:
                    return False
        return True

    def _repair_invalid_start_times(self, chromosome: Chromosome) -> bool:
        """Snap start times to nearest allowed start time."""
        for gene in chromosome.genes:
            # Skip locked genes - their time is fixed
            if gene.is_locked:
                continue

            if not self.config.is_valid_start_time(gene.start_time):
                # Find nearest allowed start time
                nearest = self._find_nearest_start_time(gene.start_time)
                gene.update_time(gene.day, nearest)
        return True

    def _repair_lab_contiguity(self, chromosome: Chromosome) -> bool:
        """Ensure lab sessions are 180 minutes."""
        for gene in chromosome.genes:
            # Skip locked genes
            if gene.is_locked:
                continue

            if gene.is_lab and gene.duration_minutes != 180:
                # Force to 180 minutes
                gene.duration_minutes = 180
                gene.end_time = calculate_slot_end_time(gene.start_time, 180)
                gene.duration_slots = 6
        return True

    def _repair_resource_conflicts(
            self,
            chromosome: Chromosome,
            resource_type: str,
            stats: RepairStats = None
    ) -> bool:
        """
        Repair overlaps for a resource (teacher/room/section).

        Strategy:
        1. Find all conflicts for this resource type
        2. For each conflict, move one (non-locked) session to alternative slot
        3. Track attempts to prevent infinite loops
        4. Skip conflicts where both genes are locked (unresolvable)

        Args:
            chromosome: Chromosome to repair
            resource_type: 'teacher', 'room', or 'section'
            stats: Optional stats tracker

        Returns:
            True if all conflicts resolved
        """
        if stats is None:
            stats = RepairStats()

        # Build conflict index
        conflicts = self._find_resource_conflicts(chromosome, resource_type)

        if not conflicts:
            return True

        # Track which conflicts we've already tried (to avoid infinite loops)
        tried_conflicts: Set[Tuple[str, str]] = set()
        local_attempts = 0
        max_local_attempts = self.config.max_repair_attempts * max(len(conflicts), 1)

        while conflicts and local_attempts < max_local_attempts:
            local_attempts += 1
            stats.total_attempts += 1

            # Check global limit
            if stats.total_attempts >= self.MAX_TOTAL_ATTEMPTS:
                return False

            # Pick conflict (prefer untried ones)
            conflict_genes = None
            for cg in conflicts:
                conflict_key = tuple(sorted([cg[0].session_key, cg[1].session_key]))
                if conflict_key not in tried_conflicts:
                    conflict_genes = cg
                    tried_conflicts.add(conflict_key)
                    break

            if conflict_genes is None:
                # All conflicts have been tried - pick random
                conflict_genes = random.choice(conflicts)

            # Try to move one of the conflicting genes (skip locked ones)
            movable_genes = [g for g in conflict_genes if not g.is_locked]

            if not movable_genes:
                # Both genes are locked - this conflict cannot be resolved
                stats.locked_conflicts_skipped += 1
                conflicts.remove(conflict_genes)
                continue

            # Sort movable genes by session_key for deterministic ordering
            movable_genes.sort(key=lambda g: g.session_key)

            repair_success = False
            for gene in movable_genes:
                # Find gene index in chromosome
                gene_idx = next(
                    (i for i, g in enumerate(chromosome.genes) if g.session_key == gene.session_key),
                    None
                )

                if gene_idx is None:
                    continue

                # Try alternative slot
                if self._find_alternative_slot(chromosome.genes[gene_idx], chromosome):
                    repair_success = True
                    break

            if not repair_success:
                # Could not repair this conflict in this attempt
                # Will retry on next pass if conflicts remain
                pass

            # Re-check conflicts
            conflicts = self._find_resource_conflicts(chromosome, resource_type)

        # Return success if no conflicts remain
        return len(conflicts) == 0

    def _find_resource_conflicts(
            self,
            chromosome: Chromosome,
            resource_type: str
    ) -> List[List[Gene]]:
        """
        Find all conflicts for a resource type.

        Returns:
            List of conflict groups (each group = list of overlapping genes)
        """
        conflicts = []

        # Build schedule index
        schedule = defaultdict(lambda: defaultdict(list))

        for gene in chromosome.genes:
            if resource_type == 'teacher':
                resource_id = gene.teacher_id
            elif resource_type == 'room':
                resource_id = gene.room_id
            else:  # section
                resource_id = gene.section_id

            schedule[resource_id][gene.day].append(gene)

        # Check each resource's schedule for overlaps
        for resource_id, days in schedule.items():
            for day, genes in days.items():
                # Check all pairs
                for i in range(len(genes)):
                    for j in range(i + 1, len(genes)):
                        if slots_overlap(
                                genes[i].start_time, genes[i].end_time,
                                genes[j].start_time, genes[j].end_time
                        ):
                            conflicts.append([genes[i], genes[j]])

        return conflicts

    def _find_alternative_slot(
            self,
            gene: Gene,
            chromosome: Chromosome
    ) -> bool:
        """
        Find alternative slot for a gene that avoids conflicts.

        Args:
            gene: Gene to relocate
            chromosome: Current chromosome (for conflict checking)

        Returns:
            True if alternative found and applied
        """
        # Cannot move locked genes
        if gene.is_locked:
            return False

        attempts = 0
        max_attempts = self.config.max_repair_attempts

        # Get available rooms
        if gene.is_lab:
            available_rooms = self.lab_rooms if self.lab_rooms else self.all_rooms
        else:
            available_rooms = self.theory_rooms if self.theory_rooms else self.all_rooms

        while attempts < max_attempts:
            attempts += 1

            # Random day and time
            new_day = random.choice(self.config.working_days)
            new_start = random.choice(self.config.allowed_start_times)
            new_end = calculate_slot_end_time(new_start, gene.duration_minutes)

            # Check if blocked
            if self.config.is_blocked(new_day, new_start, new_end):
                continue

            # Try random room
            new_room_code = random.choice(available_rooms)
            room_row = self.rooms_df[self.rooms_df['Room_Code'] == new_room_code].iloc[0]
            new_room_id = room_row.get('Room_ID', hash(new_room_code) % 10000)

            # Check if this creates conflicts
            temp_gene = Gene(
                session_key=gene.session_key,
                course_id=gene.course_id,
                course_code=gene.course_code,
                course_name=gene.course_name,
                section_id=gene.section_id,
                section_code=gene.section_code,
                teacher_id=gene.teacher_id,
                teacher_name=gene.teacher_name,
                duration_minutes=gene.duration_minutes,
                is_lab=gene.is_lab,
                session_number=gene.session_number,
                day=new_day,
                start_time=new_start,
                room_id=new_room_id,
                room_code=new_room_code
            )

            # Check for conflicts with other genes (excluding self)
            has_conflict = False
            for other_gene in chromosome.genes:
                if other_gene.session_key == gene.session_key:
                    continue

                # Teacher conflict
                if other_gene.teacher_id == temp_gene.teacher_id and other_gene.day == temp_gene.day:
                    if slots_overlap(
                            other_gene.start_time, other_gene.end_time,
                            temp_gene.start_time, temp_gene.end_time
                    ):
                        has_conflict = True
                        break

                # Room conflict
                if other_gene.room_id == temp_gene.room_id and other_gene.day == temp_gene.day:
                    if slots_overlap(
                            other_gene.start_time, other_gene.end_time,
                            temp_gene.start_time, temp_gene.end_time
                    ):
                        has_conflict = True
                        break

                # Section conflict
                if other_gene.section_id == temp_gene.section_id and other_gene.day == temp_gene.day:
                    if slots_overlap(
                            other_gene.start_time, other_gene.end_time,
                            temp_gene.start_time, temp_gene.end_time
                    ):
                        has_conflict = True
                        break

            if not has_conflict:
                # Apply the new assignment
                gene.update_time(new_day, new_start)
                gene.update_room(new_room_id, new_room_code)
                return True

        return False

    def _find_nearest_start_time(self, current_time: str) -> str:
        """Find nearest allowed start time."""
        from classsync_core.utils import time_to_minutes

        current_minutes = time_to_minutes(current_time)

        min_diff = float('inf')
        nearest = self.config.allowed_start_times[0]

        for allowed_time in self.config.allowed_start_times:
            allowed_minutes = time_to_minutes(allowed_time)
            diff = abs(current_minutes - allowed_minutes)

            if diff < min_diff:
                min_diff = diff
                nearest = allowed_time

        return nearest