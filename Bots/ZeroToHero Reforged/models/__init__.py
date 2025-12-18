"""
Data models for Zero To Hero bot.
Centralizes all dataclasses and type definitions.
"""
from .loadout import (
    HeroRequirement,
    PlayerBuildRequirement,
    MandatoryLoadout,
    LoadoutConfig
)
from .task import TaskInfo, QueuedTask
from .requirements import (
    PlayerRequirements,
    HeroRequirements,
    LoadoutRequirements,
    TaskRequirementsAccessor
)

__all__ = [
    # Loadout (original dataclasses)
    'HeroRequirement',
    'PlayerBuildRequirement',
    'MandatoryLoadout',
    'LoadoutConfig',
    # Task
    'TaskInfo',
    'QueuedTask',
    # Requirements (unified access)
    'PlayerRequirements',
    'HeroRequirements',
    'LoadoutRequirements',
    'TaskRequirementsAccessor',
]
