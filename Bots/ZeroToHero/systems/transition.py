import Py4GW
from Py4GWCoreLib import *
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

class Transition:
    def __init__(self):
        pass

    def TravelTo(self, map_id):
        """
        Handles traveling to a map. Disbands party to avoid issues.
        """
        if GLOBAL_CACHE.Party.GetPartySize() > 1:
            Py4GW.Console.Log("Transition", "Disbanding party before travel...", Py4GW.Console.MessageType.Info)
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            yield from Routines.Yield.wait(1000)

        Py4GW.Console.Log("Transition", f"Traveling to Map ID: {map_id}", Py4GW.Console.MessageType.Info)
        if GLOBAL_CACHE.Map.GetMapID() == map_id:
            return

        GLOBAL_CACHE.Map.Travel(map_id)
        yield from Routines.Yield.wait(2000)
        
        while not GLOBAL_CACHE.Map.IsMapReady():
            yield from Routines.Yield.wait(500)
            
        yield from Routines.Yield.wait(1000)

    def SetupMission(self, bot, use_hard_mode=False):
        """
        Sets up the team based on the current campaign/mission settings.
        Handles HM toggling and Team Loading.
        """
        # 1. Handle Hard Mode Toggle
        is_hm = GLOBAL_CACHE.Party.IsHardMode()
        if use_hard_mode and not is_hm:
            Py4GW.Console.Log("Transition", "Switching to Hard Mode...", Py4GW.Console.MessageType.Info)
            GLOBAL_CACHE.Party.SetHardMode(True)
            yield from Routines.Yield.wait(1000)
        elif not use_hard_mode and is_hm:
            Py4GW.Console.Log("Transition", "Switching to Normal Mode...", Py4GW.Console.MessageType.Info)
            GLOBAL_CACHE.Party.SetHardMode(False)
            yield from Routines.Yield.wait(1000)

        # 2. Determine Party Size & Mode String
        party_size = 4 # Default
        try:
            # Map specific party size logic could go here or be fetched from map data
            # For now assuming standard outpost limits or passed via config
            # Actually, let's just use the max party size of the current map? 
            # Or usually missions imply size. 
            # Let's try to detect from map or default to 8 for now if unknown.
            # In a real scenario, map_id to size mapping is best.
            party_size = 8 # Placeholder, ideally Map.GetMaxPartySize() if available
        except:
            pass

        mode_str = "HM" if use_hard_mode else "NM"
        
        # 3. Retrieve Mandatory Heroes from Task Info
        mandatory_list = []
        try:
            if bot.current_task_instance:
                info = bot.current_task_instance.GetInfo()
                mandatory_data = info.get("Mandatory_Loadout", {})
                
                # Check specific mode requirements
                if mode_str in mandatory_data:
                    reqs = mandatory_data[mode_str]
                    if "Required_Heroes" in reqs:
                        mandatory_list = reqs["Required_Heroes"]
        except Exception as e:
            Py4GW.Console.Log("Transition", f"Error reading mandatory heroes: {e}", Py4GW.Console.MessageType.Warning)

        # 4. Load Team
        if mandatory_list:
            yield from bot.team_manager.LoadTeamWithMandatoryHeroes(
                party_size, 
                mode_str, 
                mandatory_list,
                mission_name=bot.current_task_instance.name # Pass mission name for strategy hero lookup
            )
        else:
            yield from bot.team_manager.LoadTeam(party_size, mode_str)

    def MoveToAndInteract(self, bot, npc_id):
        """
        Moves to an NPC and interacts.
        """
        Py4GW.Console.Log("Transition", f"Approaching NPC {npc_id}...", Py4GW.Console.MessageType.Info)
        
        GLOBAL_CACHE.Player.ChangeTarget(npc_id)
        GLOBAL_CACHE.Player.MoveToTarget(npc_id)
        
        # Wait for movement
        yield from Routines.Yield.wait(500)
        while GLOBAL_CACHE.Player.IsMoving():
            yield from Routines.Yield.wait(100)
            
        GLOBAL_CACHE.Player.Interact(npc_id)
        yield from Routines.Yield.wait(1000)