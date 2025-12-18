"""
Combat System - Handles combat encounters and skill usage.

Provides:
- Target killing (single and multiple)
- Path following with combat
- Boss/target hunting along paths
- Enemy-specific target finding (ignores allies with same ModelID)
"""
import time
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
        self.ignore_models = []  # Model IDs to ignore during combat

    # ==================
    # TARGET FINDING
    # ==================

    def find_enemy_by_model_id(self, model_id: int, max_range: int = None) -> int:
        """
        Find an enemy agent by ModelID.
        
        Unlike Routines.Agents.GetAgentIDByModelID which finds ANY agent,
        this only searches the enemy array. Essential when allies and enemies
        share the same ModelID (e.g., Gatah and Darehk in Jokanur).
        
        Args:
            model_id: The ModelID (PlayerNumber) to search for
            max_range: Optional max distance (default: no limit)
            
        Returns:
            Agent ID of the enemy, or 0 if not found
        """
        try:
            enemies = GLOBAL_CACHE.AgentArray.GetEnemyArray()
            my_pos = Player.GetXY()
            
            for agent_id in enemies:
                if GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id) == model_id:
                    if GLOBAL_CACHE.Agent.IsDead(agent_id):
                        continue
                    
                    if max_range:
                        agent_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
                        if Utils.Distance(my_pos, agent_pos) > max_range:
                            continue
                    
                    return agent_id
            return 0
        except:
            return 0

    def find_enemy_by_model_id_include_dead(self, model_id: int) -> int:
        """
        Find an enemy agent by ModelID, including dead enemies.
        
        Used to verify kills when the enemy might still be in the array but dead.
        
        Args:
            model_id: The ModelID (PlayerNumber) to search for
            
        Returns:
            Agent ID of the enemy (alive or dead), or 0 if not found
        """
        try:
            enemies = GLOBAL_CACHE.AgentArray.GetEnemyArray()
            
            for agent_id in enemies:
                if GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id) == model_id:
                    return agent_id
            return 0
        except:
            return 0

    def find_nearest_enemy(self, model_id: int = None) -> int:
        """
        Find the nearest enemy, optionally filtered by ModelID.
        
        Args:
            model_id: Optional ModelID filter (None = any enemy)
            
        Returns:
            Agent ID of nearest matching enemy, or 0 if none found
        """
        try:
            enemies = GLOBAL_CACHE.AgentArray.GetEnemyArray()
            my_pos = Player.GetXY()
            
            candidates = []
            for agent_id in enemies:
                if GLOBAL_CACHE.Agent.IsDead(agent_id):
                    continue
                
                if model_id and GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id) != model_id:
                    continue
                
                agent_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
                dist = Utils.Distance(my_pos, agent_pos)
                candidates.append((dist, agent_id))
            
            if not candidates:
                return 0
            
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
        except:
            return 0

    def is_enemy_dead(self, model_id: int) -> bool:
        """
        Check if a specific enemy (by ModelID) is dead.
        
        Searches only the enemy array to avoid false positives
        from allies with the same ModelID.
        
        Args:
            model_id: The ModelID to check
            
        Returns:
            True if enemy with that ModelID is dead (or not in array anymore)
        """
        try:
            enemies = GLOBAL_CACHE.AgentArray.GetEnemyArray()
            
            for agent_id in enemies:
                if GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id) == model_id:
                    return GLOBAL_CACHE.Agent.IsDead(agent_id)
            
            # Enemy not found in array - they were killed and removed
            return True
        except:
            return True

    # ==================
    # IGNORE LIST MANAGEMENT
    # ==================

    def add_to_ignore_list(self, model_id: int):
        """Add a ModelID to the combat ignore list."""
        if model_id not in self.ignore_models:
            self.ignore_models.append(model_id)

    def remove_from_ignore_list(self, model_id: int):
        """Remove a ModelID from the combat ignore list."""
        if model_id in self.ignore_models:
            self.ignore_models.remove(model_id)

    def clear_ignore_list(self):
        """Clear all entries from the combat ignore list."""
        self.ignore_models.clear()

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
        Follows a path while hunting for a specific enemy target (e.g., boss).
        
        When target is found:
        - Within engage_range: Abandon path and move toward target
        - Within attack_range: Stop and fight
        
        This method searches ONLY the enemy array, so it correctly handles
        cases where allies and enemies share the same ModelID.
        
        Args:
            path: List of (x, y) waypoints to follow
            target_model_id: Model ID of enemy target to hunt
            engage_range: Range at which to stop pathing and engage (default: Range.TARGET_ENGAGE)
            attack_range: Range at which to start attacking (default: Range.TARGET_ATTACK)
            clear_enemies: Whether to kill enemies encountered on path
            
        Yields for coroutine execution.
        Returns True if target was killed, False if path ended without finding target.
        """
        engage_range = engage_range or Range.TARGET_ENGAGE
        attack_range = attack_range or Range.TARGET_ATTACK
        
        path_index = 0
        target_was_engaged = False  # Track if we ever found and engaged the target
        
        while True:
            # Safety: Abort if map loading
            if GLOBAL_CACHE.Map.IsMapLoading():
                return False
            
            # Check for target - use enemy-specific finder
            target_id = self.find_enemy_by_model_id(target_model_id)
            
            if target_id != 0:
                target_was_engaged = True  # We found the target at least once
                
                # Target exists and alive - check distance
                target_pos = GLOBAL_CACHE.Agent.GetXY(target_id)
                my_pos = Player.GetXY()
                dist = Utils.Distance(my_pos, target_pos)
                
                if dist < attack_range:
                    # Close enough to fight
                    Player.CancelMove()
                    yield from self.kill_target(target_id)
                    
                    # CRITICAL: After kill_target returns, check if enemy is dead
                    # This catches the case where kill_target succeeded but the
                    # enemy was removed from the array before we could check
                    if self.is_enemy_dead(target_model_id):
                        return True
                    
                    # Target somehow still alive, continue loop
                    continue
                elif dist < engage_range:
                    # Move toward target, abandoning path
                    Player.Move(target_pos[0], target_pos[1])
                    yield
                    continue
            else:
                # No living enemy found with this ModelID
                # Check if we previously engaged and they're now dead
                if target_was_engaged and self.is_enemy_dead(target_model_id):
                    Player.CancelMove()
                    return True
            
            # No target in engage range - follow path
            if path_index < len(path):
                target_pos = path[path_index]
                my_pos = Player.GetXY()
                
                if Utils.Distance(my_pos, target_pos) < Range.WAYPOINT_ARRIVAL:
                    path_index += 1
                else:
                    Player.Move(target_pos[0], target_pos[1])
            else:
                # Path complete - final check
                if self.is_enemy_dead(target_model_id):
                    return True
                
                # Check if there's still a living target somewhere
                target_id = self.find_enemy_by_model_id(target_model_id)
                if target_id != 0:
                    # Target exists but we're at end of path - keep moving to it
                    target_pos = GLOBAL_CACHE.Agent.GetXY(target_id)
                    Player.Move(target_pos[0], target_pos[1])
                else:
                    # No target found at end of path and never engaged
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
        combat automatically. Respects the ignore_models list.
        
        Includes stuck detection - if not making progress, re-issues move command.
        
        Args:
            path_coords: List of (x, y) tuples defining the path
            aggro_range: Range to check for enemies (default: self.aggro_range)
            
        Yields for coroutine execution.
        """
        aggro = aggro_range or self.aggro_range
        stuck_timeout = 3.0  # Seconds without progress = stuck
        
        for x, y in path_coords:
            # Safety: Abort if map loading
            if GLOBAL_CACHE.Map.IsMapLoading():
                return
            
            target = (x, y)
            last_progress_time = time.time()
            best_distance = Utils.Distance(Player.GetXY(), target)
            
            # Start moving to waypoint
            Player.Move(x, y)
            
            while True:
                # Safety check
                if GLOBAL_CACHE.Map.IsMapLoading():
                    return
                
                my_pos = Player.GetXY()
                current_distance = Utils.Distance(my_pos, target)
                
                # Check arrival
                if current_distance < Range.WAYPOINT_ARRIVAL:
                    break
                
                # Track progress
                if current_distance < best_distance - 10:
                    best_distance = current_distance
                    last_progress_time = time.time()
                
                # Check if stuck (no progress for stuck_timeout seconds)
                time_stuck = time.time() - last_progress_time
                if time_stuck > stuck_timeout:
                    # Re-issue move command to get unstuck
                    Player.Move(x, y)
                    last_progress_time = time.time()  # Reset timer but keep best_distance
                
                # Check for enemies (respecting ignore list)
                enemies = self._get_enemies_in_range(aggro)
                if enemies:
                    Player.CancelMove()
                    yield from self.kill_all(radius=aggro)
                    
                    # Safety check after combat
                    if GLOBAL_CACHE.Map.IsMapLoading():
                        return
                    
                    # Reset progress tracking after combat
                    best_distance = Utils.Distance(Player.GetXY(), target)
                    last_progress_time = time.time()
                    
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
        
        Respects the ignore_models list - enemies with ignored ModelIDs
        will not be targeted.
        
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
            
            # Find nearest enemy (respecting ignore list)
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
        
        Respects the ignore_models list.
        
        Returns:
            True if there are living enemies within earshot
        """
        enemies = self._get_enemies_in_range(Range.EARSHOT)
        return len(enemies) > 0

    def get_nearest_enemy(self, radius: int = None) -> int:
        """
        Gets the nearest enemy agent ID.
        
        Respects the ignore_models list.
        
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
        
        Respects the ignore_models list.
        
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
        
        Filters out:
        - Dead enemies
        - Enemies in ignore_models list
        
        Args:
            radius: Search radius
            
        Returns:
            List of agent IDs sorted by distance (nearest first)
        """
        try:
            enemies = AgentArray.GetEnemyArray()
            enemies = AgentArray.Filter.ByDistance(enemies, Player.GetXY(), radius)
            enemies = AgentArray.Filter.ByAttribute(enemies, 'IsAlive')
            
            # Filter out ignored models
            if self.ignore_models:
                filtered = []
                for agent_id in enemies:
                    model_id = GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id)
                    if model_id not in self.ignore_models:
                        filtered.append(agent_id)
                enemies = filtered
            
            # Sort by distance
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