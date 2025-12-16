"""
Constants and configuration values for Zero To Hero bot.
"""

# Bot Identity
BOT_NAME = "ZeroToHero"
BOT_VERSION = "0.2.0"
BOT_AUTHOR = "Paul"

# Window Configuration
WINDOW_SIZE = (450, 600)  # Main dashboard (wider + taller)
QUEUE_WINDOW_SIZE = (400, 350)  # Queue manager (larger)
TASK_INFO_WINDOW_SIZE = (500, 300)  # Task info (wider, shorter)
NOTIFICATION_WINDOW_SIZE = (550, 350)  # Requirement warning (wider, shorter)

# Campaign display order (folder names)
CAMPAIGN_ORDER = [
    "prophecies",
    "factions",
    "nightfall",
    "eye_of_the_north",
    "extra"
]

# Campaign display names (folder name -> display name)
CAMPAIGN_DISPLAY_NAMES = {
    "prophecies": "Prophecies (Missions + Main Quests)",
    "factions": "Factions (Missions + Main Quests)",
    "nightfall": "Nightfall (Missions + Main Quests)",
    "eye_of_the_north": "Eye of the North (Missions + Main Quests)",
    "eotn": "Eye of the North (Missions + Main Quests)",
    "extra": "Extra (Skill Unlocks etc.)"
}

# Task filter options for UI dropdown
TASK_FILTER_OPTIONS = ["All", "Mission", "Quest", "Task"]


def get_campaign_display_name(folder_name: str) -> str:
    """Get the display name for a campaign folder."""
    return CAMPAIGN_DISPLAY_NAMES.get(folder_name, folder_name.replace("_", " ").title())


class Colors:
    """Standard colors used throughout the UI."""
    
    # Text colors
    HEADER = (0.4, 0.8, 1.0, 1.0)       # Light blue for headers
    INFO_COLOR = (0.3, 0.7, 1.0, 1.0)   # Blue for info text
    SUCCESS_COLOR = (0.3, 1.0, 0.3, 1.0) # Green for success
    WARN_COLOR = (1.0, 0.8, 0.2, 1.0)   # Yellow for warnings
    ERROR_COLOR = (1.0, 0.3, 0.3, 1.0)  # Red for errors
    
    # Mode indicators
    HM_COLOR = (1.0, 0.5, 0.3, 1.0)     # Orange for Hard Mode
    NM_COLOR = (0.5, 0.8, 0.5, 1.0)     # Light green for Normal Mode
    
    # UI elements
    ICON = (0.5, 0.8, 1.0, 1.0)         # Icon tint color
    DISABLED = (0.5, 0.5, 0.5, 1.0)     # Grayed out
    
    # Background colors (with alpha)
    PANEL_BG = (0.15, 0.15, 0.15, 0.95)
    HIGHLIGHT_BG = (0.3, 0.3, 0.4, 0.8)