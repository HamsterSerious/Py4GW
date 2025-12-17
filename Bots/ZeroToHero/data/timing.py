"""
Timing constants for Zero To Hero bot.

Centralizes all delay values to avoid magic numbers scattered throughout code.
All values are in milliseconds unless otherwise noted.
"""


class Timing:
    """Delay constants for various operations."""
    
    # Map/Travel
    MAP_TRAVEL_INITIAL = 2000       # Wait after initiating travel
    MAP_READY_POLL = 500            # Polling interval while waiting for map
    MAP_LOAD_BUFFER = 1000          # Extra buffer after map reports ready
    
    # Party Management
    PARTY_DISBAND_WAIT = 500        # Wait after kicking heroes
    HERO_ADD_DELAY = 300            # Wait after adding a hero
    HERO_APPEAR_TIMEOUT = 3.0       # Seconds to wait for hero to appear
    
    # Skill/Build Loading
    SKILL_TEMPLATE_LOAD = 200       # Wait after loading a skill template
    SKILL_VERIFY_DELAY = 1000       # Wait before verifying skills loaded
    BUILD_APPLY_DELAY = 200         # Wait after applying build to hero
    
    # Mode Switching
    HARD_MODE_TOGGLE = 1000         # Wait after toggling hard mode
    
    # NPC Interaction
    MOVEMENT_POLL = 100             # Polling interval while moving
    INTERACT_DELAY = 250            # Wait after interacting with NPC (Reduced from 1000)
    MISSION_LOAD_INITIAL = 2000     # Initial wait for mission load
    
    # Combat
    COMBAT_TICK = 100               # Main combat loop tick (via yield)
    
    # UI/General
    FRAME_DELAY = 100               # Generic single-frame-ish delay
    SHORT_DELAY = 200               # Short operation delay
    MEDIUM_DELAY = 500              # Medium operation delay
    LONG_DELAY = 1000               # Long operation delay


class Range:
    """
    Combat/interaction ranges.
    """
    COMBAT_DEFAULT = 900            # Default engagement range
    MELEE = 144                     # Touch/melee range
    NEARBY = 252                    # Nearby range
    AREA = 322                      # Area effect range
    EARSHOT = 1012                  # Earshot/aggro range
    SPELLCAST = 1248                # Spellcasting range
    SPIRIT = 2500                   # Spirit range
    COMPASS = 5000                  # Compass range