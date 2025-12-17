"""
Combat System - Handles combat encounters and skill usage.

Provides:
- Target killing (single and multiple)
- Path following with combat
- Boss/target hunting along paths
"""
from Py4GWCoreLib import Player, AgentArray, Utils
from Py4GWCoreLib.Builds.AutoCombat import AutoCombat
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib import Routines

from data.timing import Timing, Range
from utils.timer import Timeout


class Combat:
    """
    Handles combat encounters and skill usage.
    
    Key methods for missions:
    - hunt_target_along_path(): Follow path while hunting specific target
    - move_and_clear_path(): Follow path, clear enemies encountered
    - kill_target(): Kill a specific enemy
    - kill_all(): Clear all enemies in radius
    """
    
    def __init__(self):
        self.handler = AutoCombat()
        self.combat_range = Range.COMBAT_DEFAULT
        self.aggro_range = Range.AGGRO_RANGE

    # ==================
    # HIGH-LEVEL COMBAT API
    # ==================

    def hunt_target_along_path(
        self,
        path: list,
        target_model_id: int,
        engage_range: int = None,
        attack_range: int = None,
        clear_enemies: bool = True
    ):
        """
        Follows a path while hunting for a specific target (e.g., boss).
        
        When target is found:
        - Within engage_range: Abandon path and move toward target
        - Within attack_range: Stop and fight
        
        This is ideal for boss hunting patterns where you need to
        traverse the map but engage as soon as the boss is visible.
        
        Args:
            path: List of (x, y) waypoints to follow
            target_model_id: Model ID of target to hunt
            engage_range: Range at which to stop pathing and engage (default: Range.TARGET_ENGAGE)
            attack_range: Range at which to start attacking (default: Range.TARGET_ATTACK)
            clear_enemies: Whether to kill enemies encountered on path
            
        Yields for coroutine execution.
        Returns True if target was killed, False if path ended without finding target.
        """
        engage_range = engage_range or Range.TARGET_ENGAGE
        attack_range = attack_range or Range.TARGET_ATTACK
        
        path_index = 0
        
        while True:
            # Safety: Abort if map loading
            if GLOBAL_CACHE.Map.IsMapLoading():
                return False
            
            # Check for target
            target_id = Routines.Agents.GetAgentIDByModelID(target_model_id)
            
            if target_id != 0:
                # Target exists - check if dead
                if GLOBAL_CACHE.Agent.IsDead(target_id):
                    Player.CancelMove()
                    return True
                
                # Target alive - check distance
                target_pos = GLOBAL_CACHE.Agent.GetXY(target_id)
                my_pos = Player.GetXY()
                dist = Utils.Distance(my_pos, target_pos)
                
                if dist < attack_range:
                    # Close enough to fight
                    Player.CancelMove()
                    yield from self.kill_target(target_id)
                    continue
                elif dist < engage_range:
                    # Move toward target, abandoning path
                    Player.Move(target_pos[0], target_pos[1])
                    yield
                    continue
            
            # No target in engage range - follow path
            if path_index < len(path):
                target_pos = path[path_index]
                my_pos = Player.GetXY()
                
                if Utils.Distance(my_pos, target_pos) < Range.WAYPOINT_ARRIVAL:
                    path_index += 1
                else:
                    Player.Move(target_pos[0], target_pos[1])
            else:
                # Path complete
                if target_id != 0:
                    # Target exists but we're at end of path - keep moving to it
                    target_pos = GLOBAL_CACHE.Agent.GetXY(target_id)
                    Player.Move(target_pos[0], target_pos[1])
                else:
                    # No target found at end of path
                    return False
            
            # Clear enemies if enabled and in combat
            if clear_enemies and self.in_combat():
                Player.CancelMove()
                yield from self.kill_all(radius=self.aggro_range)
            
            yield
        
        return False

    def move_and_clear_path(self, path_coords: list, aggro_range: int = None):
        """
        Follows a path, stopping to kill enemies encountered along the way.
        
        This is the standard "move through area" method that handles
        combat automatically.
        
        Args:
            path_coords: List of (x, y) tuples defining the path
            aggro_range: Range to check for enemies (default: self.aggro_range)
            
        Yields for coroutine execution.
        """
        aggro = aggro_range or self.aggro_range
        
        for x, y in path_coords:
            # Safety: Abort if map loading
            if GLOBAL_CACHE.Map.IsMapLoading():
                return
            
            # Start moving to waypoint
            Player.Move(x, y)
            
            while True:
                # Safety check
                if GLOBAL_CACHE.Map.IsMapLoading():
                    return
                
                # Check arrival
                my_pos = Player.GetXY()
                if Utils.Distance(my_pos, (x, y)) < Range.WAYPOINT_ARRIVAL:
                    break
                
                # Check for enemies
                enemies = self._get_enemies_in_range(aggro)
                if enemies:
                    Player.CancelMove()
                    yield from self.kill_all(radius=aggro)
                    
                    # Safety check after combat
                    if GLOBAL_CACHE.Map.IsMapLoading():
                        return
                    
                    # Resume movement to same waypoint
                    Player.Move(x, y)
                
                yield

    # ==================
    # CORE COMBAT METHODS
    # ==================

    def kill_target(self, agent_id: int, timeout_ms: int = None):
        """
        Engages a specific target until it is dead.
        
        Args:
            agent_id: Agent ID of target to kill
            timeout_ms: Maximum time to spend fighting (default: Timing.COMBAT_TIMEOUT)
            
        Yields for coroutine execution.
        """
        timeout_ms = timeout_ms or Timing.COMBAT_TIMEOUT
        
        # Validate target
        if not GLOBAL_CACHE.Agent.IsValid(agent_id):
            return
        if GLOBAL_CACHE.Agent.IsDead(agent_id):
            return
        
        Player.ChangeTarget(agent_id)
        timeout = Timeout(timeout_ms)
        
        while not timeout.expired:
            # Check target state
            if not GLOBAL_CACHE.Agent.IsValid(agent_id):
                return
            if GLOBAL_CACHE.Agent.IsDead(agent_id):
                return
            if GLOBAL_CACHE.Map.IsMapLoading():
                return
            
            # Movement logic - close distance if needed
            my_pos = Player.GetXY()
            target_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
            dist = Utils.Distance(my_pos, target_pos)
            
            if dist > self.combat_range:
                Player.Move(target_pos[0], target_pos[1])
            
            # Combat logic
            yield from self.handler.ProcessSkillCasting()
            yield

    def kill_all(self, radius: int = None, timeout_ms: int = None):
        """
        Kills all enemies within radius.
        
        Args:
            radius: Search radius for enemies (default: Range.ENEMY_SEARCH)
            timeout_ms: Maximum time to spend clearing (default: Timing.KILL_ALL_TIMEOUT)
            
        Yields for coroutine execution.
        """
        radius = radius or Range.ENEMY_SEARCH
        timeout_ms = timeout_ms or Timing.KILL_ALL_TIMEOUT
        
        timeout = Timeout(timeout_ms)
        
        while not timeout.expired:
            # Safety check
            if GLOBAL_CACHE.Map.IsMapLoading():
                return
            
            # Find nearest enemy
            enemies = self._get_enemies_in_range(radius)
            
            if not enemies:
                return  # Area clear
            
            target_id = enemies[0]
            yield from self.kill_target(target_id)
            yield  # Prevent tight loop

    # ==================
    # UTILITY METHODS
    # ==================

    def in_combat(self) -> bool:
        """
        Check if currently in combat (enemies nearby).
        
        Returns:
            True if there are living enemies within earshot
        """
        enemies = self._get_enemies_in_range(Range.EARSHOT)
        return len(enemies) > 0

    def get_nearest_enemy(self, radius: int = None) -> int:
        """
        Gets the nearest enemy agent ID.
        
        Args:
            radius: Search radius (default: Range.ENEMY_SEARCH)
            
        Returns:
            Agent ID of nearest enemy, or 0 if none found
        """
        radius = radius or Range.ENEMY_SEARCH
        enemies = self._get_enemies_in_range(radius)
        return enemies[0] if enemies else 0

    def count_enemies(self, radius: int = None) -> int:
        """
        Count enemies in radius.
        
        Args:
            radius: Search radius (default: Range.ENEMY_SEARCH)
            
        Returns:
            Number of living enemies in range
        """
        radius = radius or Range.ENEMY_SEARCH
        return len(self._get_enemies_in_range(radius))

    def set_combat_range(self, distance: int):
        """Set the default combat engagement range."""
        self.combat_range = distance

    def set_aggro_range(self, distance: int):
        """Set the default aggro/detection range."""
        self.aggro_range = distance

    # ==================
    # PRIVATE HELPERS
    # ==================

    def _get_enemies_in_range(self, radius: int) -> list:
        """
        Gets sorted list of enemy agent IDs within radius.
        
        Args:
            radius: Search radius
            
        Returns:
            List of agent IDs sorted by distance (nearest first)
        """
        try:
            enemies = AgentArray.GetEnemyArray()
            enemies = AgentArray.Filter.ByDistance(enemies, Player.GetXY(), radius)
            enemies = AgentArray.Filter.ByAttribute(enemies, 'IsAlive')
            enemies.sort(
                key=lambda id: Utils.Distance(Player.GetXY(), GLOBAL_CACHE.Agent.GetXY(id))
            )
            return enemies
        except:
            return []

    # ==================
    # LEGACY ALIASES
    # ==================
    
    def KillTarget(self, agent_id: int):
        """Legacy method name."""
        yield from self.kill_target(agent_id)
    
    def KillAll(self, radius: int = 2500):
        """Legacy method name."""
        yield from self.kill_all(radius)