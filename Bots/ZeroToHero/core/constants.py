"""
Core constants for the Zero To Hero bot.
Centralizes all magic numbers, colors, and configuration values.
"""
from Py4GWCoreLib.py4gwcorelib_src.Color import Color

# ========================
# BOT CONFIGURATION
# ========================
BOT_NAME = "ZeroToHero"
BOT_VERSION = "1.0"
BOT_AUTHOR = "Paul"

# ========================
# UI CONFIGURATION
# ========================
WINDOW_SIZE = (400, 700)

# ========================
# THEME COLORS
# ========================
class Colors:
    """UI color scheme - Guild Wars inspired"""
    
    # Backgrounds
    WINDOW_BG = Color(28, 28, 28, 230).to_tuple_normalized()
    FRAME_BG = Color(48, 48, 48, 230).to_tuple_normalized()
    FRAME_HOVER = Color(68, 68, 68, 230).to_tuple_normalized()
    FRAME_ACTIVE = Color(58, 58, 58, 230).to_tuple_normalized()
    
    # Text
    BODY_TEXT = Color(139, 131, 99, 255).to_tuple_normalized()
    HEADER = Color(136, 117, 44, 255).to_tuple_normalized()
    ICON = Color(177, 152, 55, 255).to_tuple_normalized()
    DISABLED_TEXT = Color(140, 140, 140, 255).to_tuple_normalized()
    
    # UI Elements
    SEPARATOR = Color(90, 90, 90, 255).to_tuple_normalized()
    BUTTON = Color(33, 51, 58, 255).to_tuple_normalized()
    BUTTON_HOVER = Color(140, 140, 140, 255).to_tuple_normalized()
    BUTTON_ACTIVE = Color(90, 90, 90, 255).to_tuple_normalized()
    
    # Status Indicators
    HM_COLOR = (1.0, 0.3, 0.3, 1.0)      # Red - Hard Mode
    NM_COLOR = (0.3, 1.0, 0.3, 1.0)      # Green - Normal Mode
    WARN_COLOR = (1.0, 0.7, 0.0, 1.0)    # Orange - Warnings
    ERROR_COLOR = (1.0, 0.0, 0.0, 1.0)   # Red - Errors
    SUCCESS_COLOR = (0.0, 1.0, 0.0, 1.0) # Green - Success
    INFO_COLOR = (0.0, 1.0, 1.0, 1.0)    # Cyan - Info

# ========================
# CAMPAIGN SORTING
# ========================
CAMPAIGN_ORDER = [
    "Prophecies",
    "Factions", 
    "Nightfall",
    "Eye of the North",
    "EyeOfTheNorth",
    "Extra"
]

# ========================
# TASK FILTERS
# ========================
TASK_FILTER_OPTIONS = ["All", "Mission", "Quest"]