"""
Interaction System - Handles world interaction (Gadgets, Items, NPCs).
"""
import time
from Py4GWCoreLib import Player, Utils
from Py4GWCoreLib import Routines
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from data.timing import Timing

class Interaction:
    def __init__(self, bot):
        self.bot = bot

    def move_to_and_interact(self, agent_id: int, x: float = 0, y: float = 0):
        """
        Moves to an agent and interacts using native game pathfinding for smoothness.
        Eliminates the 'stop-and-go' stutter by issuing Interact early.
        """
        # 1. Resolve Target (Move to expected location if not visible)
        if not GLOBAL_CACHE.Agent.IsValid(agent_id):
            if x != 0 and y != 0:
                yield from self.bot.movement.move_to(x, y)
                yield from Routines.Yield.wait(500)
            
            if not GLOBAL_CACHE.Agent.IsValid(agent_id):
                return # Target still not found

        # 2. Smooth Approach Strategy
        SAFE_INTERACT_RANGE = 2000
        
        while True:
            if not GLOBAL_CACHE.Agent.IsValid(agent_id):
                return
                
            agent_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
            my_pos = Player.GetXY()
            dist = Utils.Distance(my_pos, agent_pos)
            
            # Switch to Interact command when close enough
            if dist <= SAFE_INTERACT_RANGE:
                break
                
            # Manual approach if far away
            Player.Move(agent_pos[0], agent_pos[1])
            yield

        # 3. Issue Interact Command
        # The game client handles the final approach
        Player.Interact(agent_id, True)
        
        # 4. Monitor Completion (The Fix)
        timeout = time.time() + 10
        last_pos = Player.GetXY()
        last_move_time = time.time()
        
        while time.time() < timeout:
            if not GLOBAL_CACHE.Agent.IsValid(agent_id):
                break
                
            agent_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
            my_pos = Player.GetXY()
            dist = Utils.Distance(my_pos, agent_pos)
            
            # Condition A: We are extremely close (Success)
            if dist < 200: 
                break
            
            # Condition B: We stopped moving and are reasonably close (Success)
            # This handles large objects where the game stops you at dist 250
            if dist < 400:
                moved_dist = Utils.Distance(my_pos, last_pos)
                if moved_dist < 2.0: # Effectively stopped
                    # Wait a tiny bit to ensure it's a real stop
                    if time.time() - last_move_time > 0.2:
                        break
                else:
                    last_move_time = time.time()
            
            last_pos = my_pos
            yield
        
        # Small delay for server confirmation
        yield from Routines.Yield.wait(Timing.INTERACT_DELAY)

    def find_gadget_by_id(self, gadget_id: int, max_dist: int = 5000) -> int:
        """Finds the nearest gadget with the specified GadgetID (ModelID)."""
        agents = GLOBAL_CACHE.AgentArray.GetGadgetArray()
        candidates = []
        my_x, my_y = Player.GetXY()
        
        for agent_id in agents:
            if GLOBAL_CACHE.Agent.GetGadgetID(agent_id) == gadget_id:
                ax, ay = GLOBAL_CACHE.Agent.GetXY(agent_id)
                dist = Utils.Distance((my_x, my_y), (ax, ay))
                if dist <= max_dist:
                    candidates.append((dist, agent_id))
        
        if not candidates:
            return 0
            
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def is_holding_item(self) -> bool:
        """Checks if the player is currently holding a bundle/item."""
        my_id = Player.GetAgentID()
        weapon_type, _ = GLOBAL_CACHE.Agent.GetWeaponType(my_id)
        return weapon_type == 10 or weapon_type == 0