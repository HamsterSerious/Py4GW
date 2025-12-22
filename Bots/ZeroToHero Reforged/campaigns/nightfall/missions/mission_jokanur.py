"""
Mission: Jokanur Diggings
Campaign: Nightfall

Investigate the ruins of Fahranur, The First City with Kormir.
This is the second mission in the Nightfall campaign.

Trials:
1. Kill Darehk the Quick
2. Retrieve Stone Tablets (avoid Ghostly Sunspears - pacifist zone)
3. Escort Kadash
4. Kill Apocryphia

DECLARATIVE PATTERN:
Complex logic (pacifist mode, escort) uses AddCustomState() with generators.
"""
from core.base_task import BaseTask
from models.task import TaskInfo
from models.loadout import LoadoutConfig, MandatoryLoadout, HeroRequirement
from data.enums import TaskType
from Py4GWCoreLib.enums_src.Hero_enums import HeroType


class MissionJokanur(BaseTask):
    """Jokanur Diggings - Second Nightfall mission."""
    
    INFO = TaskInfo(
        name="Jokanur Diggings",
        description="Investigate the ruins of Fahranur with Kormir to find what is killing the workers.",
        task_type=TaskType.MISSION,
        loadout=LoadoutConfig(
            normal_mode=MandatoryLoadout(
                required_heroes=[
                    HeroRequirement(hero_id=HeroType.Melonni.value, role="Mandatory", build="Any")
                ],
                notes="Melonni is mandatory for this mission."
            ),
            hard_mode=MandatoryLoadout(
                required_heroes=[
                    HeroRequirement(hero_id=HeroType.Melonni.value, role="Mandatory", build="Any")
                ],
                notes="Melonni is mandatory for this mission."
            )
        )
    )
    
    # ==================
    # MISSION CONSTANTS
    # ==================
    
    # Map IDs
    MAP_ID_OUTPOST = 491
    MAP_ID_COMPLETION = 449  # Kamadan
    
    # NPCs
    NPC_GATAH_MODEL = 4712
    NPC_GATAH_POS = (2888.00, 2207.00)
    DIALOG_START = 0x84
    
    # Items
    ITEM_STONE_TABLET = 17055
    
    # Gadgets (Pedestals)
    GADGET_PEDESTAL_1 = 6472  # After Trial 1
    GADGET_PEDESTAL_2 = 6475  # Trial 2 - first pedestal
    GADGET_PEDESTAL_3 = 6474  # Trial 2 - second pedestal
    
    # NPCs for escort
    NPC_KADASH_MODEL = 5546
    
    # Hero Behavior Constants
    HERO_FIGHT = 0
    HERO_GUARD = 1
    HERO_AVOID = 2
    
    # ==================
    # PATHS
    # ==================
    
    PATH_TO_RUINS = [
        (15590.30, 13267.24),
        (12465.50, 13480.69),
        (11329.49, 15380.10),
        (10470.48, 18107.08),
        (7927.25, 18685.61),
        (5945.47, 17288.90),
        (2793.44, 16898.92),
    ]
    
    # Gate positions
    GATE_POSITION = (-155.00, 14430.16)
    AFTER_GATE_POSITION = (-1505.30, 14471.92)
    
    # Trial 1 - Darehk
    PATH_TO_DAREHK = [(-1505.30, 14471.92)]
    
    # Pedestal 1 position
    PEDESTAL_1_POSITION = (-5934.00, 11249.00)
    
    # Trial 2 - Tablets (PACIFIST ZONE)
    TABLET1_SEARCH_POS = (-9297.15, 11574.76)
    TABLET1_DROP_POS = (-11461.18, 6657.43)
    
    PATH_TO_TABLET2 = [
        (-12266.74, 9621.60),
        (-12411.94, 11786.64),
    ]
    TABLET2_SEARCH_POS = (-12411.94, 11786.64)
    
    PATH_TRIAL2_RETURN = [
        (-12266.74, 9621.60),
        (-11965.52, 6699.59),
    ]
    
    # Trial 3 - Escort
    PATH_TO_KADASH = [
        (-11736.30, 4717.63),
        (-10536.60, 3467.35),
    ]
    KADASH_START_POS = (-10251.00, 1900.00)
    
    PATH_ESCORT_KADASH = [
        (-13053.12, -25.67),
        (-14305.06, -1096.00),
        (-13181.52, -2499.05),
        (-10578.11, -1752.13),
    ]
    
    # Final boss
    PATH_TO_APOCRYPHIA = [
        (-7427.13, -1588.05),
        (-7122.81, -3812.74),
        (-6315.41, -1475.75),
        (-3039.00, -1701.00),
    ]

    # ==================
    # BUILD ROUTINE (Declarative)
    # ==================

    def build_routine(self, bot) -> None:
        """Build the mission routine declaratively."""
        
        # === SETUP ===
        bot.States.AddHeader("Setup - Travel & Team")
        
        bot.Map.Travel(target_map_id=self.MAP_ID_OUTPOST)
        bot.Wait.ForMapLoad(target_map_id=self.MAP_ID_OUTPOST)
        
        bot.States.AddCustomState(
            lambda: self._setup_team_and_mode(bot),
            "Configure Team & Mode"
        )
        
        # === ENTER MISSION ===
        bot.States.AddHeader("Enter Mission")
        
        bot.Move.XY(self.NPC_GATAH_POS[0], self.NPC_GATAH_POS[1])
        bot.Dialogs.AtXY(self.NPC_GATAH_POS[0], self.NPC_GATAH_POS[1], self.DIALOG_START)
        bot.Wait.UntilOnExplorable()
        bot.Wait.ForTime(2000)
        
        bot.Templates.Aggressive()
        
        # === PHASE 1: Travel to Ancient Ruins ===
        bot.States.AddHeader("Travel to Ancient Ruins")
        
        for x, y in self.PATH_TO_RUINS:
            bot.Move.XY(x, y)
        
        # Wait at gate (custom state handles gate logic)
        bot.States.AddCustomState(
            lambda: self._wait_for_gate(bot),
            "Wait for Gate"
        )
        
        # === PHASE 2: Trial 1 - Kill Darehk ===
        bot.States.AddHeader("Trial 1: Defeat Darehk the Quick")
        
        for x, y in self.PATH_TO_DAREHK:
            bot.Move.XY(x, y)
        
        bot.Wait.UntilOutOfCombat()
        
        # Pick up stone tablet from Darehk
        bot.States.AddCustomState(
            lambda: self._pickup_tablet(bot),
            "Pickup Stone Tablet"
        )
        
        # Move to pedestal and use tablet
        bot.Move.XY(self.PEDESTAL_1_POSITION[0], self.PEDESTAL_1_POSITION[1])
        bot.Interact.WithGadgetID(self.GADGET_PEDESTAL_1)
        bot.Wait.ForTime(1000)
        
        # === PHASE 3: Trial 2 - Retrieve Stone Tablets (PACIFIST) ===
        bot.States.AddHeader("Trial 2: Retrieve Stone Tablets")
        
        # Enter pacifist mode
        bot.States.AddCustomState(
            lambda: self._set_pacifist_mode(bot, True),
            "Enable Pacifist Mode"
        )
        bot.Templates.Pacifist()
        
        # Tablet 1: Pick up and carry to drop position
        bot.Move.XY(self.TABLET1_SEARCH_POS[0], self.TABLET1_SEARCH_POS[1])
        bot.States.AddCustomState(
            lambda: self._pickup_tablet(bot),
            "Pickup Tablet 1"
        )
        
        bot.Move.XY(self.TABLET1_DROP_POS[0], self.TABLET1_DROP_POS[1])
        bot.States.AddCustomState(
            lambda: self._drop_bundle(bot),
            "Drop Tablet 1"
        )
        
        # Tablet 2: Pick up from different area
        for x, y in self.PATH_TO_TABLET2:
            bot.Move.XY(x, y)
        
        bot.States.AddCustomState(
            lambda: self._pickup_tablet(bot),
            "Pickup Tablet 2"
        )
        
        # Return with tablet 2
        for x, y in self.PATH_TRIAL2_RETURN:
            bot.Move.XY(x, y)
        
        # Use tablet on pedestal 2
        bot.Interact.WithGadgetID(self.GADGET_PEDESTAL_2)
        bot.Wait.ForTime(1000)
        
        # Pick up dropped tablet and use on pedestal 3
        bot.States.AddCustomState(
            lambda: self._pickup_tablet(bot),
            "Pickup Dropped Tablet"
        )
        bot.Interact.WithGadgetID(self.GADGET_PEDESTAL_3)
        bot.Wait.ForTime(1000)
        
        # Exit pacifist mode
        bot.States.AddCustomState(
            lambda: self._set_pacifist_mode(bot, False),
            "Disable Pacifist Mode"
        )
        bot.Templates.Aggressive()
        
        # === PHASE 4: Trial 3 - Escort Kadash ===
        bot.States.AddHeader("Trial 3: Escort Kadash")
        
        for x, y in self.PATH_TO_KADASH:
            bot.Move.XY(x, y)
        
        bot.Move.XY(self.KADASH_START_POS[0], self.KADASH_START_POS[1])
        
        # Escort Kadash (complex - custom state)
        bot.States.AddCustomState(
            lambda: self._escort_kadash(bot),
            "Escort Kadash"
        )
        
        # Wait for cutscene after escort
        bot.States.AddCustomState(
            lambda: self._skip_cinematic(bot),
            "Skip Cutscene"
        )
        
        # === PHASE 5: Final Boss - Apocryphia ===
        bot.States.AddHeader("Defeat Apocryphia")
        
        for x, y in self.PATH_TO_APOCRYPHIA:
            bot.Move.XY(x, y)
        
        bot.Wait.UntilOutOfCombat()
        
        # === MISSION COMPLETE ===
        bot.States.AddHeader("Mission Complete")
        
        bot.States.AddCustomState(
            lambda: self._skip_cinematic(bot),
            "Skip Final Cutscene"
        )
        
        bot.Wait.ForMapToChange(target_map_id=self.MAP_ID_COMPLETION)

    # ==================
    # CUSTOM STATE GENERATORS
    # ==================
    
    def _setup_team_and_mode(self, bot):
        """Generator for team setup and hard mode configuration."""
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Routines
        
        current_hm = GLOBAL_CACHE.Party.IsHardMode()
        
        if self.use_hard_mode and not current_hm:
            GLOBAL_CACHE.Party.SetHardMode()
            yield from Routines.Yield.wait(1500)
        elif not self.use_hard_mode and current_hm:
            GLOBAL_CACHE.Party.SetNormalMode()
            yield from Routines.Yield.wait(1500)
        
        party_size = GLOBAL_CACHE.Map.GetMaxPartySize()
        mode_str = "HM" if self.use_hard_mode else "NM"
        
        yield from bot.team_manager.load_team(party_size, mode_str)
        yield
    
    def _wait_for_gate(self, bot):
        """Generator to wait for gate to open."""
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Routines, Player, Utils
        import time
        
        target = self.AFTER_GATE_POSITION
        max_wait = 300  # 5 minutes max
        retry_interval = 5  # seconds
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Try to move to target
            Player.Move(target[0], target[1])
            
            # Track progress
            best_dist = Utils.Distance(Player.GetXY(), target)
            last_progress = time.time()
            
            while True:
                my_pos = Player.GetXY()
                current_dist = Utils.Distance(my_pos, target)
                
                # Arrived?
                if current_dist < 150:
                    return
                
                # Made progress?
                if current_dist < best_dist - 10:
                    best_dist = current_dist
                    last_progress = time.time()
                
                # Stuck for 3 seconds?
                if time.time() - last_progress > 3.0:
                    # Gate probably closed, wait and retry
                    Player.CancelMove()
                    yield from Routines.Yield.wait(retry_interval * 1000)
                    break
                
                yield from Routines.Yield.wait(100)
        
        yield
    
    def _pickup_tablet(self, bot):
        """Generator to pick up a stone tablet."""
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Routines, Player
        
        # Find tablet in item array
        items = GLOBAL_CACHE.AgentArray.GetItemArray()
        my_pos = Player.GetXY()
        
        for agent_id in items:
            try:
                model_id = GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id)
                if model_id == self.ITEM_STONE_TABLET:
                    # Pick it up
                    Player.PickUpItem(agent_id)
                    yield from Routines.Yield.wait(1000)
                    return
            except:
                continue
        
        yield from Routines.Yield.wait(500)
        yield
    
    def _drop_bundle(self, bot):
        """Generator to drop held bundle."""
        from Py4GWCoreLib import Routines
        
        yield from Routines.Yield.Keybinds.DropBundle()
        yield from Routines.Yield.wait(500)
        yield
    
    def _set_pacifist_mode(self, bot, enable: bool):
        """Generator to set hero behavior for pacifist zone."""
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Routines
        import Py4GW
        
        behavior = self.HERO_AVOID if enable else self.HERO_GUARD
        behavior_name = "Avoid" if enable else "Guard"
        
        try:
            heroes = GLOBAL_CACHE.Party.GetHeroes()
            for hero in heroes:
                GLOBAL_CACHE.Party.Heroes.SetHeroBehavior(hero.agent_id, behavior)
            
            Py4GW.Console.Log(
                "MissionJokanur",
                f"Set all heroes to {behavior_name} mode",
                Py4GW.Console.MessageType.Info
            )
        except Exception as e:
            Py4GW.Console.Log(
                "MissionJokanur",
                f"Error setting hero behavior: {e}",
                Py4GW.Console.MessageType.Warning
            )
        
        yield from Routines.Yield.wait(100)
        yield
    
    def _escort_kadash(self, bot):
        """Generator to escort Kadash along path."""
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Routines, Player, Utils
        import Py4GW
        
        max_distance = 500
        
        def find_kadash():
            """Find Kadash by model ID."""
            try:
                allies = GLOBAL_CACHE.AgentArray.GetAllyArray()
                for agent_id in allies:
                    if GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id) == self.NPC_KADASH_MODEL:
                        return agent_id
                npcs = GLOBAL_CACHE.AgentArray.GetNPCArray()
                for agent_id in npcs:
                    if GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id) == self.NPC_KADASH_MODEL:
                        return agent_id
            except:
                pass
            return 0
        
        for target_x, target_y in self.PATH_ESCORT_KADASH:
            target = (target_x, target_y)
            
            while True:
                if GLOBAL_CACHE.Map.IsMapLoading():
                    return
                
                # Check Kadash distance
                kadash_id = find_kadash()
                if kadash_id == 0:
                    yield from Routines.Yield.wait(1000)
                    continue
                
                my_pos = Player.GetXY()
                kadash_pos = GLOBAL_CACHE.Agent.GetXY(kadash_id)
                kadash_dist = Utils.Distance(my_pos, kadash_pos)
                target_dist = Utils.Distance(my_pos, target)
                
                # Arrived at waypoint?
                if target_dist < 150:
                    break
                
                # Too far from Kadash?
                if kadash_dist > max_distance:
                    Player.CancelMove()
                    # Wait for Kadash
                    while kadash_dist > max_distance * 0.7:
                        yield from Routines.Yield.wait(200)
                        kadash_id = find_kadash()
                        if kadash_id == 0:
                            break
                        kadash_pos = GLOBAL_CACHE.Agent.GetXY(kadash_id)
                        kadash_dist = Utils.Distance(Player.GetXY(), kadash_pos)
                
                # Move toward target
                Player.Move(target_x, target_y)
                yield from Routines.Yield.wait(100)
        
        Py4GW.Console.Log("MissionJokanur", "Escort complete!", Py4GW.Console.MessageType.Info)
        yield
    
    def _skip_cinematic(self, bot):
        """Generator to skip cinematics."""
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Routines
        
        # Wait briefly for cinematic to potentially start
        yield from Routines.Yield.wait(2000)
        
        # Check if in cinematic and skip
        for _ in range(10):  # Try a few times
            if GLOBAL_CACHE.Map.IsInCinematic():
                GLOBAL_CACHE.Map.SkipCinematic()
                yield from Routines.Yield.wait(500)
            else:
                break
            yield from Routines.Yield.wait(500)
        
        yield from Routines.Yield.wait(500)
        yield