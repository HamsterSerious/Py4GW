"""
Transition System - Handles map travel and mission lifecycle.

Provides:
- Travel to maps
- Mission entry from outpost (complete sequence)
- Mission completion waiting
- Team setup with HM/NM handling
"""
import Py4GW
from Py4GWCoreLib import Routines, Player
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from data.enums import GameMode
from data.timing import Timing, Range
from utils.timer import Timeout


class Transition:
    """
    Handles transitions between maps and mission lifecycle.
    
    Key methods for missions:
    - enter_mission_from_outpost(): Complete mission entry sequence
    - wait_for_mission_end(): Wait for mission completion
    """
    
    def __init__(self, bot):
        self.bot = bot

    # ==================
    # PROPERTIES
    # ==================

    @property
    def is_outpost(self) -> bool:
        """Check if current map is an outpost."""
        return GLOBAL_CACHE.Map.IsOutpost()
    
    @property
    def is_explorable(self) -> bool:
        """Check if current map is explorable (mission/instance)."""
        return GLOBAL_CACHE.Map.IsExplorable()
    
    @property
    def is_loading(self) -> bool:
        """Check if map is currently loading."""
        return GLOBAL_CACHE.Map.IsMapLoading()
    
    @property
    def is_ready(self) -> bool:
        """Check if map is ready for interaction."""
        return GLOBAL_CACHE.Map.IsMapReady()
    
    @property
    def current_map_id(self) -> int:
        """Get current map ID."""
        return GLOBAL_CACHE.Map.GetMapID()

    # ==================
    # HIGH-LEVEL MISSION API
    # ==================

    def enter_mission_from_outpost(
        self,
        outpost_map_id: int,
        npc_model_id: int,
        dialog_id: int,
        npc_position: tuple = None,
        use_hard_mode: bool = False
    ):
        """
        Complete mission entry sequence: travel → setup team → talk to NPC → enter.
        
        This is the PRIMARY method missions should use for starting.
        Handles all the boilerplate of entering a mission.
        
        Args:
            outpost_map_id: Map ID of the mission outpost
            npc_model_id: Model ID of the NPC that starts the mission
            dialog_id: Dialog option to select (e.g., 0x84)
            npc_position: Optional (x, y) hint for NPC location
            use_hard_mode: Whether to enter in Hard Mode
            
        Yields for coroutine execution.
        Returns True if successfully entered mission, False otherwise.
        """
        # 1. Handle starting from explorable area (e.g., after Chahbek Village)
        #    We need to travel to the outpost first - can't setup team or HM in explorable
        if self.is_explorable:
            self._log("Currently in explorable area, traveling to outpost...")
            yield from self.travel_to(outpost_map_id)
        
        # 2. Travel to outpost if not already there
        if self.current_map_id != outpost_map_id:
            self._log("Traveling to outpost...")
            yield from self.travel_to(outpost_map_id)
        
        # 3. Verify we're in an outpost now
        if not self.is_outpost:
            self._log("Failed to reach outpost!", error=True)
            return False
        
        # 4. Setup team and hard mode (now safe - we're in outpost)
        self._log("Setting up team...")
        yield from self.setup_mission(self.bot, use_hard_mode)
        
        # 5. Find and interact with mission NPC
        self._log("Starting mission...")
        success = yield from self._start_mission_via_npc(npc_model_id, dialog_id, npc_position)
        
        if not success:
            return False
        
        # 6. Verify we left the outpost
        if self.is_outpost:
            self._log("Failed to enter mission!", error=True)
            return False
        
        self._log("Mission entered successfully!")
        return True

    def wait_for_mission_end(
        self,
        current_mission_map_id: int,
        timeout_ms: int = None
    ):
        """
        Waits for mission completion (map change or loading screen).
        
        Call this after completing mission objectives - the game will
        automatically transition you to the reward/outpost.
        
        Args:
            current_mission_map_id: The map ID of the mission we're in
            timeout_ms: Maximum time to wait (default: Timing.MAP_EXIT_TIMEOUT)
            
        Yields for coroutine execution.
        """
        timeout_ms = timeout_ms or Timing.MAP_EXIT_TIMEOUT
        
        self._log("Waiting for mission completion...")
        
        # Wait for map exit (loading screen or map ID change)
        timeout = Timeout(timeout_ms)
        while not timeout.expired:
            # Loading screen started
            if self.is_loading:
                self._log("Loading screen detected...")
                break
            
            # Map ID changed
            if self.current_map_id != current_mission_map_id and self.current_map_id != 0:
                self._log("Map change detected...")
                break
            
            yield
        
        if timeout.expired:
            self._log("Timeout waiting for map exit", warning=True)
        
        # Wait for new map to be ready
        yield from self._wait_until_map_ready(timeout_ms=Timing.MAP_LOAD_TIMEOUT)
        
        self._log(f"Arrived at map {self.current_map_id}")

    # ==================
    # CORE TRAVEL METHODS
    # ==================
    
    def travel_to(self, map_id: int):
        """
        Handles traveling to a map.
        Automatically disbands party (only in outpost) to avoid travel issues.
        
        Args:
            map_id: Destination map ID
            
        Yields for coroutine execution.
        """
        # Check if already at destination
        if self.current_map_id == map_id and self.is_ready:
            self._log(f"Already at map {map_id}")
            return
        
        # Disband party before travel (only works in outpost)
        if self.is_outpost and GLOBAL_CACHE.Party.GetPartySize() > 1:
            self._log("Disbanding party before travel...")
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            yield from Routines.Yield.wait(Timing.PARTY_DISBAND_WAIT)
        
        self._log(f"Traveling to Map ID: {map_id}")
        GLOBAL_CACHE.Map.Travel(map_id)
        yield from self._wait_until_map_ready()

    def setup_mission(self, bot, use_hard_mode: bool = False):
        """
        Sets up the team based on the current mission settings.
        Handles hard mode toggle and team loading.
        
        Args:
            bot: Bot instance
            use_hard_mode: Whether to enable hard mode
            
        Yields for coroutine execution.
        Returns the actual game mode being used (may differ if HM not unlocked).
        """
        # Try to sync hard mode
        hm_success = yield from self._sync_hard_mode(use_hard_mode)
        
        # Determine actual mode (if HM toggle failed, we're in NM)
        actual_hard_mode = GLOBAL_CACHE.Party.IsHardMode()
        if use_hard_mode and not actual_hard_mode:
            self._log("Running in Normal Mode (Hard Mode unavailable)", warning=True)
        
        game_mode = GameMode.from_bool(actual_hard_mode)
        
        # Get team parameters
        party_size = self._get_party_size()
        mandatory_list = self._get_mandatory_heroes(bot, game_mode)
        mission_name = self._get_mission_name(bot)
        
        # Load team
        if mandatory_list:
            self._log(f"Loading team with {len(mandatory_list)} mandatory hero(es)")
            yield from bot.team_manager.load_team_with_mandatory_heroes(
                party_size, game_mode.value, mandatory_list, mission_name=mission_name
            )
        else:
            yield from bot.team_manager.load_team(party_size, game_mode.value)
        
        return game_mode

    # ==================
    # PRIVATE: NPC INTERACTION
    # ==================

    def _start_mission_via_npc(
        self,
        npc_model_id: int,
        dialog_id: int,
        npc_position: tuple = None
    ):
        """
        Finds NPC, approaches, and sends dialog to start mission.
        
        Returns True if dialog was sent successfully.
        """
        # Find the NPC
        npc_agent_id = Routines.Agents.GetAgentIDByModelID(npc_model_id)
        
        if npc_agent_id == 0 and npc_position:
            # NPC not visible, move to expected position first
            self._log("NPC not visible, moving to expected location...")
            yield from self.bot.movement.move_to(npc_position[0], npc_position[1])
            yield from Routines.Yield.wait(Timing.MEDIUM_DELAY)
            npc_agent_id = Routines.Agents.GetAgentIDByModelID(npc_model_id)
        
        if npc_agent_id == 0:
            self._log(f"Could not find NPC (Model: {npc_model_id})", error=True)
            return False
        
        # Get NPC name for logging
        try:
            npc_name = GLOBAL_CACHE.Agent.GetName(npc_agent_id) or f"NPC {npc_model_id}"
        except:
            npc_name = f"NPC {npc_model_id}"
        
        self._log(f"Talking to {npc_name}...")
        
        # Interact with NPC
        x, y = npc_position if npc_position else (0, 0)
        yield from self.bot.interaction.move_to_and_interact(npc_agent_id, x, y)
        
        # Wait for dialog window to fully open
        yield from Routines.Yield.wait(Timing.NPC_DIALOG_OPEN_DELAY)
        
        # Send dialog
        self._log("Accepting mission...")
        Player.SendDialog(dialog_id)
        
        # Wait for mission countdown + loading
        # GW1 has a 5-10 second countdown after accepting, then loading
        # We poll during this time instead of blocking
        self._log("Waiting for mission countdown...")
        timeout = Timeout(Timing.MISSION_COUNTDOWN_WAIT)
        
        while not timeout.expired:
            # Check if we're loading (countdown finished, now loading)
            if self.is_loading:
                self._log("Loading mission...")
                break
            
            # Check if we already left the outpost (very fast load)
            if not self.is_outpost:
                break
            
            yield from Routines.Yield.wait(Timing.MAP_READY_POLL)
        
        # Now wait for the map to be fully ready
        yield from self._wait_until_map_ready(timeout_ms=Timing.MAP_LOAD_TIMEOUT, expect_map_change=True)
        
        return True

    # ==================
    # PRIVATE: MAP LOADING
    # ==================

    def _wait_until_map_ready(self, timeout_ms: int = None, expect_map_change: bool = False):
        """
        Waits for map to finish loading and be ready.
        
        Args:
            timeout_ms: Maximum wait time (default: Timing.MAP_LOAD_TIMEOUT)
            expect_map_change: If True, waits for loading to START before checking ready
        """
        timeout_ms = timeout_ms or Timing.MAP_LOAD_TIMEOUT
        timeout = Timeout(timeout_ms)
        
        if expect_map_change:
            # When expecting a map change (like mission entry), we MUST see loading start
            # Don't return early just because current map is "ready"
            loading_started = False
            
            while not timeout.expired:
                if self.is_loading:
                    loading_started = True
                    break
                # Also check if map ID changed (some transitions are fast)
                yield from Routines.Yield.wait(Timing.FRAME_DELAY)
            
            if not loading_started and not timeout.expired:
                # Check if we somehow ended up in a different map state
                if not self.is_outpost:
                    # We're in explorable now, transition happened
                    yield from Routines.Yield.wait(Timing.MAP_LOAD_BUFFER)
                    return
        else:
            # Standard wait - check if already loading or ready
            while not timeout.expired:
                if self.is_loading:
                    break
                if self.is_ready:
                    yield from Routines.Yield.wait(Timing.MAP_LOAD_BUFFER)
                    return
                yield from Routines.Yield.wait(Timing.FRAME_DELAY)
        
        # Wait for loading to finish
        while not timeout.expired and self.is_loading:
            yield from Routines.Yield.wait(Timing.MAP_READY_POLL)
        
        # Wait for ready flag
        while not timeout.expired and not self.is_ready:
            yield from Routines.Yield.wait(Timing.MAP_READY_POLL)
        
        # Final buffer
        yield from Routines.Yield.wait(Timing.MAP_LOAD_BUFFER)

    # ==================
    # PRIVATE: HELPERS
    # ==================

    def _sync_hard_mode(self, use_hard_mode: bool):
        """
        Syncs game hard mode state with desired state. Only works in outpost.
        
        Returns True if mode is correct, False if failed (e.g., HM not unlocked).
        """
        # Hard mode can only be toggled in outpost
        if not self.is_outpost:
            self._log("Not in outpost, skipping hard mode toggle", warning=True)
            return True  # Not an error, just can't toggle here
        
        is_hm = GLOBAL_CACHE.Party.IsHardMode()
        
        # Already in correct mode?
        if use_hard_mode == is_hm:
            return True
        
        # Try to toggle with verification
        max_attempts = 3
        
        if use_hard_mode and not is_hm:
            self._log("Enabling Hard Mode...")
            
            for attempt in range(max_attempts):
                GLOBAL_CACHE.Party.SetHardMode()
                yield from Routines.Yield.wait(Timing.HARD_MODE_TOGGLE)
                
                # Verify it worked
                if GLOBAL_CACHE.Party.IsHardMode():
                    self._log("Hard Mode enabled.")
                    return True
                
                if attempt < max_attempts - 1:
                    self._log(f"Hard Mode toggle failed, retrying... ({attempt + 1}/{max_attempts})", warning=True)
            
            # All attempts failed - likely HM not unlocked
            self._log("Failed to enable Hard Mode - may not be unlocked for this campaign!", error=True)
            self._log("Continuing in Normal Mode instead.", warning=True)
            return False
            
        elif not use_hard_mode and is_hm:
            self._log("Disabling Hard Mode...")
            
            for attempt in range(max_attempts):
                GLOBAL_CACHE.Party.SetNormalMode()
                yield from Routines.Yield.wait(Timing.HARD_MODE_TOGGLE)
                
                # Verify it worked
                if not GLOBAL_CACHE.Party.IsHardMode():
                    self._log("Normal Mode enabled.")
                    return True
                
                if attempt < max_attempts - 1:
                    self._log(f"Normal Mode toggle failed, retrying... ({attempt + 1}/{max_attempts})", warning=True)
            
            # This shouldn't really fail, but handle it
            self._log("Failed to disable Hard Mode!", error=True)
            return False
        
        return True

    def _get_party_size(self) -> int:
        """Get maximum party size for current map."""
        try:
            return GLOBAL_CACHE.Map.GetMaxPartySize()
        except:
            return 8

    def _get_mandatory_heroes(self, bot, game_mode: GameMode) -> list:
        """Get mandatory hero requirements for current task."""
        if not bot.executor.current_task:
            return []
        try:
            from models.requirements import TaskRequirementsAccessor
            task_info = bot.executor.current_task.get_info()
            accessor = TaskRequirementsAccessor(task_info)
            return accessor.get_hero_requirements_for_mode(game_mode)
        except:
            return []

    def _get_mission_name(self, bot) -> str:
        """Get name of current mission for hero assignments."""
        if bot.executor.current_task:
            return bot.executor.current_task.name
        return ""

    def _log(self, message: str, warning: bool = False, error: bool = False):
        """Log a message with appropriate level."""
        if error:
            level = Py4GW.Console.MessageType.Error
        elif warning:
            level = Py4GW.Console.MessageType.Warning
        else:
            level = Py4GW.Console.MessageType.Info
        
        Py4GW.Console.Log("Transition", message, level)

    # ==================
    # LEGACY COMPATIBILITY
    # ==================
    
    def wait_for_map_load(self):
        """Legacy method - use _wait_until_map_ready instead."""
        yield from self._wait_until_map_ready()
    
    def wait_for_mission_load(self):
        """Legacy method - use _wait_until_map_ready instead."""
        yield from self._wait_until_map_ready()
    
    def move_to_interact_and_dialog(self, npc_id: int, dialog_id: int, x: float = 0, y: float = 0, log_message: str = None):
        """Legacy method for NPC interaction with dialog."""
        if log_message:
            self._log(log_message)
        
        yield from self.bot.interaction.move_to_and_interact(npc_id, x, y)
        
        # Wait for dialog window to open
        yield from Routines.Yield.wait(Timing.NPC_DIALOG_OPEN_DELAY)
        
        self._log("Sending dialog...")
        Player.SendDialog(dialog_id)
        
        # Wait for mission countdown
        yield from Routines.Yield.wait(Timing.MISSION_COUNTDOWN_WAIT)
        yield from self._wait_until_map_ready(expect_map_change=True)

    # Legacy aliases
    def TravelTo(self, map_id: int):
        yield from self.travel_to(map_id)
    
    def SetupMission(self, bot, use_hard_mode: bool = False):
        yield from self.setup_mission(bot, use_hard_mode)