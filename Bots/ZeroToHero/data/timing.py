"""
Timing constants for Zero To Hero bot.

Centralizes all delay values to avoid magic numbers scattered throughout code.
All values are in milliseconds unless otherwise noted.
"""


class Timing:
    """Delay constants for various operations."""
    
    # ===================
    # MAP / TRAVEL
    # ===================
    MAP_TRAVEL_INITIAL = 2000       # Wait after initiating travel
    MAP_READY_POLL = 500            # Polling interval while waiting for map
    MAP_LOAD_BUFFER = 1000          # Extra buffer after map reports ready
    MAP_LOAD_TIMEOUT = 30000        # Max time to wait for map load
    MAP_EXIT_TIMEOUT = 60000        # Max time to wait for mission end
    POST_TRAVEL_DELAY = 1500        # Wait after arriving before party operations (game needs time to initialize)
    
    # ===================
    # PARTY MANAGEMENT
    # ===================
    PARTY_DISBAND_WAIT = 500        # Wait after kicking heroes
    HERO_ADD_DELAY = 300            # Wait after adding a hero
    HERO_APPEAR_TIMEOUT = 3.0       # Seconds to wait for hero to appear
    
    # ===================
    # SKILL / BUILD LOADING
    # ===================
    SKILL_TEMPLATE_LOAD = 200       # Wait after loading a skill template
    SKILL_VERIFY_DELAY = 1000       # Wait before verifying skills loaded
    BUILD_APPLY_DELAY = 200         # Wait after applying build to hero
    
    # ===================
    # MODE SWITCHING
    # ===================
    HARD_MODE_TOGGLE = 1500         # Wait after toggling hard mode (needs time to register)
    
    # ===================
    # NPC / INTERACTION
    # ===================
    MOVEMENT_POLL = 100             # Polling interval while moving
    INTERACT_DELAY = 250            # Wait after basic interaction
    NPC_DIALOG_OPEN_DELAY = 1500    # Wait for NPC dialog window to open after interact
    DIALOG_SEND_DELAY = 500         # Wait between dialog send attempts
    MISSION_COUNTDOWN_WAIT = 12000  # Wait for mission countdown (5-10 sec countdown + buffer)
    GADGET_SEARCH_TIMEOUT = 5000    # Max time to search for a gadget
    GADGET_PICKUP_DELAY = 500       # Wait after picking up gadget
    GADGET_USE_DELAY = 1000         # Wait after using gadget on target
    
    # ===================
    # COMBAT
    # ===================
    COMBAT_TICK = 100               # Main combat loop tick (via yield)
    COMBAT_TIMEOUT = 60000          # Max time to fight a single target
    KILL_ALL_TIMEOUT = 120000       # Max time to clear an area
    
    # ===================
    # UI / GENERAL
    # ===================
    FRAME_DELAY = 100               # Generic single-frame-ish delay
    SHORT_DELAY = 200               # Short operation delay
    MEDIUM_DELAY = 500              # Medium operation delay
    LONG_DELAY = 1000               # Long operation delay
    
    # ===================
    # MONITOR / BACKGROUND
    # ===================
    MONITOR_TICK = 500              # Background monitor polling interval


class Range:
    """
    Distance constants for combat and interactions.
    All values are in game units.
    """
    
    # ===================
    # STANDARD GAME RANGES
    # ===================
    MELEE = 144                     # Touch/melee range
    NEARBY = 252                    # Nearby range (adjacent)
    AREA = 322                      # Area effect range
    EARSHOT = 1012                  # Earshot/aggro range
    SPELLCAST = 1248                # Standard spellcasting range
    SPIRIT = 2500                   # Spirit range
    COMPASS = 5000                  # Compass/radar range
    
    # ===================
    # COMBAT RANGES
    # ===================
    COMBAT_DEFAULT = 900            # Default engagement range
    COMBAT_MELEE = 144              # Melee combat range
    COMBAT_RANGED = 1100            # Ranged combat range
    
    # ===================
    # MOVEMENT / NAVIGATION
    # ===================
    WAYPOINT_ARRIVAL = 150          # Distance to consider "arrived" at waypoint
    INTERACT_RANGE = 200            # Close enough to interact
    NPC_APPROACH = 250              # Standard NPC approach distance
    
    # ===================
    # TARGETING
    # ===================
    AGGRO_RANGE = 1500              # Range to detect/aggro enemies
    TARGET_ENGAGE = 2000            # Range to abandon pathing and engage target
    TARGET_ATTACK = 1200            # Range to start attacking target
    BOSS_ENGAGE = 2000              # Range to engage boss targets
    BOSS_ATTACK = 1200              # Range to attack boss
    
    # ===================
    # SEARCH RANGES
    # ===================
    GADGET_SEARCH = 5000            # Max range to search for gadgets
    NPC_SEARCH = 3000               # Max range to search for NPCs
    ENEMY_SEARCH = 2500             # Default enemy search radius