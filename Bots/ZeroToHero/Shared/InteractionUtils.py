"""
InteractionUtils.py - Interaction utilities for ZeroToHero missions.

Provides:
- Bundle (environmental item) handling
- Gadget interaction state machines
- NPC interaction helpers
"""

from Py4GWCoreLib import *
from .AgentUtils import AgentFinder


class BundleHandler:
    """
    Handles picking up and using environmental items (bundles) like oil, torches, etc.
    """
    
    # Weapon types that indicate player is holding a bundle
    BUNDLE_TYPE_NAMES = ["Bundle", "Item", "Environmental", "Unknown", ""]
    
    @staticmethod
    def IsHoldingBundle():
        """
        Check if the player is currently holding a bundle item.
        
        Returns:
            bool: True if holding a bundle
        """
        try:
            agent_id = Player.GetAgentID()
            weapon_type_id, weapon_type_name = Agent.GetWeaponType(agent_id)
            
            # Bundle detection
            if weapon_type_name in BundleHandler.BUNDLE_TYPE_NAMES:
                return True
            if weapon_type_id == 0:
                return True
            
            return False
        except Exception:
            return False
    
    @staticmethod
    def DropBundle():
        """
        Drop the currently held bundle.
        
        Returns:
            bool: True if drop command was sent
        """
        try:
            if BundleHandler.IsHoldingBundle():
                Player.DropBundle()
                return True
            return False
        except Exception:
            return False


class BundlePickupState:
    """
    State machine for picking up a bundle item.
    
    Usage:
        pickup = BundlePickupState(gadget_x, gadget_y)
        
        # In your execution loop:
        result = pickup.Execute(logger)
        if result == "success":
            # Got the item!
        elif result == "failed":
            # Couldn't get it
        # else: still working ("searching", "interacting", "waiting")
    """
    
    STATE_SEARCH = 0
    STATE_INTERACT = 1
    STATE_WAIT = 2
    STATE_VERIFY = 3
    
    def __init__(self, gadget_x, gadget_y, max_distance=300, max_retries=3):
        """
        Args:
            gadget_x (float): X coordinate of the bundle
            gadget_y (float): Y coordinate of the bundle
            max_distance (float): Search radius
            max_retries (int): Number of pickup attempts before failing
        """
        self.gadget_pos = (gadget_x, gadget_y)
        self.max_distance = max_distance
        self.max_retries = max_retries
        
        self._state = self.STATE_SEARCH
        self._timer = Timer()
        self._timer.Start()
        self._retries = 0
        self._gadget_id = 0
    
    def Reset(self):
        """Reset the pickup state."""
        self._state = self.STATE_SEARCH
        self._timer.Reset()
        self._retries = 0
        self._gadget_id = 0
    
    def Execute(self, logger=None):
        """
        Execute one tick of the pickup state machine.
        
        Returns:
            str: "searching", "interacting", "waiting", "success", or "failed"
        """
        if self._state == self.STATE_SEARCH:
            # Find the gadget
            gadget_id = AgentFinder.FindNearestGadget(
                self.gadget_pos[0], 
                self.gadget_pos[1], 
                self.max_distance
            )
            
            if gadget_id == 0:
                # Silent search - only log after long delay
                if self._timer.HasElapsed(5000):
                    if logger:
                        logger.Add("Searching for item...", (1, 1, 0, 0.7))
                    self._timer.Reset()
                return "searching"
            
            self._gadget_id = gadget_id
            self._state = self.STATE_INTERACT
            self._timer.Reset()
            return "interacting"
        
        elif self._state == self.STATE_INTERACT:
            # Interact with the gadget (no log - action speaks for itself)
            Player.Interact(self._gadget_id)
            self._state = self.STATE_WAIT
            self._timer.Reset()
            return "interacting"
        
        elif self._state == self.STATE_WAIT:
            # Wait for pickup animation
            if self._timer.HasElapsed(1500):
                self._state = self.STATE_VERIFY
                self._timer.Reset()
            return "waiting"
        
        elif self._state == self.STATE_VERIFY:
            # Check if we're holding the bundle
            if BundleHandler.IsHoldingBundle():
                return "success"
            
            # Retry if not holding
            self._retries += 1
            if self._retries >= self.max_retries:
                if logger:
                    logger.Add("Failed to pick up item.", (1, 0, 0, 1), prefix="[Error]")
                return "failed"
            
            self._state = self.STATE_SEARCH
            self._timer.Reset()
            return "searching"
        
        return "searching"


class GadgetInteractionState:
    """
    State machine for interacting with a gadget (lever, catapult, etc.)
    
    Usage:
        interact = GadgetInteractionState(catapult_x, catapult_y, wait_ms=2000)
        
        # In your execution loop:
        result = interact.Execute(logger)
        if result == "complete":
            # Interaction done!
    """
    
    STATE_SEARCH = 0
    STATE_INTERACT = 1
    STATE_WAIT = 2
    
    def __init__(self, gadget_x, gadget_y, wait_ms=1500, max_distance=300):
        """
        Args:
            gadget_x (float): X coordinate of the gadget
            gadget_y (float): Y coordinate of the gadget
            wait_ms (int): Time to wait after interaction (ms)
            max_distance (float): Search radius
        """
        self.gadget_pos = (gadget_x, gadget_y)
        self.wait_ms = wait_ms
        self.max_distance = max_distance
        
        self._state = self.STATE_SEARCH
        self._timer = Timer()
        self._timer.Start()
        self._log_timer = Timer()
        self._log_timer.Start()
        self._gadget_id = 0
    
    def Reset(self):
        """Reset the interaction state."""
        self._state = self.STATE_SEARCH
        self._timer.Reset()
        self._log_timer.Reset()
        self._gadget_id = 0
    
    def Execute(self, logger=None, log_msg="Interacting"):
        """
        Execute one tick of the interaction state machine.
        
        Returns:
            str: "searching", "interacting", "waiting", or "complete"
        """
        if self._state == self.STATE_SEARCH:
            gadget_id = AgentFinder.FindNearestGadget(
                self.gadget_pos[0],
                self.gadget_pos[1],
                self.max_distance
            )
            
            if gadget_id == 0:
                # Silent search - only log after long delay
                if self._log_timer.HasElapsed(5000):
                    if logger:
                        logger.Add("Searching for gadget...", (1, 1, 0, 0.7))
                    self._log_timer.Reset()
                return "searching"
            
            self._gadget_id = gadget_id
            self._state = self.STATE_INTERACT
            return "interacting"
        
        elif self._state == self.STATE_INTERACT:
            # Log the action message once
            if logger and log_msg:
                logger.Add(f"{log_msg}...", (0, 1, 1, 1))
            Player.Interact(self._gadget_id)
            self._timer.Reset()
            self._state = self.STATE_WAIT
            return "interacting"
        
        elif self._state == self.STATE_WAIT:
            if self._timer.HasElapsed(self.wait_ms):
                return "complete"
            return "waiting"
        
        return "searching"


class NPCInteractionHelper:
    """
    Helper for NPC interactions (move to, target, interact).
    """
    
    @staticmethod
    def MoveToAgent(agent_id, min_distance=250, logger=None):
        """
        Move toward an agent until within min_distance.
        
        Args:
            agent_id (int): Agent to move toward
            min_distance (float): Stop distance
            logger: Optional logger
            
        Returns:
            bool: True if within range
        """
        if not Agent.IsValid(agent_id):
            return False
        
        player_pos = Player.GetXY()
        agent_pos = Agent.GetXY(agent_id)
        distance = Utils.Distance(player_pos, agent_pos)
        
        if distance <= min_distance:
            return True
        
        Player.Move(agent_pos[0], agent_pos[1])
        return False
    
    @staticmethod
    def TargetAndInteract(agent_id):
        """
        Target an agent and interact with it.
        
        Args:
            agent_id (int): Agent to interact with
            
        Returns:
            bool: True if interaction initiated
        """
        if not Agent.IsValid(agent_id):
            return False
        
        Player.ChangeTarget(agent_id)
        Player.Interact(agent_id)
        return True
    
    @staticmethod
    def SendDialog(dialog_id):
        """
        Send a dialog response.
        
        Args:
            dialog_id (int): Dialog ID to send
        """
        Player.SendDialog(dialog_id)
