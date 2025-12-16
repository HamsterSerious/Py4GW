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