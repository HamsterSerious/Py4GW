"""
UI package for Zero To Hero bot.

Contains all user interface components:
- BaseWindow: Common window functionality
- DashboardUI: Main control interface
- NotificationWindow: Mandatory loadout warnings
- QueueWindow: Task queue management
- TaskInfoWindow: Task details display
- TeamWindow: Team configuration
- Theme: Styling utilities
"""
from .base_window import BaseWindow, ClosableWindow
from .dashboard import DashboardUI
from .notification_window import NotificationWindow
from .queue_window import QueueWindow
from .task_info_window import TaskInfoWindow
from .team_window import TeamWindow
from .themes import Theme

__all__ = [
    'BaseWindow',
    'ClosableWindow',
    'DashboardUI',
    'NotificationWindow',
    'QueueWindow',
    'TaskInfoWindow',
    'TeamWindow',
    'Theme',
]
