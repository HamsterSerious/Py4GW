"""
MissionContext.py - Base classes for ZeroToHero missions.

Provides:
- MissionContext: Interface definition for mission modules
- BaseMission: Helper class with standardized mission methods
"""

from Py4GWCoreLib import *

# Import all shared utilities
from .CombatHandler import CombatHandler
from .Navigation import MissionNavigation
from .PartyUtils import PartyRequirements, PartyValidator
from .AgentUtils import AgentFinder, AgentPosition
from .MapUtils import MapValidator, MissionStateTracker, MapWaiter
from .InteractionUtils import BundleHandler, BundlePickupState, GadgetInteractionState, NPCInteractionHelper
from .OutpostHandler import OutpostHandler


class MissionContext:
    """
    Interface definition for Mission Modules.
    All missions must implement these methods.
    """
    
    def GetInfo(self):
        """
        Returns a dict with mission metadata.
        
        Expected keys:
            - Name (str): Display name of the mission
            - Description (str): Brief description
            - Recommended_Builds (list): List of recommended builds/heroes
            - HM_Tips (str): Hard Mode specific tips
        """
        raise NotImplementedError

    def Execution_Routine(self, bot, logger):
        """
        Main update loop. Called every frame while bot is running.
        
        Args:
            bot: The BotState object
            logger: The LogConsole object for logging to UI
        """
        raise NotImplementedError

    def Reset(self):
        """
        Called when the bot is started to reset the mission state.
        """
        pass


class BaseMission:
    """
    A helper class that provides standardized methods for common mission tasks
    like Movement, Interaction, Dialogs, and state tracking.
    
    NOTE: This class does NOT inherit from MissionContext to prevent the 
    MissionLoader from trying to load it as a standalone mission.
    Actual missions should inherit from (BaseMission, MissionContext).
    
    Usage:
        class MyMission(BaseMission, MissionContext):
            Outpost_Map_ID = 123
            Mission_Map_ID = 456
            
            def __init__(self):
                super().__init__()
                # Mission-specific init
    """
    
    # Override these in subclass
    Outpost_Map_ID = 0
    Mission_Map_ID = 0
    
    def __init__(self):
        # Core handlers
        self.combat_handler = CombatHandler()
        self.nav = MissionNavigation(self.combat_handler)
        
        # State tracking
        self.step = 1
        self.sub_state = 0
        self.waiting = False
        
        # Mission state tracker
        self.mission_tracker = MissionStateTracker(
            mission_map_id=self.Mission_Map_ID,
            outpost_map_id=self.Outpost_Map_ID
        )
        
        # Timers
        self.timer = Timer()
        self.timer.Start()
        self._move_timer = Timer()
        self._move_timer.Start()
        self._interact_timer = Timer()
        self._interact_timer.Start()

    def Reset(self):
        """Resets all standard state variables."""
        self.step = 1
        self.sub_state = 0
        self.waiting = False
        
        self.timer.Reset()
        self._move_timer.Reset()
        self._interact_timer.Reset()
        
        self.nav.Reset()
        self.mission_tracker.Reset()

    # --- Map Utilities ---
    
    def IsInOutpost(self):
        """Check if we're in the outpost."""
        return MapValidator.IsInOutpost()
    
    def IsInMission(self):
        """Check if we're in the mission instance."""
        return MapValidator.IsInExplorable() and MapValidator.IsOnMap(self.Mission_Map_ID)
    
    def CheckMissionEnd(self, bot, logger):
        """
        Check if mission ended (complete or failed).
        Should be called each frame in mission logic.
        
        Returns:
            bool: True if mission ended
        """
        if self.mission_tracker.Update(logger):
            bot.is_running = False
            return True
        return False
    
    def VerifyCorrectMap(self, bot, logger):
        """
        Verify we're on the correct map. Stops bot if not.
        
        Returns:
            bool: True if on correct map
        """
        is_mission_phase = self.step >= 3  # Typically steps 1-2 are outpost
        
        if not self.mission_tracker.VerifyCorrectMap(is_mission_phase, logger):
            bot.is_running = False
            return False
        return True

    # --- Movement Utilities ---

    def ExecuteMove(self, path_handler, next_step_id, logger, log_msg=None):
        """
        Executes a move operation using the MissionNavigation handler.
        Automatically advances the step when the path is finished.
        
        Args:
            path_handler: PathHandler with waypoints
            next_step_id (int): Step to advance to when complete
            logger: Logger for status messages
            log_msg (str): Optional message to log when starting
            
        Returns:
            bool: True if movement complete
        """
        if log_msg and not self.waiting:
            logger.Add(log_msg, prefix="[Move]")
            self.waiting = True

        if self.nav.Execute(path_handler, logger):
            self.step = next_step_id
            self.waiting = False
            self.sub_state = 0
            path_handler.reset()
            return True
        return False

    # --- Interaction Utilities ---

    def ExecuteInteract(self, gadget_id, wait_after_ms, next_step_id, logger, log_msg="Interacting"):
        """
        Handles a simple gadget interaction.
        
        Args:
            gadget_id (int): Agent ID of gadget
            wait_after_ms (int): Time to wait after interaction
            next_step_id (int): Step to advance to when complete
            logger: Logger for status messages
            log_msg (str): Message to log
            
        Returns:
            bool: True if interaction complete
        """
        if self.sub_state == 0:
            if Agent.IsValid(gadget_id):
                logger.Add(f"{log_msg}...", prefix="[Interact]")
                Player.Interact(gadget_id)
                self.timer.Reset()
                self.sub_state = 1
            
        elif self.sub_state == 1:
            if self.timer.HasElapsed(wait_after_ms):
                self.sub_state = 0
                self.step = next_step_id
                return True
        return False

    def ExecuteDialog(self, npc_id, dialog_id, wait_after_ms, next_step_id, logger):
        """
        Handles approaching an NPC and sending a dialog.
        
        Args:
            npc_id (int): Agent ID of NPC
            dialog_id (int): Dialog ID to send
            wait_after_ms (int): Time to wait after dialog
            next_step_id (int): Step to advance to when complete
            logger: Logger for status messages
            
        Returns:
            bool: True if dialog complete
        """
        if self.sub_state == 0:
            if not Agent.IsValid(npc_id):
                return False

            Player.ChangeTarget(npc_id)
            
            p_pos = Player.GetXY()
            npc_pos = Agent.GetXY(npc_id)
            if Utils.Distance(p_pos, npc_pos) > 250:
                Player.Move(npc_pos[0], npc_pos[1])
            else:
                self.sub_state = 1
                
        elif self.sub_state == 1:
            Player.SendDialog(dialog_id)
            self.timer.Reset()
            self.sub_state = 2
            
        elif self.sub_state == 2:
            if self.timer.HasElapsed(wait_after_ms):
                self.sub_state = 0
                self.step = next_step_id
                return True
        return False

    # --- Agent Finding Shortcuts ---
    
    def FindNearestNPC(self, x, y, max_distance=300):
        """Find nearest NPC at position."""
        return AgentFinder.FindNearestNPC(x, y, max_distance)
    
    def FindNearestGadget(self, x, y, max_distance=300):
        """Find nearest gadget at position."""
        return AgentFinder.FindNearestGadget(x, y, max_distance)
    
    def FindNearestEnemy(self, max_distance=1200):
        """Find nearest alive enemy."""
        return AgentFinder.FindNearestEnemy(max_distance)

    # --- Bundle Handling Shortcuts ---
    
    def IsHoldingBundle(self):
        """Check if holding a bundle item."""
        return BundleHandler.IsHoldingBundle()
    
    def DropBundle(self):
        """Drop the current bundle."""
        return BundleHandler.DropBundle()
