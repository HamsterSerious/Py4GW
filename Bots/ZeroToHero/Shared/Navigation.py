"""
Navigation.py - Smart movement handler for ZeroToHero missions.

Provides:
- Path following with automatic combat pausing
- Stuck/gate detection with patient waiting
- Post-combat safety delays
"""

from Py4GWCoreLib import *
from .InteractionUtils import BundleHandler


class MissionNavigation:
    """
    Handles 'Smart Movement' for missions.
    - Moves along a path
    - Pauses to fight if enemies are near
    - Detects if 'Stuck' (blocked by gate) and waits patiently
    """
    
    def __init__(self, combat_handler):
        """
        Args:
            combat_handler: CombatHandler instance for combat execution
        """
        self.combat_handler = combat_handler
        
        # Internal handlers
        self.movement_handler = Routines.Movement.FollowXY()
        
        # State
        self.last_pos = (0, 0)
        self.waiting_for_aggro_clear = False
        
        # Timers
        self.stuck_timer = Timer()
        self.stuck_timer.Start()
        
        self.combat_timer = Timer()
        self.combat_timer.Start()
        
        self.stuck_log_timer = Timer()
        self.stuck_log_timer.Start()

    def Reset(self):
        """Resets the navigation state."""
        self.movement_handler.reset()
        self.stuck_timer.Reset()
        self.combat_timer.Reset()
        self.stuck_log_timer.Reset()
        self.waiting_for_aggro_clear = False
        self.last_pos = Player.GetXY()

    def Execute(self, path_handler, logger=None):
        """
        Main Routine. Call this every frame.
        
        Args:
            path_handler: PathHandler with waypoints
            logger: Optional logger for status messages
            
        Returns:
            bool: True if the path is finished and safe, False otherwise
        """
        # --------------------------------------------------------
        # 0. BUNDLE CHECK - Skip combat if holding an item
        # --------------------------------------------------------
        is_holding_bundle = BundleHandler.IsHoldingBundle()
        
        enemies = self.GetNearbyEnemies()

        # --------------------------------------------------------
        # 1. COMBAT CHECK
        # --------------------------------------------------------
        if enemies:
            # Always pause when enemies are nearby
            # But only attack if NOT holding a bundle
            if not is_holding_bundle:
                target_id = enemies[0]
                self.combat_handler.Execute(target_agent_id=target_id)
            # else: Let heroes/henchmen handle it while we hold the bundle
            
            # Reset checks while in combat (regardless of bundle)
            self.combat_timer.Reset()
            self.stuck_timer.Reset()
            self.waiting_for_aggro_clear = True
            return False  # Don't continue moving until enemies are dead

        # --------------------------------------------------------
        # 2. POST-COMBAT DELAY
        # --------------------------------------------------------
        if self.waiting_for_aggro_clear:
            # Wait 2s after combat to ensure safety
            if self.combat_timer.HasElapsed(2000):
                self.waiting_for_aggro_clear = False
            else:
                return False

        # --------------------------------------------------------
        # 3. STUCK / GATE DETECTION
        # --------------------------------------------------------
        player_x, player_y = Player.GetXY()
        dist_moved = Utils.Distance((player_x, player_y), self.last_pos)

        # If we barely moved (< 50 units) in the last 3 seconds
        if dist_moved < 50:
            if self.stuck_timer.HasElapsed(3000):
                # Only log every 15 seconds
                if self.stuck_log_timer.HasElapsed(15000):
                    if logger:
                        logger.Add("Waiting for path to clear...", (1.0, 0.5, 0.0, 1.0))
                    self.stuck_log_timer.Reset()
        else:
            # Moving fine, reset trackers
            self.stuck_timer.Reset()
            self.stuck_log_timer.Reset()
            self.last_pos = (player_x, player_y)

        # --------------------------------------------------------
        # 4. MOVEMENT EXECUTION
        # --------------------------------------------------------
        Routines.Movement.FollowPath(path_handler, self.movement_handler)

        if Routines.Movement.IsFollowPathFinished(path_handler, self.movement_handler):
            self.movement_handler.reset()
            return True

        return False

    def GetNearbyEnemies(self, max_distance=1200):
        """
        Returns list of alive enemy Agent IDs within range.
        
        Args:
            max_distance (float): Search radius (default: Earshot)
            
        Returns:
            list: Enemy agent IDs
        """
        player_x, player_y = Player.GetXY()
        enemies = AgentArray.GetEnemyArray()
        enemies = AgentArray.Filter.ByDistance(enemies, (player_x, player_y), max_distance)
        enemies = AgentArray.Filter.ByCondition(enemies, lambda id: Agent.IsAlive(id))
        return enemies
