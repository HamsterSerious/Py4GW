"""
AgentUtils.py - Agent finding utilities for ZeroToHero missions.

Provides:
- NPC finding by position or name
- Gadget finding by position
- Enemy detection utilities
"""

from Py4GWCoreLib import *


class AgentFinder:
    """
    Utility class for finding NPCs, Gadgets, and other agents in the world.
    """
    
    @staticmethod
    def FindNearestNPC(x, y, max_distance=300, name_filter=None):
        """
        Find the nearest NPC at given coordinates.
        
        Args:
            x (float): X coordinate to search near
            y (float): Y coordinate to search near
            max_distance (float): Maximum search radius
            name_filter (str, optional): Only return NPCs with this name
            
        Returns:
            int: Agent ID of nearest NPC, or 0 if not found
        """
        scan_pos = (x, y)
        
        try:
            all_agents = AgentArray.GetAgentArray()
        except Exception:
            return 0
        
        npcs = []
        for agent_id in all_agents:
            try:
                if not Agent.IsValid(agent_id):
                    continue
                if not Agent.IsLiving(agent_id):
                    continue
                if Agent.GetLoginNumber(agent_id) != 0:
                    continue  # Player, not NPC
                
                # Optional name filter
                if name_filter:
                    agent_name = Agent.GetName(agent_id)
                    if name_filter.lower() not in agent_name.lower():
                        continue
                
                agent_pos = Agent.GetXY(agent_id)
                dist = Utils.Distance(scan_pos, agent_pos)
                
                if dist <= max_distance:
                    npcs.append((agent_id, dist))
            except Exception:
                continue
        
        if npcs:
            npcs.sort(key=lambda x: x[1])
            return npcs[0][0]
        
        return 0
    
    @staticmethod
    def FindNearestGadget(x, y, max_distance=300):
        """
        Find the nearest gadget at given coordinates.
        
        Args:
            x (float): X coordinate to search near
            y (float): Y coordinate to search near
            max_distance (float): Maximum search radius
            
        Returns:
            int: Agent ID of nearest gadget, or 0 if not found
        """
        scan_pos = (x, y)
        
        try:
            gadget_array = AgentArray.GetGadgetArray()
            gadget_array = AgentArray.Filter.ByDistance(gadget_array, scan_pos, max_distance)
            gadget_array = AgentArray.Sort.ByDistance(gadget_array, scan_pos)
            return gadget_array[0] if gadget_array else 0
        except Exception:
            return 0
    
    @staticmethod
    def FindNearestEnemy(max_distance=1200):
        """
        Find the nearest alive enemy to the player.
        
        Args:
            max_distance (float): Maximum search radius (default: Earshot)
            
        Returns:
            int: Agent ID of nearest enemy, or 0 if not found
        """
        try:
            player_pos = Player.GetXY()
            enemies = AgentArray.GetEnemyArray()
            enemies = AgentArray.Filter.ByDistance(enemies, player_pos, max_distance)
            enemies = AgentArray.Filter.ByCondition(enemies, lambda id: Agent.IsAlive(id))
            enemies = AgentArray.Sort.ByDistance(enemies, player_pos)
            return enemies[0] if enemies else 0
        except Exception:
            return 0
    
    @staticmethod
    def GetNearbyEnemies(max_distance=1200):
        """
        Get list of all alive enemies within range.
        
        Args:
            max_distance (float): Maximum search radius (default: Earshot)
            
        Returns:
            list: List of enemy Agent IDs
        """
        try:
            player_pos = Player.GetXY()
            enemies = AgentArray.GetEnemyArray()
            enemies = AgentArray.Filter.ByDistance(enemies, player_pos, max_distance)
            enemies = AgentArray.Filter.ByCondition(enemies, lambda id: Agent.IsAlive(id))
            return enemies
        except Exception:
            return []
    
    @staticmethod
    def FindNearestAlly(max_distance=1200, include_player=False):
        """
        Find the nearest alive ally.
        
        Args:
            max_distance (float): Maximum search radius
            include_player (bool): Include player in search
            
        Returns:
            int: Agent ID of nearest ally, or 0 if not found
        """
        try:
            player_id = Player.GetAgentID()
            player_pos = Player.GetXY()
            allies = AgentArray.GetAllyArray()
            allies = AgentArray.Filter.ByDistance(allies, player_pos, max_distance)
            allies = AgentArray.Filter.ByCondition(allies, lambda id: Agent.IsAlive(id))
            
            if not include_player:
                allies = [a for a in allies if a != player_id]
            
            allies = AgentArray.Sort.ByDistance(allies, player_pos)
            return allies[0] if allies else 0
        except Exception:
            return 0
    
    @staticmethod
    def FindAgentByName(name, max_distance=5000):
        """
        Find an agent by name within range.
        
        Args:
            name (str): Name (or partial name) to search for
            max_distance (float): Maximum search radius
            
        Returns:
            int: Agent ID if found, 0 otherwise
        """
        try:
            player_pos = Player.GetXY()
            all_agents = AgentArray.GetAgentArray()
            all_agents = AgentArray.Filter.ByDistance(all_agents, player_pos, max_distance)
            
            for agent_id in all_agents:
                try:
                    if not Agent.IsValid(agent_id):
                        continue
                    agent_name = Agent.GetName(agent_id)
                    if name.lower() in agent_name.lower():
                        return agent_id
                except Exception:
                    continue
            
            return 0
        except Exception:
            return 0
    
    @staticmethod
    def GetDistanceToAgent(agent_id):
        """
        Get distance from player to an agent.
        
        Args:
            agent_id (int): Agent ID
            
        Returns:
            float: Distance, or -1 if invalid
        """
        try:
            if not Agent.IsValid(agent_id):
                return -1
            player_pos = Player.GetXY()
            agent_pos = Agent.GetXY(agent_id)
            return Utils.Distance(player_pos, agent_pos)
        except Exception:
            return -1
    
    @staticmethod
    def IsAgentInRange(agent_id, max_range):
        """
        Check if an agent is within range.
        
        Args:
            agent_id (int): Agent ID
            max_range (float): Maximum range
            
        Returns:
            bool: True if in range
        """
        dist = AgentFinder.GetDistanceToAgent(agent_id)
        return 0 <= dist <= max_range


class AgentPosition:
    """
    Helper class for storing and working with agent positions.
    """
    def __init__(self, x, y, name=None):
        self.x = x
        self.y = y
        self.name = name
    
    def AsTuple(self):
        return (self.x, self.y)
    
    def DistanceFrom(self, other_pos):
        """Get distance from another position tuple."""
        return Utils.Distance((self.x, self.y), other_pos)
    
    def DistanceFromPlayer(self):
        """Get distance from player."""
        return Utils.Distance((self.x, self.y), Player.GetXY())
