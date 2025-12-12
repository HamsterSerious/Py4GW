"""
OutpostHandler.py - Generic outpost state machine for ZeroToHero missions.

Provides a reusable state machine for:
- Validating party composition
- Finding and talking to NPCs
- Sending dialog sequences to start missions
- Handling the "Enter Mission" button (non-NPC missions)

Usage:
    # For NPC-initiated missions:
    handler = OutpostHandler(
        requirements=PartyRequirements(min_size=4, required_heroes=["Koss"]),
        npc_position=(3482, -5167),
        npc_name="First Spear Jahdugar",
        dialog_sequence=[0x81, 0x84]  # Accept quest, then start mission
    )
    
    # For button-initiated missions (no NPC):
    handler = OutpostHandler(
        requirements=PartyRequirements(min_size=4),
        use_enter_button=True
    )
    
    # In your execution loop:
    if handler.Execute(bot, logger):
        # Outpost phase complete! Transition to mission logic
"""

from Py4GWCoreLib import *
from .PartyUtils import PartyRequirements, PartyValidator
from .AgentUtils import AgentFinder
from .MapUtils import MapValidator


class OutpostHandler:
    """
    Generic state machine for handling the outpost phase of missions.
    """
    
    # States
    STATE_VALIDATE_PARTY = 0
    STATE_FIND_NPC = 1
    STATE_MOVE_TO_NPC = 2
    STATE_TARGET_NPC = 3
    STATE_INTERACT_NPC = 4
    STATE_SEND_DIALOG = 5
    STATE_WAIT_DIALOG = 6
    STATE_NEXT_DIALOG = 7
    STATE_ENTER_BUTTON = 8
    STATE_WAIT_LOAD = 9
    STATE_COMPLETE = 10
    STATE_FAILED = -1
    
    def __init__(
        self,
        requirements=None,
        npc_position=None,
        npc_name=None,
        dialog_sequence=None,
        use_enter_button=False,
        outpost_map_id=None,
        npc_search_radius=500,
        interact_distance=250,
        dialog_wait_ms=1500
    ):
        """
        Args:
            requirements (PartyRequirements): Party validation requirements
            npc_position (tuple): (x, y) position of quest NPC
            npc_name (str): Name of quest NPC (for logging)
            dialog_sequence (list): List of dialog IDs to send in order
            use_enter_button (bool): If True, use Enter Mission button instead of NPC
            outpost_map_id (int): Expected outpost map ID (optional validation)
            npc_search_radius (float): Radius to search for NPC
            interact_distance (float): Distance to stop and interact
            dialog_wait_ms (int): Time to wait between dialogs
        """
        self.requirements = requirements or PartyRequirements()
        self.npc_position = npc_position
        self.npc_name = npc_name or "Quest NPC"
        self.dialog_sequence = dialog_sequence or []
        self.use_enter_button = use_enter_button
        self.outpost_map_id = outpost_map_id
        self.npc_search_radius = npc_search_radius
        self.interact_distance = interact_distance
        self.dialog_wait_ms = dialog_wait_ms
        
        # State tracking
        self._state = self.STATE_VALIDATE_PARTY
        self._current_npc_id = 0
        self._dialog_index = 0
        self._failure_reason = None
        
        # Timers
        self._timer = Timer()
        self._timer.Start()
        self._move_timer = Timer()
        self._move_timer.Start()
        self._search_timer = Timer()
        self._search_timer.Start()
    
    def Reset(self):
        """Reset the handler state for reuse."""
        self._state = self.STATE_VALIDATE_PARTY
        self._current_npc_id = 0
        self._dialog_index = 0
        self._failure_reason = None
        self._timer.Reset()
        self._move_timer.Reset()
        self._search_timer.Reset()
    
    def IsComplete(self):
        """Check if outpost phase is complete."""
        return self._state == self.STATE_COMPLETE
    
    def IsFailed(self):
        """Check if outpost phase failed."""
        return self._state == self.STATE_FAILED
    
    def GetFailureReason(self):
        """Get the reason for failure."""
        return self._failure_reason
    
    def GetCurrentState(self):
        """Get current state (for debugging)."""
        state_names = {
            0: "VALIDATE_PARTY", 1: "FIND_NPC", 2: "MOVE_TO_NPC",
            3: "TARGET_NPC", 4: "INTERACT_NPC", 5: "SEND_DIALOG",
            6: "WAIT_DIALOG", 7: "NEXT_DIALOG", 8: "ENTER_BUTTON",
            9: "WAIT_LOAD", 10: "COMPLETE", -1: "FAILED"
        }
        return state_names.get(self._state, "UNKNOWN")
    
    def Execute(self, bot, logger):
        """
        Execute one tick of the outpost state machine.
        
        Args:
            bot: The BotState object
            logger: Logger for status messages
            
        Returns:
            bool: True if complete (ready to enter mission logic)
        """
        # Handle map loading
        if MapValidator.IsMapLoading():
            return False
        
        # Verify we're in an outpost
        if not MapValidator.IsInOutpost():
            if MapValidator.IsInExplorable():
                # We're already in the mission!
                self._state = self.STATE_COMPLETE
                return True
            return False
        
        # Optional: Verify correct outpost
        if self.outpost_map_id:
            current_map = MapValidator.GetCurrentMapID()
            if current_map != self.outpost_map_id:
                self._failure_reason = f"Wrong outpost (ID: {current_map})"
                logger.Add(self._failure_reason, (1, 0, 0, 1), prefix="[Error]")
                self._state = self.STATE_FAILED
                bot.is_running = False
                return False
        
        # Execute current state
        if self._state == self.STATE_VALIDATE_PARTY:
            return self._ExecuteValidateParty(bot, logger)
        
        elif self._state == self.STATE_FIND_NPC:
            return self._ExecuteFindNPC(bot, logger)
        
        elif self._state == self.STATE_MOVE_TO_NPC:
            return self._ExecuteMoveToNPC(bot, logger)
        
        elif self._state == self.STATE_TARGET_NPC:
            return self._ExecuteTargetNPC(bot, logger)
        
        elif self._state == self.STATE_INTERACT_NPC:
            return self._ExecuteInteractNPC(bot, logger)
        
        elif self._state == self.STATE_SEND_DIALOG:
            return self._ExecuteSendDialog(bot, logger)
        
        elif self._state == self.STATE_WAIT_DIALOG:
            return self._ExecuteWaitDialog(bot, logger)
        
        elif self._state == self.STATE_NEXT_DIALOG:
            return self._ExecuteNextDialog(bot, logger)
        
        elif self._state == self.STATE_ENTER_BUTTON:
            return self._ExecuteEnterButton(bot, logger)
        
        elif self._state == self.STATE_WAIT_LOAD:
            return self._ExecuteWaitLoad(bot, logger)
        
        elif self._state == self.STATE_COMPLETE:
            return True
        
        elif self._state == self.STATE_FAILED:
            return False
        
        return False
    
    # --- State Implementations ---
    
    def _ExecuteValidateParty(self, bot, logger):
        """Validate party requirements."""
        is_valid, error_msg = self.requirements.Validate(logger)
        
        if not is_valid:
            self._failure_reason = error_msg
            self._state = self.STATE_FAILED
            bot.is_running = False
            return False
        
        logger.Add("Party validated. Preparing to start mission...", (0, 1, 0, 1))
        
        # Decide next state
        if self.use_enter_button:
            self._state = self.STATE_ENTER_BUTTON
        else:
            self._state = self.STATE_FIND_NPC
        
        self._timer.Reset()
        return False
    
    def _ExecuteFindNPC(self, bot, logger):
        """Find the quest NPC."""
        if not self.npc_position:
            self._failure_reason = "No NPC position configured"
            logger.Add(self._failure_reason, (1, 0, 0, 1), prefix="[Error]")
            self._state = self.STATE_FAILED
            bot.is_running = False
            return False
        
        npc_id = AgentFinder.FindNearestNPC(
            self.npc_position[0],
            self.npc_position[1],
            self.npc_search_radius
        )
        
        if npc_id == 0:
            if self._search_timer.HasElapsed(5000):
                logger.Add(f"Searching for {self.npc_name}...", (1, 1, 0, 1))
                self._search_timer.Reset()
            return False
        
        self._current_npc_id = npc_id
        self._state = self.STATE_MOVE_TO_NPC
        self._move_timer.Reset()
        return False
    
    def _ExecuteMoveToNPC(self, bot, logger):
        """Move toward the NPC."""
        npc_id = self._current_npc_id
        
        if not Agent.IsValid(npc_id):
            self._state = self.STATE_FIND_NPC
            return False
        
        player_pos = Player.GetXY()
        npc_pos = Agent.GetXY(npc_id)
        distance = Utils.Distance(player_pos, npc_pos)
        
        if distance > self.interact_distance:
            if self._move_timer.HasElapsed(1000):
                Player.Move(npc_pos[0], npc_pos[1])
                self._move_timer.Reset()
            return False
        
        self._state = self.STATE_TARGET_NPC
        self._timer.Reset()
        return False
    
    def _ExecuteTargetNPC(self, bot, logger):
        """Target the NPC."""
        Player.ChangeTarget(self._current_npc_id)
        self._state = self.STATE_INTERACT_NPC
        self._timer.Reset()
        return False
    
    def _ExecuteInteractNPC(self, bot, logger):
        """Interact with NPC to open dialog."""
        if self._timer.HasElapsed(500):
            Player.Interact(self._current_npc_id)
            self._state = self.STATE_SEND_DIALOG
            self._dialog_index = 0
            self._timer.Reset()
        return False
    
    def _ExecuteSendDialog(self, bot, logger):
        """Send the current dialog in sequence."""
        if not self._timer.HasElapsed(self.dialog_wait_ms):
            return False
        
        if self._dialog_index >= len(self.dialog_sequence):
            # All dialogs sent
            logger.Add("Entering mission...", (0, 1, 0, 1))
            self._state = self.STATE_WAIT_LOAD
            self._timer.Reset()
            return False
        
        dialog_id = self.dialog_sequence[self._dialog_index]
        Player.SendDialog(dialog_id)
        self._state = self.STATE_WAIT_DIALOG
        self._timer.Reset()
        return False
    
    def _ExecuteWaitDialog(self, bot, logger):
        """Wait after sending a dialog."""
        if self._timer.HasElapsed(self.dialog_wait_ms):
            self._state = self.STATE_NEXT_DIALOG
        return False
    
    def _ExecuteNextDialog(self, bot, logger):
        """Move to next dialog or finish."""
        self._dialog_index += 1
        
        if self._dialog_index >= len(self.dialog_sequence):
            logger.Add("Entering mission...", (0, 1, 0, 1))
            self._state = self.STATE_WAIT_LOAD
        else:
            # Need to re-interact for next dialog
            self._state = self.STATE_INTERACT_NPC
        
        self._timer.Reset()
        return False
    
    def _ExecuteEnterButton(self, bot, logger):
        """Handle Enter Mission button (non-NPC missions)."""
        # TODO: Implement Enter Mission button logic
        logger.Add("Enter Mission button not yet implemented.", (1, 1, 0, 1), prefix="[TODO]")
        self._state = self.STATE_WAIT_LOAD
        self._timer.Reset()
        return False
    
    def _ExecuteWaitLoad(self, bot, logger):
        """Wait for mission to load."""
        # Check if we've transitioned to explorable
        if MapValidator.IsInExplorable():
            self._state = self.STATE_COMPLETE
            return True
        
        # Timeout check (30 seconds)
        if self._timer.HasElapsed(30000):
            logger.Add("Still waiting for mission to load...", (1, 0.5, 0, 1), prefix="[Warn]")
            self._timer.Reset()
        
        return False
