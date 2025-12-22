"""
Team management for Zero To Hero bot.

Contains:
- TeamManager: Coordinator for team operations
- TeamConfigManager: Configuration persistence
- TeamComposer: Hero recruitment and builds
- BuildValidator: Testing and verification
"""
from .manager import TeamManager
from .config import TeamConfigManager
from .composer import TeamComposer
from .validator import BuildValidator

__all__ = [
    'TeamManager',
    'TeamConfigManager',
    'TeamComposer',
    'BuildValidator',
]