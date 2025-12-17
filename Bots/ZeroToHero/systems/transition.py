"""
Transition System - Handles map travel and mission setup.

Provides:
- Travel to maps
- Mission/team setup with HM/NM handling
- NPC interaction for mission entry
"""
import Py4GW
from Py4GWCoreLib import Routines
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from data.enums import GameMode
from data.timing import Timing
from models.requirements import TaskRequirementsAccessor


class Transition:
    """
    Handles transitions between maps and mission setup.
    """
    
    def __init__(self):
        pass
    
    def travel_to(self, map_id: int):
        """
        Handles traveling to a map. Disbands party to avoid issues.
        
        Args:
            map_id: Target map ID to travel to
            
        Yields for coroutine execution.
        """
        # Disband party before travel
        if GLOBAL_CACHE.Party.GetPartySize() > 1:
            Py4GW.Console.Log(
                "Transition", 
                "Disbanding party before travel...", 
                Py4GW.Console.MessageType.Info
            )
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            yield from Routines.Yield.wait(Timing.MAP_LOAD_BUFFER)
        
        # Check if already at destination
        current_map = GLOBAL_CACHE.Map.GetMapID()
        if current_map == map_id:
            Py4GW.Console.Log(
                "Transition", 
                f"Already at map {map_id}", 
                Py4GW.Console.MessageType.Info
            )
            return
        
        Py4GW.Console.Log(
            "Transition", 
            f"Traveling to Map ID: {map_id}", 
            Py4GW.Console.MessageType.Info
        )
        
        GLOBAL_CACHE.Map.Travel(map_id)
        yield from Routines.Yield.wait(Timing.MAP_TRAVEL_INITIAL)
        
        # Wait for map to be ready
        while not GLOBAL_CACHE.Map.IsMapReady():
            yield from Routines.Yield.wait(Timing.MAP_READY_POLL)
        
        yield from Routines.Yield.wait(Timing.MAP_LOAD_BUFFER)
    
    def setup_mission(self, bot, use_hard_mode: bool = False):
        """
        Sets up the team based on the current mission settings.
        Handles HM toggling and team loading with mandatory heroes.
        
        Args:
            bot: The bot instance
            use_hard_mode: Whether to set Hard Mode
            
        Yields for coroutine execution.
        """
        game_mode = GameMode.from_bool(use_hard_mode)
        
        # Handle Hard Mode Toggle
        yield from self._sync_hard_mode(use_hard_mode)
        
        # Determine Party Size from game
        party_size = self._get_party_size()
        
        # Get mandatory heroes from current task
        mandatory_list = self._get_mandatory_heroes(bot, game_mode)
        mission_name = self._get_mission_name(bot)
        
        # Load Team
        if mandatory_list:
            Py4GW.Console.Log(
                "Transition", 
                f"Loading team with {len(mandatory_list)} mandatory hero(es)", 
                Py4GW.Console.MessageType.Info
            )
            yield from bot.team_manager.load_team_with_mandatory_heroes(
                party_size, 
                game_mode.value,
                mandatory_list,
                mission_name=mission_name
            )
        else:
            yield from bot.team_manager.load_team(party_size, game_mode.value)
    
    def move_to_and_interact(self, bot, npc_id: int):
        """
        Moves to an NPC and interacts.
        
        Args:
            bot: The bot instance
            npc_id: Agent ID of the NPC to interact with
            
        Yields for coroutine execution.
        """
        Py4GW.Console.Log(
            "Transition", 
            f"Approaching NPC {npc_id}...", 
            Py4GW.Console.MessageType.Info
        )
        
        GLOBAL_CACHE.Player.ChangeTarget(npc_id)
        GLOBAL_CACHE.Player.MoveToTarget(npc_id)
        
        # Wait for movement
        yield from Routines.Yield.wait(Timing.MEDIUM_DELAY)
        while GLOBAL_CACHE.Player.IsMoving():
            yield from Routines.Yield.wait(Timing.MOVEMENT_POLL)
        
        GLOBAL_CACHE.Player.Interact(npc_id)
        yield from Routines.Yield.wait(Timing.INTERACT_DELAY)
    
    def enter_mission(self, bot):
        """
        Wait for mission entry after interacting with NPC.
        Use this after move_to_and_interact with a mission NPC.
        
        Yields for coroutine execution.
        """
        Py4GW.Console.Log(
            "Transition", 
            "Waiting for mission load...", 
            Py4GW.Console.MessageType.Info
        )
        
        yield from Routines.Yield.wait(Timing.MISSION_LOAD_INITIAL)
        
        while not GLOBAL_CACHE.Map.IsMapReady():
            yield from Routines.Yield.wait(Timing.MAP_READY_POLL)
        
        yield from Routines.Yield.wait(Timing.MAP_LOAD_BUFFER)
        
        Py4GW.Console.Log(
            "Transition", 
            "Mission loaded.", 
            Py4GW.Console.MessageType.Success
        )
    
    # ==================
    # PRIVATE HELPERS
    # ==================
    
    def _sync_hard_mode(self, use_hard_mode: bool):
        """Synchronize game's hard mode setting with desired mode."""
        is_hm = GLOBAL_CACHE.Party.IsHardMode()
        
        if use_hard_mode and not is_hm:
            Py4GW.Console.Log(
                "Transition", 
                "Switching to Hard Mode...", 
                Py4GW.Console.MessageType.Info
            )
            GLOBAL_CACHE.Party.SetHardMode(True)
            yield from Routines.Yield.wait(Timing.HARD_MODE_TOGGLE)
        elif not use_hard_mode and is_hm:
            Py4GW.Console.Log(
                "Transition", 
                "Switching to Normal Mode...", 
                Py4GW.Console.MessageType.Info
            )
            GLOBAL_CACHE.Party.SetHardMode(False)
            yield from Routines.Yield.wait(Timing.HARD_MODE_TOGGLE)
    
    def _get_party_size(self) -> int:
        """Get the maximum party size for current map."""
        try:
            party_size = GLOBAL_CACHE.Map.GetMaxPartySize()
            Py4GW.Console.Log(
                "Transition", 
                f"Max party size for this map: {party_size}", 
                Py4GW.Console.MessageType.Info
            )
            return party_size
        except Exception as e:
            Py4GW.Console.Log(
                "Transition", 
                f"Failed to get party size, defaulting to 8: {e}", 
                Py4GW.Console.MessageType.Warning
            )
            return 8
    
    def _get_mandatory_heroes(self, bot, game_mode: GameMode) -> list:
        """
        Extract mandatory hero requirements from current task.
        
        Uses TaskRequirementsAccessor for clean access.
        
        Returns:
            List of HeroRequirements (empty if none)
        """
        if not bot.executor.current_task:
            return []
        
        try:
            task_info = bot.executor.current_task.get_info()
            accessor = TaskRequirementsAccessor(task_info)
            return accessor.get_hero_requirements_for_mode(game_mode)
        except Exception as e:
            Py4GW.Console.Log(
                "Transition", 
                f"Error reading mandatory heroes: {e}", 
                Py4GW.Console.MessageType.Warning
            )
            return []
    
    def _get_mission_name(self, bot) -> str:
        """Get the name of the current mission/task."""
        if bot.executor.current_task:
            return bot.executor.current_task.name
        return ""
    
    # ==================
    # LEGACY ALIASES
    # ==================
    
    def TravelTo(self, map_id: int):
        """Legacy method name - use travel_to() instead."""
        yield from self.travel_to(map_id)
    
    def SetupMission(self, bot, use_hard_mode: bool = False):
        """Legacy method name - use setup_mission() instead."""
        yield from self.setup_mission(bot, use_hard_mode)
    
    def MoveToAndInteract(self, bot, npc_id: int):
        """Legacy method name - use move_to_and_interact() instead."""
        yield from self.move_to_and_interact(bot, npc_id)
    
    def EnterMission(self, bot):
        """Legacy method name - use enter_mission() instead."""
        yield from self.enter_mission(bot)
