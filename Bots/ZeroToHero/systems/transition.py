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


class Transition:
    """
    Handles transitions between maps and mission setup.
    """
    
    def __init__(self):
        pass

    def TravelTo(self, map_id):
        """
        Handles traveling to a map. Disbands party to avoid issues.
        
        Args:
            map_id: Target map ID to travel to
        """
        if GLOBAL_CACHE.Party.GetPartySize() > 1:
            Py4GW.Console.Log(
                "Transition", 
                "Disbanding party before travel...", 
                Py4GW.Console.MessageType.Info
            )
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            yield from Routines.Yield.wait(1000)

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
        yield from Routines.Yield.wait(2000)
        
        while not GLOBAL_CACHE.Map.IsMapReady():
            yield from Routines.Yield.wait(500)
            
        yield from Routines.Yield.wait(1000)

    def SetupMission(self, bot, use_hard_mode=False):
        """
        Sets up the team based on the current mission settings.
        Handles HM toggling and team loading with mandatory heroes.
        
        Args:
            bot: The bot instance
            use_hard_mode: Whether to set Hard Mode
        """
        game_mode = GameMode.from_bool(use_hard_mode)
        
        # 1. Handle Hard Mode Toggle
        yield from self._sync_hard_mode(use_hard_mode)

        # 2. Determine Party Size from game
        party_size = self._get_party_size()

        # 3. Get mandatory heroes from current task
        mandatory_list = self._get_mandatory_heroes(bot, game_mode)
        mission_name = self._get_mission_name(bot)

        # 4. Load Team
        if mandatory_list:
            Py4GW.Console.Log(
                "Transition", 
                f"Loading team with {len(mandatory_list)} mandatory hero(es)", 
                Py4GW.Console.MessageType.Info
            )
            yield from bot.team_manager.LoadTeamWithMandatoryHeroes(
                party_size, 
                game_mode.value,  # "NM" or "HM"
                mandatory_list,
                mission_name=mission_name
            )
        else:
            yield from bot.team_manager.LoadTeam(party_size, game_mode.value)

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
            yield from Routines.Yield.wait(1000)
        elif not use_hard_mode and is_hm:
            Py4GW.Console.Log(
                "Transition", 
                "Switching to Normal Mode...", 
                Py4GW.Console.MessageType.Info
            )
            GLOBAL_CACHE.Party.SetHardMode(False)
            yield from Routines.Yield.wait(1000)

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
        
        Returns list of hero requirement dicts for backward compatibility
        with team_manager.
        """
        if not bot.current_task_instance:
            return []
        
        try:
            # Try new-style get_info() first
            if hasattr(bot.current_task_instance, 'get_info'):
                info = bot.current_task_instance.get_info()
                
                if info.loadout:
                    loadout = info.loadout.get_for_mode(game_mode)
                    if loadout and loadout.required_heroes:
                        # Convert HeroRequirement dataclasses to dicts for compatibility
                        return [
                            {
                                "HeroID": h.hero_id,
                                "Role": h.role,
                                "Build": h.build,
                                "Expected_Skills": h.expected_skills,
                                "Equipment": h.equipment,
                                "Weapons": h.weapons
                            }
                            for h in loadout.required_heroes
                        ]
            
            # Fall back to legacy GetInfo() method
            legacy_info = bot.current_task_instance.GetInfo()
            mandatory_data = legacy_info.get("Mandatory_Loadout", {})
            
            mode_str = game_mode.value  # "NM" or "HM"
            if mode_str in mandatory_data:
                reqs = mandatory_data[mode_str]
                if "Required_Heroes" in reqs:
                    return reqs["Required_Heroes"]
                    
        except Exception as e:
            Py4GW.Console.Log(
                "Transition", 
                f"Error reading mandatory heroes: {e}", 
                Py4GW.Console.MessageType.Warning
            )
        
        return []

    def _get_mission_name(self, bot) -> str:
        """Get the name of the current mission/task."""
        if bot.current_task_instance:
            return bot.current_task_instance.name
        return ""

    def MoveToAndInteract(self, bot, npc_id):
        """
        Moves to an NPC and interacts.
        
        Args:
            bot: The bot instance
            npc_id: Agent ID of the NPC to interact with
        """
        Py4GW.Console.Log(
            "Transition", 
            f"Approaching NPC {npc_id}...", 
            Py4GW.Console.MessageType.Info
        )
        
        GLOBAL_CACHE.Player.ChangeTarget(npc_id)
        GLOBAL_CACHE.Player.MoveToTarget(npc_id)
        
        # Wait for movement
        yield from Routines.Yield.wait(500)
        while GLOBAL_CACHE.Player.IsMoving():
            yield from Routines.Yield.wait(100)
            
        GLOBAL_CACHE.Player.Interact(npc_id)
        yield from Routines.Yield.wait(1000)

    def EnterMission(self, bot):
        """
        Wait for mission entry after interacting with NPC.
        Use this after MoveToAndInteract with a mission NPC.
        """
        Py4GW.Console.Log(
            "Transition", 
            "Waiting for mission load...", 
            Py4GW.Console.MessageType.Info
        )
        
        yield from Routines.Yield.wait(2000)
        
        while not GLOBAL_CACHE.Map.IsMapReady():
            yield from Routines.Yield.wait(500)
        
        yield from Routines.Yield.wait(1000)
        
        Py4GW.Console.Log(
            "Transition", 
            "Mission loaded.", 
            Py4GW.Console.MessageType.Success
        )