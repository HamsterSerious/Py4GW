from Py4GWCoreLib import *

class MissionNavigation:
    """
    Handles 'Smart Movement' for missions.
    - Moves along a path.
    - Pauses to fight if enemies are near.
    - Detects if 'Stuck' (blocked by gate) and waits patiently.
    """
    def __init__(self, combat_handler):
        self.combat_handler = combat_handler
        
        # internal handlers
        self.movement_handler = Routines.Movement.FollowXY()
        
        # State
        self.last_pos = (0, 0)
        self.waiting_for_aggro_clear = False
        
        # Timers
        self.stuck_timer = Timer()
        self.stuck_timer.Start()
        
        self.combat_timer = Timer()
        self.combat_timer.Start()
        
        # FIX #4: Separate timer for stuck warning logging
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
        Returns: True if the path is finished and safe. False otherwise.
        """
        enemies = self.GetNearbyEnemies()

        # --------------------------------------------------------
        # 1. COMBAT CHECK
        # --------------------------------------------------------
        if enemies:
            # We have enemies. Fight them.
            target_id = enemies[0]
            
            # FIX #2: Actually engage the enemy
            self.combat_handler.Execute(target_agent_id=target_id)
            
            # Reset checks while fighting
            self.combat_timer.Reset()
            self.stuck_timer.Reset()
            self.waiting_for_aggro_clear = True
            return False # Not finished moving

        # --------------------------------------------------------
        # 2. POST-COMBAT DELAY
        # --------------------------------------------------------
        if self.waiting_for_aggro_clear:
            # We just finished combat. Wait a moment (2s) to ensure no lag/respawn
            if self.combat_timer.HasElapsed(2000):
                self.waiting_for_aggro_clear = False
            else:
                return False # Waiting for safety

        # --------------------------------------------------------
        # 3. STUCK / GATE DETECTION
        # --------------------------------------------------------
        # This logic handles waiting for gates to open without erroring out.
        player_x, player_y = Player.GetXY()
        dist_moved = Utils.Distance((player_x, player_y), self.last_pos)

        # If we barely moved (< 50 units) in the last 3 seconds
        if dist_moved < 50:
            if self.stuck_timer.HasElapsed(3000):
                # FIX #4: Only log every 10 seconds using separate timer
                if self.stuck_log_timer.HasElapsed(10000):
                    if logger:
                        logger.Add(f"Path blocked (Waiting for gate/obstacle)...", (1.0, 0.5, 0.0, 1.0), prefix="[Nav]")
                    self.stuck_log_timer.Reset()
                # We are blocked but continue trying to move
        else:
            # We are moving fine, reset the stuck tracker
            self.stuck_timer.Reset()
            self.stuck_log_timer.Reset()  # Also reset log timer when moving
            self.last_pos = (player_x, player_y)

        # --------------------------------------------------------
        # 4. MOVEMENT EXECUTION
        # --------------------------------------------------------
        Routines.Movement.FollowPath(path_handler, self.movement_handler)

        if Routines.Movement.IsFollowPathFinished(path_handler, self.movement_handler):
            # We are at the end of the path AND no enemies are around.
            # Reset handler for next use
            self.movement_handler.reset()
            return True

        return False

    def GetNearbyEnemies(self):
        """Returns list of alive enemy Agent IDs within Earshot (1200)."""
        player_x, player_y = Player.GetXY()
        enemies = AgentArray.GetEnemyArray()
        enemies = AgentArray.Filter.ByDistance(enemies, (player_x, player_y), 1200)
        enemies = AgentArray.Filter.ByCondition(enemies, lambda id: Agent.IsAlive(id))
        return enemies
