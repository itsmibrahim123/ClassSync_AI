"""
GA Engine - Main genetic algorithm orchestrator.
Coordinates selection, crossover, mutation, repair, and evaluation.
"""

import time
import random
from typing import List, Callable, Optional, Dict
from collections import defaultdict
import pandas as pd

from classsync_core.scheduler.config import GAConfig
from classsync_core.scheduler.chromosome import Chromosome
from classsync_core.scheduler.initializer import PopulationInitializer
from classsync_core.scheduler.operators import GeneticOperators
from classsync_core.scheduler.repair import RepairMechanism
from classsync_core.scheduler.fitness_evaluator import FitnessEvaluator


class GAEngine:
    """
    Main Genetic Algorithm engine for timetable optimization.
    
    Workflow:
    1. Initialize population
    2. Evaluate fitness
    3. For each generation:
       - Selection (tournament)
       - Crossover
       - Mutation
       - Repair
       - Evaluation
       - Elitism
    4. Return best solution
    """
    
    def __init__(
        self,
        config: GAConfig,
        sessions_df: pd.DataFrame,
        rooms_df: pd.DataFrame,
        teacher_constraints: list = None,
        room_constraints: list = None,
        locked_assignments: list = None,
        progress_callback: Optional[Callable] = None,
        random_seed: Optional[int] = None
    ):
        """
        Initialize GA engine.

        Args:
            config: GA configuration
            sessions_df: Sessions to schedule
            rooms_df: Available rooms
            teacher_constraints: List of teacher availability constraints
            room_constraints: List of room availability constraints
            locked_assignments: Pre-scheduled sessions to respect
            progress_callback: Optional callback for progress updates
            random_seed: Optional seed for reproducible results
        """
        self.config = config
        self.sessions_df = sessions_df
        self.rooms_df = rooms_df
        self.teacher_constraints = teacher_constraints or []
        self.room_constraints = room_constraints or []
        self.locked_assignments = locked_assignments or []
        self.progress_callback = progress_callback
        self.random_seed = random_seed

        # Initialize components with constraints
        self.initializer = PopulationInitializer(
            config, sessions_df, rooms_df,
            locked_assignments=self.locked_assignments
        )
        self.operators = GeneticOperators(config, rooms_df)
        self.repair = RepairMechanism(config, rooms_df)
        self.evaluator = FitnessEvaluator(
            config, rooms_df,
            teacher_constraints=self.teacher_constraints,
            room_constraints=self.room_constraints
        )

        # Statistics tracking
        self.best_fitness_history = []
        self.avg_fitness_history = []
        self.generation_times = []
        
    def run(
        self,
        population_size: Optional[int] = None,
        generations: Optional[int] = None
    ) -> Dict:
        """
        Run the genetic algorithm.
        
        Args:
            population_size: Population size (uses config default if None)
            generations: Number of generations (uses config default if None)
        
        Returns:
            Dictionary with results:
            {
                'best_chromosome': Chromosome,
                'best_fitness': float,
                'generation': int,
                'total_time': float,
                'statistics': {...}
            }
        """
        start_time = time.time()

        # Set random seed for reproducibility (if provided)
        if self.random_seed is not None:
            random.seed(self.random_seed)
            self._log(f"Random seed set to {self.random_seed} for reproducible results")

        pop_size = population_size or self.config.population_size
        max_gens = generations or self.config.generations

        # 1. Initialize population
        self._log("Initializing population...")
        population = self.initializer.create_population(pop_size)
        
        # 2. Evaluate initial population
        self._log("Evaluating initial population...")
        for chromosome in population:
            self.evaluator.evaluate(chromosome)
        
        # Track best solution
        best_chromosome = max(population, key=lambda c: c.fitness or 0)
        best_fitness = best_chromosome.fitness or 0
        stagnant_generations = 0
        
        # 3. Evolution loop
        for generation in range(max_gens):
            gen_start = time.time()
            
            # Create next generation
            new_population = self._create_next_generation(
                population, 
                generation
            )
            
            # Evaluate new population
            for chromosome in new_population:
                if chromosome.fitness is None:
                    self.evaluator.evaluate(chromosome)
            
            # Update best
            generation_best = max(new_population, key=lambda c: c.fitness or 0)
            if generation_best.fitness > best_fitness:
                best_chromosome = generation_best.copy()
                best_fitness = generation_best.fitness
                stagnant_generations = 0
            else:
                stagnant_generations += 1
            
            # Statistics
            avg_fitness = sum(c.fitness or 0 for c in new_population) / len(new_population)
            self.best_fitness_history.append(best_fitness)
            self.avg_fitness_history.append(avg_fitness)
            self.generation_times.append(time.time() - gen_start)
            
            # Logging
            if generation % self.config.log_interval == 0:
                self._log(
                    f"Gen {generation}/{max_gens}: "
                    f"Best={best_fitness:.2f}, Avg={avg_fitness:.2f}, "
                    f"Feasible={sum(1 for c in new_population if c.is_feasible)}/{len(new_population)}"
                )
            
            # Progress callback
            if self.progress_callback:
                self.progress_callback({
                    'generation': generation,
                    'max_generations': max_gens,
                    'best_fitness': best_fitness,
                    'avg_fitness': avg_fitness,
                    'is_feasible': best_chromosome.is_feasible,
                    'stagnant_generations': stagnant_generations
                })
            
            # Early stopping
            if best_fitness >= self.config.min_acceptable_fitness:
                self._log(f"Target fitness reached at generation {generation}!")
                break
            
            if stagnant_generations >= self.config.max_stagnant_generations:
                self._log(f"No improvement for {stagnant_generations} generations. Stopping.")
                break
            
            # Replace population
            population = new_population
        
        total_time = time.time() - start_time
        
        # Return results
        return {
            'best_chromosome': best_chromosome,
            'best_fitness': best_fitness,
            'generation': generation + 1,
            'total_time': total_time,
            'is_feasible': best_chromosome.is_feasible,
            'hard_violations': best_chromosome.hard_violations,
            'statistics': {
                'best_fitness_history': self.best_fitness_history,
                'avg_fitness_history': self.avg_fitness_history,
                'generation_times': self.generation_times,
                'final_population_size': len(population),
                'sessions_scheduled': len(best_chromosome.genes),
                'coverage_percentage': best_chromosome.get_statistics().get('coverage_percentage', 0)
            }
        }
    
    def _create_next_generation(
        self, 
        population: List[Chromosome],
        generation: int
    ) -> List[Chromosome]:
        """
        Create next generation using selection, crossover, mutation, and elitism.
        
        Args:
            population: Current population
            generation: Current generation number
        
        Returns:
            New population
        """
        new_population = []
        
        # Elitism: keep top individuals unchanged
        elite_count = max(1, int(len(population) * self.config.elitism_rate))
        elite = sorted(population, key=lambda c: c.fitness or 0, reverse=True)[:elite_count]
        new_population.extend([c.copy() for c in elite])
        
        # Generate offspring to fill rest of population
        offspring_needed = len(population) - elite_count
        
        while len(new_population) < len(population):
            # Selection
            parent1 = self._tournament_selection(population)
            parent2 = self._tournament_selection(population)
            
            # Crossover
            if random.random() < self.config.crossover_rate:
                child1, child2 = self.operators.crossover(parent1, parent2)
            else:
                child1, child2 = parent1.copy(), parent2.copy()
            
            # Mutation
            child1 = self.operators.mutate(child1, generation)
            child2 = self.operators.mutate(child2, generation)
            
            # Repair
            if self.repair.repair(child1):
                new_population.append(child1)
            else:
                # If unrepairable, use parent instead
                new_population.append(parent1.copy())
            
            if len(new_population) < len(population):
                if self.repair.repair(child2):
                    new_population.append(child2)
                else:
                    new_population.append(parent2.copy())
        
        # Trim to exact size
        return new_population[:len(population)]
    
    def _tournament_selection(self, population: List[Chromosome]) -> Chromosome:
        """
        Tournament selection: pick best from random subset.
        
        Args:
            population: Population to select from
        
        Returns:
            Selected chromosome
        """
        tournament = random.sample(
            population, 
            min(self.config.tournament_size, len(population))
        )
        return max(tournament, key=lambda c: c.fitness or 0)
    
    def _log(self, message: str):
        """Log message if logging enabled."""
        print(f"[GA] {message}")
