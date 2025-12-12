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
    STATE_STOP_MOVING = 3      # NEW: Ensure we stop before targeting
    STATE_TARGET_NPC = 4
    STATE_WAIT_TARGET = 5      # NEW: Wait for target to register
    STATE_INTERACT_NPC = 6
    STATE_WAIT_DIALOG_OPEN = 7
    STATE_SEND_DIALOG = 8
    STATE_WAIT_DIALOG = 9
    STATE_NEXT_DIALOG = 10
    STATE_ENTER_BUTTON = 11
    STATE_WAIT_LOAD = 12
    STATE_COMPLETE = 13
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
        dialog_wait_ms=1500,        # Increased from 1000
        dialog_open_wait_ms=1200    # Increased from 800
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
            dialog_open_wait_ms (int): Time to wait for dialog window to open
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
        self.dialog_open_wait_ms = dialog_open_wait_ms
        
        # State tracking
        self._state = self.STATE_VALIDATE_PARTY
        self._current_npc_id = 0
        self._dialog_index = 0
        self._failure_reason = None
        self._interact_attempts = 0
        self._max_interact_attempts = 5  # Increased from 3
        
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
        self._interact_attempts = 0
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
            3: "STOP_MOVING", 4: "TARGET_NPC", 5: "WAIT_TARGET",
            6: "INTERACT_NPC", 7: "WAIT_DIALOG_OPEN",
            8: "SEND_DIALOG", 9: "WAIT_DIALOG", 10: "NEXT_DIALOG", 
            11: "ENTER_BUTTON", 12: "WAIT_LOAD", 13: "COMPLETE", -1: "FAILED"
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
        
        elif self._state == self.STATE_STOP_MOVING:
            return self._ExecuteStopMoving(bot, logger)
        
        elif self._state == self.STATE_TARGET_NPC:
            return self._ExecuteTargetNPC(bot, logger)
        
        elif self._state == self.STATE_WAIT_TARGET:
            return self._ExecuteWaitTarget(bot, logger)
        
        elif self._state == self.STATE_INTERACT_NPC:
            return self._ExecuteInteractNPC(bot, logger)
        
        elif self._state == self.STATE_WAIT_DIALOG_OPEN:
            return self._ExecuteWaitDialogOpen(bot, logger)
        
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
        
        # Close enough - stop moving first
        self._state = self.STATE_STOP_MOVING
        self._timer.Reset()
        return False
    
    def _ExecuteStopMoving(self, bot, logger):
        """Stop all movement before targeting NPC."""
        # Cancel any movement
        player_pos = Player.GetXY()
        Player.Move(player_pos[0], player_pos[1])  # Move to self = stop
        
        # Wait a moment for movement to stop
        if self._timer.HasElapsed(300):
            self._state = self.STATE_TARGET_NPC
            self._timer.Reset()
        return False
    
    def _ExecuteTargetNPC(self, bot, logger):
        """Target the NPC."""
        Player.ChangeTarget(self._current_npc_id)
        self._state = self.STATE_WAIT_TARGET
        self._timer.Reset()
        return False
    
    def _ExecuteWaitTarget(self, bot, logger):
        """Wait for target to register."""
        # Verify target is set correctly
        if self._timer.HasElapsed(500):
            current_target = Player.GetTargetID()
            if current_target != self._current_npc_id:
                # Target didn't stick, retry
                logger.Add("Re-targeting NPC...", (1, 1, 0, 1))
                self._state = self.STATE_TARGET_NPC
                return False
            
            self._state = self.STATE_INTERACT_NPC
            self._timer.Reset()
        return False
    
    def _ExecuteInteractNPC(self, bot, logger):
        """Interact with NPC to open dialog."""
        # Wait a moment after targeting
        if not self._timer.HasElapsed(500):
            return False
        
        logger.Add(f"Talking to {self.npc_name}...", (0, 1, 1, 1))
        Player.Interact(self._current_npc_id)
        self._state = self.STATE_WAIT_DIALOG_OPEN
        self._timer.Reset()
        return False
    
    def _ExecuteWaitDialogOpen(self, bot, logger):
        """Wait for dialog window to open."""
        if not self._timer.HasElapsed(self.dialog_open_wait_ms):
            return False
        
        # Dialog should be open now, move to send
        self._state = self.STATE_SEND_DIALOG
        self._timer.Reset()
        return False
    
    def _ExecuteSendDialog(self, bot, logger):
        """Send the current dialog in sequence."""
        if self._dialog_index >= len(self.dialog_sequence):
            # All dialogs sent
            logger.Add("Entering mission...", (0, 1, 0, 1))
            self._state = self.STATE_WAIT_LOAD
            self._timer.Reset()
            return False
        
        dialog_id = self.dialog_sequence[self._dialog_index]
        
        # Send dialog (no logging of dialog ID - user doesn't need to see it)
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
            # For multi-dialog sequences, we might need to re-interact
            # But first try just sending the next dialog
            self._state = self.STATE_SEND_DIALOG
        
        self._timer.Reset()
        return False
    
    def _ExecuteEnterButton(self, bot, logger):
        """Handle Enter Mission button (non-NPC missions)."""
        # Use the Map.EnterChallenge() for missions with enter button
        if Map.HasEnterChallengeButton():
            logger.Add("Clicking Enter Mission...", (0, 1, 0, 1))
            Map.EnterChallenge()
            self._state = self.STATE_WAIT_LOAD
            self._timer.Reset()
        else:
            # No button available, wait for it
            if self._timer.HasElapsed(5000):
                logger.Add("Waiting for Enter Mission button...", (1, 1, 0, 1))
                self._timer.Reset()
        return False
    
    def _ExecuteWaitLoad(self, bot, logger):
        """Wait for mission to load."""
        # Check if we've transitioned to explorable
        if MapValidator.IsInExplorable():
            self._state = self.STATE_COMPLETE
            return True
        
        # Timeout check - try re-interacting
        if self._timer.HasElapsed(10000):  # Reduced from 15000 for faster retry
            self._interact_attempts += 1
            
            if self._interact_attempts >= self._max_interact_attempts:
                logger.Add("Failed to start mission after multiple attempts.", (1, 0, 0, 1), prefix="[Error]")
                self._state = self.STATE_FAILED
                return False
            
            logger.Add(f"Retrying mission start (attempt {self._interact_attempts}/{self._max_interact_attempts})...", (1, 0.5, 0, 1), prefix="[Warn]")
            
            # Go back to finding and targeting NPC
            self._dialog_index = 0
            self._state = self.STATE_FIND_NPC
            self._timer.Reset()
            self._search_timer.Reset()
        
        return False
