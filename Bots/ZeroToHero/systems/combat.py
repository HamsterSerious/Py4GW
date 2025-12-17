"""
Combat System - Handles combat and skill usage.
"""
from Py4GWCoreLib import Agent, Player, AgentArray, Utils
from Py4GWCoreLib.Builds.AutoCombat import AutoCombat

from data.timing import Timing, Range


class Combat:
    """
    Handles combat encounters and skill usage.
    
    Uses Py4GWCoreLib's AutoCombat for skill rotation.
    """
    
    def __init__(self):
        self.handler = AutoCombat()
        self.combat_range = Range.COMBAT_DEFAULT
    
    def kill_target(self, agent_id: int):
        """
        Engages a specific target until it is dead.
        
        Args:
            agent_id: Agent ID of the target
            
        Yields for coroutine execution.
        """
        if not Agent.IsValid(agent_id) or Agent.IsDead(agent_id):
            return
        
        Player.ChangeTarget(agent_id)
        
        while Agent.IsValid(agent_id) and not Agent.IsDead(agent_id):
            # Movement logic - close distance if needed
            my_x, my_y = Player.GetXY()
            target_x, target_y = Agent.GetXY(agent_id)
            dist = Utils.Distance((my_x, my_y), (target_x, target_y))
            
            if dist > self.combat_range:
                Player.Move(target_x, target_y)
            
            # Combat logic
            yield from self.handler.ProcessSkillCasting()
            yield
    
    def kill_all(self, radius: int = 2500):
        """
        Finds all enemies within radius and kills them one by one.
        
        Args:
            radius: Search radius for enemies
            
        Yields for coroutine execution.
        """
        while True:
            yield  # Prevent infinite loop freeze
            
            # Find nearest enemy
            enemy_array = AgentArray.GetEnemyArray()
            enemy_array = AgentArray.Filter.ByDistance(enemy_array, Player.GetXY(), radius)
            enemy_array = AgentArray.Filter.ByAttribute(enemy_array, 'IsAlive')
            enemy_array.sort(key=lambda id: Utils.Distance(Player.GetXY(), Agent.GetXY(id)))
            
            if not enemy_array:
                break  # No more enemies
            
            target_id = enemy_array[0]
            yield from self.kill_target(target_id)
    
    def in_combat(self) -> bool:
        """
        Check if currently in combat.
        
        Returns:
            True if enemies are nearby and aggressive
        """
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
        """
        Set the engagement range.
        
        Args:
            distance: Range in game units
        """
        self.combat_range = distance
    
    # ==================
    # LEGACY ALIASES
    # ==================
    
    def KillTarget(self, agent_id: int):
        """Legacy method name - use kill_target() instead."""
        yield from self.kill_target(agent_id)
    
    def KillAll(self, radius: int = 2500):
        """Legacy method name - use kill_all() instead."""
        yield from self.kill_all(radius)
