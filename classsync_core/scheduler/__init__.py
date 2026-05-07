"""
ClassSync AI Genetic Algorithm Scheduler
Production-ready timetable optimization system.
"""

from classsync_core.scheduler.config import GAConfig, DEFAULT_GA_CONFIG
from classsync_core.scheduler.chromosome import Chromosome, Gene
from classsync_core.scheduler.fitness_evaluator import FitnessEvaluator
from classsync_core.scheduler.ga_engine import GAEngine
from classsync_core.scheduler.initializer import PopulationInitializer
from classsync_core.scheduler.operators import GeneticOperators
from classsync_core.scheduler.repair import RepairMechanism

__all__ = [
    'GAConfig',
    'DEFAULT_GA_CONFIG',
    'Chromosome',
    'Gene',
    'FitnessEvaluator',
    'GAEngine',
    'PopulationInitializer',
    'GeneticOperators',
    'RepairMechanism'
]

__version__ = '1.0.0'
