"""
Bot-specific enums for Zero To Hero.

Note: Game data enums (HeroType, Profession, Map IDs, etc.) should be
imported from Py4GWCoreLib instead of defined here.
"""
from enum import Enum


class TaskType(Enum):
    """Type of task for categorization and filtering."""
    MISSION = "Mission"
    QUEST = "Quest"
    TASK = "Task"


class GameMode(Enum):
    """Game difficulty mode."""
    NORMAL = "NM"
    HARD = "HM"
    
    @classmethod
    def from_bool(cls, hard_mode: bool) -> 'GameMode':
        """Convert boolean hard_mode flag to GameMode enum."""
        return cls.HARD if hard_mode else cls.NORMAL
    
    def to_bool(self) -> bool:
        """Convert GameMode to boolean (True = Hard Mode)."""
        return self == GameMode.HARD
