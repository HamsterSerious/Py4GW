"""
Transition System - Handles map travel and mission setup.

Provides:
- Travel to maps
- Mission/team setup with HM/NM handling
- NPC interaction for mission entry
"""
import Py4GW
from Py4GWCoreLib import Routines, Player
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from data.enums import GameMode
from data.timing import Timing
from models.requirements import TaskRequirementsAccessor


class Transition:
    """
    Handles transitions between maps and mission setup.
    """
    
    def __init__(self, bot):
        self.bot = bot

    @property
    def is_outpost(self) -> bool:
        """Checks if current map is an outpost using Cache."""
        return GLOBAL_CACHE.Map.IsOutpost() 
    
    def travel_to(self, map_id: int):
        """
        Handles traveling to a map. Disbands party to avoid issues.
        """
        # Disband party before travel
        if GLOBAL_CACHE.Party.GetPartySize() > 1:
            Py4GW.Console.Log("Transition", "Disbanding party before travel...", Py4GW.Console.MessageType.Info)
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            yield from Routines.Yield.wait(Timing.MAP_LOAD_BUFFER)
        
        # Check if already at destination
        current_map = GLOBAL_CACHE.Map.GetMapID()
        if current_map == map_id:
            Py4GW.Console.Log("Transition", f"Already at map {map_id}", Py4GW.Console.MessageType.Info)
            return
        
        Py4GW.Console.Log("Transition", f"Traveling to Map ID: {map_id}", Py4GW.Console.MessageType.Info)
        
        GLOBAL_CACHE.Map.Travel(map_id)
        yield from self.wait_for_map_load()
    
    def wait_for_map_load(self):
        """
        Standard wait for map travel.
        Proactively waits for 'IsMapLoading' instead of just sleeping.
        """
        Py4GW.Console.Log("Transition", "Waiting for map load...", Py4GW.Console.MessageType.Info)
        
        # 1. Wait for Loading Screen to START
        attempts = 0
        max_attempts = 50 # 5 seconds
        loading_started = False
        
        while attempts < max_attempts:
            # Check if game entered loading state
            if GLOBAL_CACHE.Map.IsMapLoading(): 
                loading_started = True
                break
            
            yield from Routines.Yield.wait(100)
            attempts += 1
            
        if not loading_started:
            Py4GW.Console.Log("Transition", "Warning: Loading screen not detected (Fast load or lag?)", Py4GW.Console.MessageType.Warning)

        # 2. Wait for Loading Screen to FINISH
        while GLOBAL_CACHE.Map.IsMapLoading(): 
             yield from Routines.Yield.wait(Timing.MAP_READY_POLL)
             
        # 3. Wait for Map to be READY
        while not GLOBAL_CACHE.Map.IsMapReady(): 
            yield from Routines.Yield.wait(Timing.MAP_READY_POLL)
            
        yield from Routines.Yield.wait(Timing.MAP_LOAD_BUFFER)

    def wait_for_mission_load(self):
        """
        Specialized wait for mission entry.
        Handles cases where Map ID remains the same.
        """
        Py4GW.Console.Log("Transition", "Waiting for mission load...", Py4GW.Console.MessageType.Info)
        
        # 1. Wait for something to happen (Loading or Mode Change)
        max_attempts = 150 # 15 seconds
        attempts = 0
        loading_started = False
        
        while attempts < max_attempts:
            if GLOBAL_CACHE.Map.IsMapLoading(): 
                loading_started = True
                break
            
            if not self.is_outpost:
                loading_started = True
                break
                
            yield from Routines.Yield.wait(100)
            attempts += 1
            
        if not loading_started:
            Py4GW.Console.Log("Transition", "Warning: Timed out waiting for mission entry!", Py4GW.Console.MessageType.Warning)
        
        # 2. Wait for map to become ready again
        while GLOBAL_CACHE.Map.IsMapLoading():
            yield from Routines.Yield.wait(Timing.MAP_READY_POLL)
            
        while not GLOBAL_CACHE.Map.IsMapReady():
            yield from Routines.Yield.wait(Timing.MAP_READY_POLL)
            
        yield from Routines.Yield.wait(Timing.MAP_LOAD_BUFFER)
        Py4GW.Console.Log("Transition", "Mission loaded.", Py4GW.Console.MessageType.Success)

    def move_to_interact_and_dialog(self, npc_id: int, dialog_id: int, x: float = 0, y: float = 0, log_message: str = None):
        """
        Moves to NPC, Interacts, and sends Dialog.
        
        Args:
            log_message: Optional custom log for the action (e.g. "Starting Mission")
        """
        # 1. Approach and Interact
        if hasattr(self.bot, 'interaction'):
            yield from self.bot.interaction.move_to_and_interact(npc_id, x, y)
        else:
            # Fallback
            Py4GW.Console.Log("Transition", f"Approaching NPC {npc_id}...", Py4GW.Console.MessageType.Info)
            Player.ChangeTarget(npc_id)
            Player.MoveToTarget(npc_id)
            yield from Routines.Yield.wait(1000)
            
            while Player.IsMoving():
                 yield from Routines.Yield.wait(100)
            
            Player.CancelMove()
            yield from Routines.Yield.wait(200)

            GLOBAL_CACHE.Player.Interact(npc_id, True)
            yield from Routines.Yield.wait(1000)

        # 2. Send Dialog
        if log_message:
            Py4GW.Console.Log("Transition", log_message, Py4GW.Console.MessageType.Info)
        else:
            Py4GW.Console.Log("Transition", f"Sending Dialog {hex(dialog_id)}...", Py4GW.Console.MessageType.Info)
            
        Player.SendDialog(dialog_id)
        
        yield from Routines.Yield.wait(2000)
        
        # 3. Wait for load
        yield from self.wait_for_mission_load()
    
    def setup_mission(self, bot, use_hard_mode: bool = False):
        """Sets up the team based on the current mission settings."""
        game_mode = GameMode.from_bool(use_hard_mode)
        yield from self._sync_hard_mode(use_hard_mode)
        party_size = self._get_party_size()
        mandatory_list = self._get_mandatory_heroes(bot, game_mode)
        mission_name = self._get_mission_name(bot)
        
        if mandatory_list:
            Py4GW.Console.Log("Transition", f"Loading team with {len(mandatory_list)} mandatory hero(es)", Py4GW.Console.MessageType.Info)
            yield from bot.team_manager.load_team_with_mandatory_heroes(
                party_size, game_mode.value, mandatory_list, mission_name=mission_name
            )
        else:
            yield from bot.team_manager.load_team(party_size, game_mode.value)
    
    # ==================
    # PRIVATE HELPERS
    # ==================
    
    def _sync_hard_mode(self, use_hard_mode: bool):
        is_hm = GLOBAL_CACHE.Party.IsHardMode()
        if use_hard_mode and not is_hm:
            GLOBAL_CACHE.Party.SetHardMode() 
            yield from Routines.Yield.wait(Timing.HARD_MODE_TOGGLE)
        elif not use_hard_mode and is_hm:
            GLOBAL_CACHE.Party.SetNormalMode() 
            yield from Routines.Yield.wait(Timing.HARD_MODE_TOGGLE)
    
    def _get_party_size(self) -> int:
        try: return GLOBAL_CACHE.Map.GetMaxPartySize()
        except: return 8
        
    def _get_mandatory_heroes(self, bot, game_mode: GameMode) -> list:
        if not bot.executor.current_task: return []
        try:
            task_info = bot.executor.current_task.get_info()
            accessor = TaskRequirementsAccessor(task_info)
            return accessor.get_hero_requirements_for_mode(game_mode)
        except: return []
        
    def _get_mission_name(self, bot) -> str:
        if bot.executor.current_task: return bot.executor.current_task.name
        return ""
    
    def move_to_and_interact(self, bot, npc_id: int):
        if hasattr(self.bot, 'interaction'):
            yield from self.bot.interaction.move_to_and_interact(npc_id)
        else:
            GLOBAL_CACHE.Player.ChangeTarget(npc_id)
            GLOBAL_CACHE.Player.MoveToTarget(npc_id)
            yield from Routines.Yield.wait(Timing.MEDIUM_DELAY)
            while GLOBAL_CACHE.Player.IsMoving():
                yield from Routines.Yield.wait(Timing.MOVEMENT_POLL)
            GLOBAL_CACHE.Player.Interact(npc_id, True)
            yield from Routines.Yield.wait(Timing.INTERACT_DELAY)

    def enter_mission(self, bot):
        yield from self.wait_for_map_load()
        Py4GW.Console.Log("Transition", "Mission loaded.", Py4GW.Console.MessageType.Success)
    
    # ==================
    # LEGACY ALIASES
    # ==================
    def TravelTo(self, map_id: int): yield from self.travel_to(map_id)
    def SetupMission(self, bot, use_hard_mode: bool = False): yield from self.setup_mission(bot, use_hard_mode)
    def MoveToAndInteract(self, bot, npc_id: int): yield from self.move_to_interact_and_dialog(npc_id, 0)
    def EnterMission(self, bot): yield from self.enter_mission(bot)