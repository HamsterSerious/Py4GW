"""
Core package for Zero To Hero bot.

Contains:
- ZeroToHeroBot: Main bot controller
- BaseTask: Task base class (declarative pattern)
- TaskRegistry: Task discovery and queue management
- TaskExecutor: Task tracking (FSM handles execution)
- Constants: Configuration values
"""
from .base_task import BaseTask
from .task_registry import TaskRegistry
from .task_executor import TaskExecutor, NotificationManager, SelectionState
from .constants import (
    BOT_NAME,
    BOT_VERSION,
    BOT_AUTHOR,
    WINDOW_SIZE,
    QUEUE_WINDOW_SIZE,
    TASK_INFO_WINDOW_SIZE,
    NOTIFICATION_WINDOW_SIZE,
    TEAM_WINDOW_SIZE,
    CAMPAIGN_ORDER,
    CAMPAIGN_DISPLAY_NAMES,
    TASK_FILTER_OPTIONS,
    get_campaign_display_name,
    Colors,
)

__all__ = [
    # Classes
    'BaseTask',
    'TaskRegistry',
    'TaskExecutor',
    'NotificationManager',
    'SelectionState',
    # Constants
    'BOT_NAME',
    'BOT_VERSION',
    'BOT_AUTHOR',
    'WINDOW_SIZE',
    'QUEUE_WINDOW_SIZE',
    'TASK_INFO_WINDOW_SIZE',
    'NOTIFICATION_WINDOW_SIZE',
    'TEAM_WINDOW_SIZE',
    'CAMPAIGN_ORDER',
    'CAMPAIGN_DISPLAY_NAMES',
    'TASK_FILTER_OPTIONS',
    'get_campaign_display_name',
    'Colors',
]