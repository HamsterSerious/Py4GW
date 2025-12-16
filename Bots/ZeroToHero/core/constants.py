"""
Constants and configuration values for Zero To Hero bot.
"""

# Bot Identity
BOT_NAME = "ZeroToHero"
BOT_VERSION = "0.2.0"
BOT_AUTHOR = "YourName"

# Window Configuration
WINDOW_SIZE = (400, 500)

# Campaign display order (for UI sorting)
CAMPAIGN_ORDER = [
    "prophecies",
    "factions",
    "nightfall",
    "eye_of_the_north",
    "extra"
]

# Task filter options for UI dropdown
TASK_FILTER_OPTIONS = ["All", "Mission", "Quest", "Task"]


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