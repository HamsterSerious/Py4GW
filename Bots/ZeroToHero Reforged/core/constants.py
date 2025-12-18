"""
Constants and configuration values for Zero To Hero bot.
"""

# Bot Identity
BOT_NAME = "ZeroToHero"
BOT_VERSION = "0.3.0"  # Bumped for refactor
BOT_AUTHOR = "Paul"

# Window Configuration
WINDOW_SIZE = (450, 600)
QUEUE_WINDOW_SIZE = (400, 350)
TASK_INFO_WINDOW_SIZE = (500, 300)
NOTIFICATION_WINDOW_SIZE = (550, 350)
TEAM_WINDOW_SIZE = (500, 450)
PROGRESS_WINDOW_SIZE = (350, 250)

# Campaign display order (must match actual folder names in campaigns/)
CAMPAIGN_ORDER = [
    "prophecies",
    "factions",
    "nightfall",
    "eotn",      # Fixed: was "eye_of_the_north"
    "extra"
]

# Campaign display names (folder name -> display name)
CAMPAIGN_DISPLAY_NAMES = {
    "prophecies": "Prophecies",
    "factions": "Factions",
    "nightfall": "Nightfall",
    "eotn": "Eye of the North",
    "extra": "Extra (Skills, Farming, etc.)"
}

# Task filter options for UI dropdown
TASK_FILTER_OPTIONS = ["All", "Mission", "Quest", "Task"]


def get_campaign_display_name(folder_name: str) -> str:
    """Get the display name for a campaign folder."""
    return CAMPAIGN_DISPLAY_NAMES.get(folder_name, folder_name.replace("_", " ").title())


class Colors:
    """Standard colors used throughout the UI."""
    
    # Text colors (RGBA tuples)
    HEADER = (0.4, 0.8, 1.0, 1.0)        # Light blue for headers
    INFO = (0.3, 0.7, 1.0, 1.0)          # Blue for info text
    SUCCESS = (0.3, 1.0, 0.3, 1.0)       # Green for success
    WARNING = (1.0, 0.8, 0.2, 1.0)       # Yellow for warnings
    ERROR = (1.0, 0.3, 0.3, 1.0)         # Red for errors
    
    # Mode indicators
    HARD_MODE = (1.0, 0.5, 0.3, 1.0)     # Orange for Hard Mode
    NORMAL_MODE = (0.5, 0.8, 0.5, 1.0)   # Light green for Normal Mode
    
    # UI elements
    ICON = (0.5, 0.8, 1.0, 1.0)          # Icon tint color
    DISABLED = (0.5, 0.5, 0.5, 1.0)      # Grayed out
    MUTED = (0.6, 0.6, 0.6, 1.0)         # Muted text
    BUILD_CODE = (0.7, 1.0, 0.7, 1.0)    # Build code text (clickable)
    
    # Background colors (with alpha)
    PANEL_BG = (0.15, 0.15, 0.15, 0.95)
    HIGHLIGHT_BG = (0.3, 0.3, 0.4, 0.8)
    
    # Legacy aliases (for backward compatibility during refactor)
    INFO_COLOR = INFO
    SUCCESS_COLOR = SUCCESS
    WARN_COLOR = WARNING
    ERROR_COLOR = ERROR
    HM_COLOR = HARD_MODE
    NM_COLOR = NORMAL_MODE
