from Py4GWCoreLib import *
from Py4GWCoreLib.Builds.AutoCombat import AutoCombat

class Combat:
    def __init__(self):
        # We use the built-in generic AutoCombat handler
        self.handler = AutoCombat()
        self.combat_range = 900 

    def KillTarget(self, agent_id):
        """
        Engages a specific target until it is dead.
        """
        if not Agent.IsValid(agent_id) or Agent.IsDead(agent_id):
            return

        # Target the enemy
        Player.ChangeTarget(agent_id)
        
        while Agent.IsValid(agent_id) and not Agent.IsDead(agent_id):
            # 1. Movement Logic
            my_x, my_y = Player.GetXY()
            target_x, target_y = Agent.GetXY(agent_id)
            dist = Utils.Distance((my_x, my_y), (target_x, target_y))

            if dist > self.combat_range:
                Player.Move(target_x, target_y)
            else:
                if Agent.IsMoving(Player.GetAgentID()):
                    # Optional: Stop to cast if needed
                    pass

            # 2. Combat Logic
            yield from self.handler.ProcessSkillCasting()
            
            yield # Frame wait

    def KillAll(self, radius=2500):
        """
        Finds all enemies within radius and kills them one by one.
        """
        while True:
            yield # Prevent infinite loop freeze
            
            # 1. Find nearest enemy
            enemy_array = AgentArray.GetEnemyArray()
            
            # Filter by Distance
            enemy_array = AgentArray.Filter.ByDistance(enemy_array, Player.GetXY(), radius)
            
            # FIXED: Changed 'IsLiving' (which includes corpses) to 'IsAlive' (Health > 0)
            enemy_array = AgentArray.Filter.ByAttribute(enemy_array, 'IsAlive')
            
            # Sort by distance
            enemy_array.sort(key=lambda id: Utils.Distance(Player.GetXY(), Agent.GetXY(id)))

            if not enemy_array:
                break # No more enemies

            target_id = enemy_array[0]
            
            # 2. Kill it
            yield from self.KillTarget(target_id)