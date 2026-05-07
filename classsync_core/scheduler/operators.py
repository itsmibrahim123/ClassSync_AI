"""
Genetic Operators - Mutation and Crossover implementations.
"""
import random
from typing import List, Tuple
from copy import deepcopy
from classsync_core.scheduler.chromosome import Chromosome, Gene
from classsync_core.scheduler.config import GAConfig
from classsync_core.utils import calculate_slot_end_time, time_to_minutes
class GeneticOperators:

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

        # Time slots (valid combinations)
        self.time_slots = []
        for day in config.working_days:
            for start_time in config.allowed_start_times:
                self.time_slots.append((day, start_time))


    def crossover(
            self,
            parent1: Chromosome,
            parent2: Chromosome,
            method: str = 'day_based'
    ) -> Tuple[Chromosome, Chromosome]:
        """
        Perform crossover between two parents.

        Args:
            parent1, parent2: Parent chromosomes
            method: 'day_based' or 'uniform'

        Returns:
            Two offspring chromosomes
        """
        if method == 'day_based' or random.random() < self.config.day_based_crossover_ratio:
            return self._day_based_crossover(parent1, parent2)
        else:
            return self._uniform_crossover(parent1, parent2)


    def _day_based_crossover(
            self,
            parent1: Chromosome,
            parent2: Chromosome
    ) -> Tuple[Chromosome, Chromosome]:
        """
        Day-based crossover: inherit complete days from each parent.
        Example: Child1 gets Mon/Wed/Fri from P1, Tue/Thu from P2

        IMPORTANT: Locked genes are always copied from parent1 and restored
        to their locked values to ensure lock integrity.
        """
        # Build lookup for locked genes from parent1 (authoritative source)
        locked_genes_p1 = {g.session_key: g for g in parent1.genes if g.is_locked}

        # Randomly split days
        days = self.config.working_days[:]
        random.shuffle(days)
        split_point = len(days) // 2

        days_from_p1 = set(days[:split_point])
        days_from_p2 = set(days[split_point:])

        # Create offspring 1
        child1_genes = []
        child1_keys = set()

        # First: Add all locked genes from parent1 (never from parent2)
        for gene in parent1.genes:
            if gene.is_locked:
                new_gene = deepcopy(gene)
                new_gene.restore_lock()  # Ensure locked values are restored
                child1_genes.append(new_gene)
                child1_keys.add(gene.session_key)

        # Then: Add non-locked genes based on day split
        for gene in parent1.genes:
            if gene.session_key in child1_keys:
                continue  # Already added as locked
            if gene.day in days_from_p1:
                child1_genes.append(deepcopy(gene))
                child1_keys.add(gene.session_key)

        for gene in parent2.genes:
            if gene.session_key in child1_keys:
                continue  # Already added
            if gene.day in days_from_p2:
                child1_genes.append(deepcopy(gene))
                child1_keys.add(gene.session_key)

        # Fill any missing genes from parent1
        for gene in parent1.genes:
            if gene.session_key not in child1_keys:
                child1_genes.append(deepcopy(gene))
                child1_keys.add(gene.session_key)

        # Create offspring 2 (opposite day assignment)
        child2_genes = []
        child2_keys = set()

        # First: Add all locked genes from parent1
        for gene in parent1.genes:
            if gene.is_locked:
                new_gene = deepcopy(gene)
                new_gene.restore_lock()
                child2_genes.append(new_gene)
                child2_keys.add(gene.session_key)

        # Then: Add non-locked genes based on opposite day split
        for gene in parent2.genes:
            if gene.session_key in child2_keys:
                continue
            if gene.day in days_from_p1:
                child2_genes.append(deepcopy(gene))
                child2_keys.add(gene.session_key)

        for gene in parent1.genes:
            if gene.session_key in child2_keys:
                continue
            if gene.day in days_from_p2:
                child2_genes.append(deepcopy(gene))
                child2_keys.add(gene.session_key)

        # Fill any missing genes from parent1
        for gene in parent1.genes:
            if gene.session_key not in child2_keys:
                child2_genes.append(deepcopy(gene))
                child2_keys.add(gene.session_key)

        return Chromosome(child1_genes), Chromosome(child2_genes)


    def _uniform_crossover(
            self,
            parent1: Chromosome,
            parent2: Chromosome
    ) -> Tuple[Chromosome, Chromosome]:
        """
        Uniform crossover: randomly inherit each gene from either parent.

        IMPORTANT: Locked genes are always copied from parent1 and restored
        to their locked values. Non-locked genes are randomly inherited.
        """
        child1_genes = []
        child2_genes = []

        for i in range(len(parent1.genes)):
            gene1 = parent1.genes[i]

            # For locked genes: always use parent1's version and restore lock
            if gene1.is_locked:
                new_gene1 = deepcopy(gene1)
                new_gene1.restore_lock()
                child1_genes.append(new_gene1)

                new_gene2 = deepcopy(gene1)
                new_gene2.restore_lock()
                child2_genes.append(new_gene2)
            else:
                # For non-locked genes: random inheritance
                if random.random() < 0.5:
                    child1_genes.append(deepcopy(parent1.genes[i]))
                    child2_genes.append(deepcopy(parent2.genes[i]))
                else:
                    child1_genes.append(deepcopy(parent2.genes[i]))
                    child2_genes.append(deepcopy(parent1.genes[i]))

        return Chromosome(child1_genes), Chromosome(child2_genes)


    def mutate(self, chromosome: Chromosome, generation: int) -> Chromosome:
        """
        Apply mutation to chromosome.
        Mutation rate decreases over generations.
        Locked genes are skipped (cannot be mutated).

        Args:
            chromosome: Chromosome to mutate
            generation: Current generation number

        Returns:
            Mutated chromosome
        """
        mutation_rate = self.config.get_mutation_rate(generation)

        mutated = chromosome.copy()

        for i, gene in enumerate(mutated.genes):
            # Skip locked genes - they cannot be mutated
            if gene.is_locked:
                continue

            if random.random() < mutation_rate:
                # Choose random mutation type
                mutation_type = random.choice([
                    'time_swap', 'day_swap', 'room_swap', 'time_shift'
                ])

                if mutation_type == 'time_swap':
                    mutated.genes[i] = self._mutate_time_swap(gene)
                elif mutation_type == 'day_swap':
                    mutated.genes[i] = self._mutate_day_swap(gene)
                elif mutation_type == 'room_swap':
                    mutated.genes[i] = self._mutate_room_swap(gene)
                elif mutation_type == 'time_shift':
                    mutated.genes[i] = self._mutate_time_shift(gene)

        return mutated


    def _mutate_time_swap(self, gene: Gene) -> Gene:
        """Change to different allowed start time on same day."""
        new_gene = deepcopy(gene)
        day_end_minutes = time_to_minutes(self.config.day_end_time)

        # Pick different start time
        available_times = []
        for t in self.config.allowed_start_times:
            if t != gene.start_time:
                # Check if this start time fits within the day
                end_time = calculate_slot_end_time(t, gene.duration_minutes)
                if time_to_minutes(end_time) <= day_end_minutes:
                    available_times.append(t)
        
        if not available_times:
            return new_gene

        new_start = random.choice(available_times)
        new_gene.update_time(gene.day, new_start)

        return new_gene


    def _mutate_day_swap(self, gene: Gene) -> Gene:
        """Move session to different day, same time."""
        new_gene = deepcopy(gene)

        # Pick different day
        available_days = [d for d in self.config.working_days if d != gene.day]
        if not available_days:
            return new_gene

        new_day = random.choice(available_days)
        new_gene.update_time(new_day, gene.start_time)

        return new_gene


    def _mutate_room_swap(self, gene: Gene) -> Gene:
        """Assign different room of appropriate type."""
        new_gene = deepcopy(gene)

        # Get appropriate room list
        if gene.is_lab:
            available_rooms = [r for r in self.lab_rooms if r != gene.room_code]
        else:
            available_rooms = [r for r in self.theory_rooms if r != gene.room_code]

        if not available_rooms:
            available_rooms = [r for r in self.all_rooms if r != gene.room_code]

        if not available_rooms:
            return new_gene

        new_room_code = random.choice(available_rooms)
        room_row = self.rooms_df[self.rooms_df['Room_Code'] == new_room_code].iloc[0]
        new_room_id = room_row.get('Room_ID', hash(new_room_code) % 10000)

        new_gene.update_room(new_room_id, new_room_code)

        return new_gene


    def _mutate_time_shift(self, gene: Gene) -> Gene:
        """Shift to adjacent time slot (±1 slot) if valid."""
        new_gene = deepcopy(gene)
        day_end_minutes = time_to_minutes(self.config.day_end_time)

        # Find current index in allowed times
        try:
            current_idx = self.config.allowed_start_times.index(gene.start_time)
        except ValueError:
            return new_gene

        # Try shift up or down
        shift = random.choice([-1, 1])
        new_idx = current_idx + shift

        if 0 <= new_idx < len(self.config.allowed_start_times):
            new_start = self.config.allowed_start_times[new_idx]
            
            # Check if new start time fits within the day
            end_time = calculate_slot_end_time(new_start, gene.duration_minutes)
            if time_to_minutes(end_time) <= day_end_minutes:
                new_gene.update_time(gene.day, new_start)

        return new_gene