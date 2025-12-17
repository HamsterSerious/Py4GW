"""
Combat System - Handles combat and skill usage.
"""
from Py4GWCoreLib import Agent, Player, AgentArray, Utils
from Py4GWCoreLib.Builds.AutoCombat import AutoCombat
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib import Routines

from data.timing import Timing, Range

class Combat:
    """
    Handles combat encounters and skill usage.
    """
    
    def __init__(self):
        self.handler = AutoCombat()
        self.combat_range = Range.COMBAT_DEFAULT
        self.aggro_range = 1500  # Range to check for enemies while moving
    
    def kill_target(self, agent_id: int):
        """
        Engages a specific target until it is dead.
        Aborts if map starts loading.
        """
        if not GLOBAL_CACHE.Agent.IsValid(agent_id) or GLOBAL_CACHE.Agent.IsDead(agent_id):
            return
        
        Player.ChangeTarget(agent_id)
        
        while GLOBAL_CACHE.Agent.IsValid(agent_id) and not GLOBAL_CACHE.Agent.IsDead(agent_id):
            # Safety Check: Abort if map changes/loads
            if GLOBAL_CACHE.Map.IsMapLoading(): #
                return

            # Movement logic - close distance if needed
            my_x, my_y = Player.GetXY()
            target_x, target_y = GLOBAL_CACHE.Agent.GetXY(agent_id)
            dist = Utils.Distance((my_x, my_y), (target_x, target_y))
            
            if dist > self.combat_range:
                Player.Move(target_x, target_y)
            
            # Combat logic
            yield from self.handler.ProcessSkillCasting()
            yield
    
    def kill_all(self, radius: int = 2500):
        """
        Finds all enemies within radius and kills them one by one.
        Aborts if map starts loading.
        """
        while True:
            # Safety Check: Abort if map changes/loads
            if GLOBAL_CACHE.Map.IsMapLoading(): #
                return
                
            yield  # Prevent infinite loop freeze
            
            # Find nearest enemy
            enemy_array = AgentArray.GetEnemyArray()
            enemy_array = AgentArray.Filter.ByDistance(enemy_array, Player.GetXY(), radius)
            enemy_array = AgentArray.Filter.ByAttribute(enemy_array, 'IsAlive')
            
            # Sort by distance
            enemy_array.sort(key=lambda id: Utils.Distance(Player.GetXY(), GLOBAL_CACHE.Agent.GetXY(id)))
            
            if not enemy_array:
                break  # No more enemies
            
            target_id = enemy_array[0]
            yield from self.kill_target(target_id)
            
    def move_and_clear_path(self, path_coords: list):
        """
        Follows a path, but stops to kill any enemies encountered along the way.
        Aborts immediately if the map starts loading.
        
        Args:
            path_coords: List of (x, y) tuples
        """
        for x, y in path_coords:
            # Safety Check: Abort if map changes/loads
            if GLOBAL_CACHE.Map.IsMapLoading(): #
                return
                
            # Move to the next waypoint
            Player.Move(x, y)
            
            while True:
                # Safety Check: Abort if map changes/loads inside the loop
                if GLOBAL_CACHE.Map.IsMapLoading():
                    return

                # 1. Check if we arrived at this waypoint
                my_x, my_y = Player.GetXY()
                dist_to_wp = Utils.Distance((my_x, my_y), (x, y))
                
                if dist_to_wp < 150: # Arrived at waypoint
                    break
                
                # 2. Check for enemies to kill
                enemy_array = AgentArray.GetEnemyArray()
                enemy_array = AgentArray.Filter.ByDistance(enemy_array, (my_x, my_y), self.aggro_range)
                enemy_array = AgentArray.Filter.ByAttribute(enemy_array, 'IsAlive')
                
                if enemy_array:
                    # Enemy detected! Stop and Kill.
                    Player.CancelMove()
                    yield from self.kill_all(radius=self.aggro_range)
                    
                    # After combat, check again if we should abort
                    if GLOBAL_CACHE.Map.IsMapLoading():
                        return
                        
                    # Resume movement to the SAME waypoint after combat
                    Player.Move(x, y)
                
                # 3. Update Combat/Movement state
                yield # Frame yield
    
    def in_combat(self) -> bool:
        """Check if currently in combat."""
        try:
            enemy_array = AgentArray.GetEnemyArray()
            enemy_array = AgentArray.Filter.ByDistance(
                enemy_array, 
                Player.GetXY(), 
                Range.EARSHOT
            )
            enemy_array = AgentArray.Filter.ByAttribute(enemy_array, 'IsAlive')
            return len(enemy_array) > 0
        except:
            return False
    
    def set_combat_range(self, distance: int):
        self.combat_range = distance
    
    # ==================
    # LEGACY ALIASES
    # ==================
    
    def KillTarget(self, agent_id: int):
        yield from self.kill_target(agent_id)
    
    def KillAll(self, radius: int = 2500):
        yield from self.kill_all(radius)