"""
Interaction System - Handles world interactions.

Provides:
- NPC interaction
- Gadget finding and interaction
- Environmental bundle pickup and use (e.g., oil + catapult)
"""
import time
from Py4GWCoreLib import Player, Utils, Routines
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from data.timing import Timing, Range
from utils.timer import Timeout


class Interaction:
    """
    Handles world interactions: gadgets, bundles, NPCs.
    
    Key methods for missions:
    - pickup_bundle(): Pick up an environmental item (oil, torch, etc.)
    - use_bundle_on_gadget(): Use held item on a gadget (catapult, etc.)
    - pickup_and_use_bundle(): Complete pickup-and-use sequence
    - move_to_and_interact(): Approach and interact with any agent
    """
    
    def __init__(self, bot):
        self.bot = bot

    # ==================
    # BUNDLE/GADGET MECHANICS
    # ==================

    def pickup_bundle(self, gadget_model_id: int, timeout_ms: int = None):
        """
        Picks up an environmental bundle/item (oil flask, torch, etc.).
        
        These are gadgets in the world that the player can pick up and carry.
        
        Args:
            gadget_model_id: Model ID of the gadget to pick up
            timeout_ms: Time to wait for gadget to appear (default: Timing.GADGET_SEARCH_TIMEOUT)
            
        Yields for coroutine execution.
        Returns True if bundle was picked up successfully.
        """
        timeout_ms = timeout_ms or Timing.GADGET_SEARCH_TIMEOUT
        
        # Find the gadget
        timeout = Timeout(timeout_ms)
        gadget_id = 0
        
        while not timeout.expired and gadget_id == 0:
            gadget_id = self.find_gadget_by_id(gadget_model_id)
            if gadget_id == 0:
                yield
        
        if gadget_id == 0:
            return False
        
        # Interact to pick up
        yield from self.move_to_and_interact(gadget_id)
        yield from Routines.Yield.wait(Timing.GADGET_PICKUP_DELAY)
        
        # Verify pickup
        if not self.is_holding_bundle():
            # Retry once
            yield from self.move_to_and_interact(gadget_id)
            yield from Routines.Yield.wait(Timing.GADGET_PICKUP_DELAY)
        
        return self.is_holding_bundle()

    def use_bundle_on_gadget(self, gadget_model_id: int, timeout_ms: int = None):
        """
        Uses held bundle on a gadget (e.g., oil on catapult).
        
        Must be holding a bundle before calling this.
        
        Args:
            gadget_model_id: Model ID of the target gadget
            timeout_ms: Time to wait for gadget (default: Timing.GADGET_SEARCH_TIMEOUT)
            
        Yields for coroutine execution.
        Returns True if interaction completed.
        """
        timeout_ms = timeout_ms or Timing.GADGET_SEARCH_TIMEOUT
        
        # Find the gadget
        timeout = Timeout(timeout_ms)
        gadget_id = 0
        
        while not timeout.expired and gadget_id == 0:
            gadget_id = self.find_gadget_by_id(gadget_model_id)
            if gadget_id == 0:
                yield
        
        if gadget_id == 0:
            return False
        
        yield from self.move_to_and_interact(gadget_id)
        yield from Routines.Yield.wait(Timing.GADGET_USE_DELAY)
        return True

    def pickup_and_use_bundle(
        self,
        bundle_model_id: int,
        bundle_position: tuple,
        target_model_id: int,
        target_position: tuple,
        post_use_delay_ms: int = None
    ):
        """
        Complete pickup-and-use sequence for environmental bundles.
        
        Example: Pick up oil → carry to catapult → load catapult
        
        This method handles:
        1. Moving to bundle location (with combat)
        2. Picking up the bundle
        3. Moving to target location (with combat)
        4. Using bundle on target
        
        Args:
            bundle_model_id: Model ID of bundle gadget to pick up
            bundle_position: (x, y) position of bundle
            target_model_id: Model ID of target gadget
            target_position: (x, y) position of target
            post_use_delay_ms: Delay after using bundle (default: Timing.GADGET_USE_DELAY)
            
        Yields for coroutine execution.
        Returns True if sequence completed successfully.
        """
        post_use_delay_ms = post_use_delay_ms or Timing.GADGET_USE_DELAY
        
        # Move to and pickup bundle
        yield from self.bot.combat.move_and_clear_path([bundle_position])
        
        if not (yield from self.pickup_bundle(bundle_model_id)):
            return False
        
        # Move to and use on target
        yield from self.bot.combat.move_and_clear_path([target_position])
        
        if not (yield from self.use_bundle_on_gadget(target_model_id)):
            return False
        
        yield from Routines.Yield.wait(post_use_delay_ms)
        return True

    def interact_with_gadget(self, gadget_model_id: int, timeout_ms: int = None):
        """
        Simple gadget interaction (no bundle involved).
        
        Use this for levers, buttons, etc.
        
        Args:
            gadget_model_id: Model ID of gadget
            timeout_ms: Time to wait for gadget
            
        Yields for coroutine execution.
        Returns True if interaction completed.
        """
        timeout_ms = timeout_ms or Timing.GADGET_SEARCH_TIMEOUT
        
        gadget_id = 0
        timeout = Timeout(timeout_ms)
        
        while not timeout.expired and gadget_id == 0:
            gadget_id = self.find_gadget_by_id(gadget_model_id)
            if gadget_id == 0:
                yield
        
        if gadget_id == 0:
            return False
        
        yield from self.move_to_and_interact(gadget_id)
        return True

    # ==================
    # CORE INTERACTION
    # ==================

    def move_to_and_interact(self, agent_id: int, x: float = 0, y: float = 0):
        """
        Moves to an agent and interacts using native game pathfinding.
        
        Uses the game's Interact command which handles the final approach
        smoothly without stuttering.
        
        Args:
            agent_id: Agent ID to interact with
            x: Hint X position if agent not initially visible
            y: Hint Y position if agent not initially visible
            
        Yields for coroutine execution.
        """
        # Resolve target (move to expected location if not visible)
        if not GLOBAL_CACHE.Agent.IsValid(agent_id):
            if x != 0 and y != 0:
                yield from self.bot.movement.move_to(x, y)
                yield from Routines.Yield.wait(Timing.MEDIUM_DELAY)
            
            if not GLOBAL_CACHE.Agent.IsValid(agent_id):
                return  # Target still not found

        # Smooth approach - move close before issuing interact
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

        # Issue interact command (game handles final approach)
        Player.Interact(agent_id, True)
        
        # Monitor completion
        timeout = Timeout(10000)
        last_pos = Player.GetXY()
        last_move_time = time.time()
        
        while not timeout.expired:
            if not GLOBAL_CACHE.Agent.IsValid(agent_id):
                break
            
            agent_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
            my_pos = Player.GetXY()
            dist = Utils.Distance(my_pos, agent_pos)
            
            # Success: Extremely close
            if dist < Range.INTERACT_RANGE:
                break
            
            # Success: Stopped moving and reasonably close
            # (handles large objects where game stops you at ~250)
            if dist < 400:
                moved_dist = Utils.Distance(my_pos, last_pos)
                if moved_dist < 2.0:  # Effectively stopped
                    if time.time() - last_move_time > 0.2:
                        break
                else:
                    last_move_time = time.time()
            
            last_pos = my_pos
            yield
        
        # Small delay for server confirmation
        yield from Routines.Yield.wait(Timing.INTERACT_DELAY)

    # ==================
    # GADGET FINDING
    # ==================

    def find_gadget_by_id(self, gadget_id: int, max_dist: int = None) -> int:
        """
        Finds the nearest gadget with the specified GadgetID (ModelID).
        
        Args:
            gadget_id: The GadgetID to search for
            max_dist: Maximum search distance (default: Range.GADGET_SEARCH)
            
        Returns:
            Agent ID of nearest matching gadget, or 0 if not found
        """
        max_dist = max_dist or Range.GADGET_SEARCH
        
        agents = GLOBAL_CACHE.AgentArray.GetGadgetArray()
        candidates = []
        my_pos = Player.GetXY()
        
        for agent_id in agents:
            try:
                if GLOBAL_CACHE.Agent.GetGadgetID(agent_id) == gadget_id:
                    agent_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
                    dist = Utils.Distance(my_pos, agent_pos)
                    if dist <= max_dist:
                        candidates.append((dist, agent_id))
            except:
                continue
        
        if not candidates:
            return 0
        
        # Return nearest
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def find_all_gadgets_by_id(self, gadget_id: int, max_dist: int = None) -> list:
        """
        Finds all gadgets with the specified GadgetID.
        
        Args:
            gadget_id: The GadgetID to search for
            max_dist: Maximum search distance (default: Range.GADGET_SEARCH)
            
        Returns:
            List of (distance, agent_id) tuples sorted by distance
        """
        max_dist = max_dist or Range.GADGET_SEARCH
        
        agents = GLOBAL_CACHE.AgentArray.GetGadgetArray()
        candidates = []
        my_pos = Player.GetXY()
        
        for agent_id in agents:
            try:
                if GLOBAL_CACHE.Agent.GetGadgetID(agent_id) == gadget_id:
                    agent_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
                    dist = Utils.Distance(my_pos, agent_pos)
                    if dist <= max_dist:
                        candidates.append((dist, agent_id))
            except:
                continue
        
        candidates.sort(key=lambda x: x[0])
        return candidates

    # ==================
    # STATE CHECKS
    # ==================

    def is_holding_bundle(self) -> bool:
        """
        Checks if the player is currently holding an environmental bundle.
        
        Bundles are items like oil flasks, torches, etc. that replace
        your weapon temporarily.
        
        Returns:
            True if holding a bundle
        """
        try:
            my_id = Player.GetAgentID()
            weapon_type, _ = GLOBAL_CACHE.Agent.GetWeaponType(my_id)
            # Weapon type 10 = bundle, 0 = unarmed (also indicates bundle in some cases)
            return weapon_type == 10 or weapon_type == 0
        except:
            return False

    def drop_bundle(self):
        """
        Drops the currently held bundle.
        
        Yields for coroutine execution.
        """
        if self.is_holding_bundle():
            # Drop by clicking on ground or using drop command
            Player.DropBundle()
            yield from Routines.Yield.wait(Timing.SHORT_DELAY)

    # ==================
    # LEGACY ALIASES
    # ==================
    
    def is_holding_item(self) -> bool:
        """Legacy method name - use is_holding_bundle()."""
        return self.is_holding_bundle()