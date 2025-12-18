"""
Mission: Jokanur Diggings
Campaign: Nightfall

Investigate the ruins of Fahranur, The First City with Kormir to find what is killing the workers.
This is the second mission in the Nightfall campaign.

Trials:
1. Kill Darehk the Quick
2. Retrieve Stone Tablets (avoid Ghostly Sunspears)
3. Escort Kadash
4. Kill Apocryphia
"""
from core.base_task import BaseTask
from models.task import TaskInfo
from models.loadout import LoadoutConfig, MandatoryLoadout, HeroRequirement
from data.enums import TaskType
from data.timing import Timing, Range
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib import Routines, Player, Utils
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
    MAP_ID_MISSION = 491  # Same as outpost - use IsOutpost/IsExplorable to differentiate
    MAP_ID_COMPLETION = 449  # Kamadan
    
    # NPCs
    NPC_GATAH_MODEL = 4712
    NPC_GATAH_POS = (2888.00, 2207.00)
    NPC_GATAH_APPROACH = (2171.93, -184.73)  # Walk here first if NPC not visible
    DIALOG_START = 0x84
    
    # Trial 1 - Darehk the Quick
    BOSS_DAREHK_MODEL = 5545  # NOTE: Same ModelID as Ghostly Sunspear!
    
    # Trial 2 - Stone Tablets
    ITEM_STONE_TABLET = 17055
    GADGET_PEDESTAL_1 = 6472  # After Trial 1
    GADGET_PEDESTAL_2 = 6475  # Trial 2 - first pedestal
    GADGET_PEDESTAL_3 = 6474  # Trial 2 - second pedestal
    
    # Ghostly Sunspear (same ModelID as Darehk - avoid attacking these!)
    ENEMY_GHOSTLY_SUNSPEAR = 5545
    PACIFIST_TRIGGER_RANGE = 1500
    
    # Trial 3 - Escort Kadash
    NPC_KADASH_MODEL = 5546
    ESCORT_MAX_DISTANCE = 500
    
    # Final Boss
    BOSS_APOCRYPHIA_MODEL = 4335
    
    # Hero Behavior Constants
    HERO_FIGHT = 0
    HERO_GUARD = 1
    HERO_AVOID = 2
    
    # ==================
    # PATHS
    # ==================
    
    # Path to Ancient Istani Ruins (before first gate)
    PATH_TO_RUINS = [
        (15590.30, 13267.24),
        (12465.50, 13480.69),
        (11329.49, 15380.10),
        (10470.48, 18107.08),
        (7927.25, 18685.61),
        (5945.47, 17288.90),
        (2793.44, 16898.92),
    ]
    
    # Gate position
    GATE_POSITION = (-155.00, 14430.16)
    AFTER_GATE_POSITION = (-1505.30, 14471.92)
    
    # Path to engage Darehk
    PATH_TO_DAREHK = [
        (-1505.30, 14471.92),
    ]
    DAREHK_ENGAGE_RANGE = 3000  # Extended range for this boss
    
    # Pedestal 1 position
    PEDESTAL_1_POSITION = (-5934.00, 11249.00)
    
    # Trial 2 paths
    PATH_TRIAL2_START = [
        (-9297.15, 11574.76),
    ]
    
    # Tablet 1: Pick up, carry to drop position
    TABLET1_SEARCH_POS = (-9297.15, 11574.76)
    TABLET1_DROP_POS = (-11461.18, 6657.43)
    
    # Tablet 2: Pick up from different area
    PATH_TO_TABLET2 = [
        (-12266.74, 9621.60),
        (-12411.94, 11786.64),
    ]
    TABLET2_SEARCH_POS = (-12411.94, 11786.64)
    
    # Return path with tablet 2
    PATH_TRIAL2_RETURN = [
        (-12266.74, 9621.60),
        (-11965.52, 6699.59),
    ]
    PEDESTAL_2_POSITION = (-11965.52, 6699.59)  # GadgetID 6475
    PEDESTAL_3_POSITION = (-11965.52, 6699.59)  # GadgetID 6474 (same area)
    
    # Trial 3 - Escort path
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
    
    # Final boss path
    PATH_TO_APOCRYPHIA = [
        (-7427.13, -1588.05),
        (-7122.81, -3812.74),
        (-6315.41, -1475.75),
        (-3039.00, -1701.00),
    ]
    APOCRYPHIA_POSITION = (-3039.00, -1701.00)

    # ==================
    # MAIN EXECUTION
    # ==================

    def execute(self, bot):
        """Main mission execution."""
        try:
            # === SETUP OBJECTIVES ===
            self.update_status("Initializing Jokanur Diggings...")
            
            obj_ruins = self.add_objective("Find the Ancient Ruins")
            obj_trial1 = self.add_objective("Trial 1: Defeat Darehk the Quick")
            obj_trial2 = self.add_objective("Trial 2: Retrieve Stone Tablets", total=2)
            obj_trial3 = self.add_objective("Trial 3: Escort Kadash")
            obj_boss = self.add_objective("Defeat Apocryphia")
            
            # === ENTER MISSION ===
            success = yield from bot.transition.enter_mission_from_outpost(
                outpost_map_id=self.MAP_ID_OUTPOST,
                npc_model_id=self.NPC_GATAH_MODEL,
                dialog_id=self.DIALOG_START,
                npc_position=self.NPC_GATAH_POS,
                use_hard_mode=self.use_hard_mode
            )
            
            if not success:
                self.update_status("Failed to enter mission!")
                self.failed = True
                return
            
            self.update_status("Mission Started!")
            
            # === PHASE 1: Travel to Ancient Ruins ===
            self.set_active_objective("Find the Ancient Ruins")
            self.update_status("Traveling to the Ancient Istani Ruins...")
            
            yield from bot.combat.move_and_clear_path(self.PATH_TO_RUINS)
            
            # Wait at gate
            self.update_status("Waiting for gate to open...")
            gate_success = yield from bot.movement.move_with_gate_check(
                self.AFTER_GATE_POSITION[0],
                self.AFTER_GATE_POSITION[1],
                stuck_timeout_sec=3.0,
                retry_delay_sec=5.0,
                status_callback=lambda msg: self.update_status(msg)
            )
            
            if not gate_success:
                self.update_status("Failed to pass through gate!")
                self.failed = True
                return
            
            self.complete_objective("Find the Ancient Ruins")
            
            # === PHASE 2: Trial 1 - Kill Darehk the Quick ===
            self.set_active_objective("Trial 1: Defeat Darehk the Quick")
            self.update_status("Hunting Darehk the Quick...")
            
            killed = yield from bot.combat.hunt_target_along_path(
                path=self.PATH_TO_DAREHK,
                target_model_id=self.BOSS_DAREHK_MODEL,
                engage_range=self.DAREHK_ENGAGE_RANGE,
            )
            
            if not killed:
                self.update_status("Warning: Darehk not confirmed dead - searching area...")
                yield from bot.combat.kill_all(radius=2500)
            
            self.update_status("Darehk defeated! Picking up Stone Tablet...")
            
            # Wait for item drop
            yield from Routines.Yield.wait(2000)
            
            # Pick up Stone Tablet
            picked_up = yield from bot.items.pickup_item_by_model_id(
                model_id=self.ITEM_STONE_TABLET,
                max_range=2500,
                timeout_ms=5000
            )
            
            if not picked_up and not bot.interaction.is_holding_bundle():
                self.update_status("Warning: Could not pick up Stone Tablet!")
            
            # Move to and use tablet on first pedestal
            self.update_status("Moving to Stone Pedestal...")
            yield from bot.combat.move_and_clear_path([self.PEDESTAL_1_POSITION])
            
            self.update_status("Using tablet on pedestal...")
            yield from bot.interaction.use_bundle_on_gadget(self.GADGET_PEDESTAL_1)
            
            self.complete_objective("Trial 1: Defeat Darehk the Quick")
            
            # === PHASE 3: Trial 2 - Retrieve Stone Tablets (PACIFIST ZONE) ===
            self.set_active_objective("Trial 2: Retrieve Stone Tablets")
            self.update_status("Trial 2: Entering pacifist zone...")
            
            # --- TABLET 1 ---
            # Enable pacifist mode for heroes
            self._set_all_heroes_behavior(self.HERO_AVOID)
            
            # Move WITHOUT combat to tablet area
            self.update_status("Moving to first tablet (avoiding Ghostly Sunspears)...")
            yield from bot.movement.move_to(self.TABLET1_SEARCH_POS[0], self.TABLET1_SEARCH_POS[1])
            
            # Pick up nearest tablet
            self.update_status("Picking up first tablet...")
            picked_up = yield from bot.items.pickup_item_by_model_id(
                model_id=self.ITEM_STONE_TABLET,
                max_range=2500
            )
            
            if not bot.interaction.is_holding_bundle():
                self.update_status("Warning: Could not pick up tablet 1!")
            
            # Carry to drop position
            self.update_status("Carrying tablet to drop position...")
            yield from bot.movement.move_to(self.TABLET1_DROP_POS[0], self.TABLET1_DROP_POS[1])
            
            # Drop the tablet
            yield from bot.interaction.drop_bundle()
            obj_trial2.current_count = 1
            
            # --- TABLET 2 ---
            self.update_status("Moving to second tablet...")
            for waypoint in self.PATH_TO_TABLET2:
                yield from bot.movement.move_to(waypoint[0], waypoint[1])
            
            # Pick up second tablet
            self.update_status("Picking up second tablet...")
            picked_up = yield from bot.items.pickup_item_by_model_id(
                model_id=self.ITEM_STONE_TABLET,
                max_range=2500
            )
            
            if not bot.interaction.is_holding_bundle():
                self.update_status("Warning: Could not pick up tablet 2!")
            
            # Return with tablet
            self.update_status("Returning with tablet...")
            for waypoint in self.PATH_TRIAL2_RETURN:
                yield from bot.movement.move_to(waypoint[0], waypoint[1])
            
            # Use tablet on pedestal 2
            self.update_status("Using tablet on first Trial 2 pedestal...")
            yield from bot.interaction.use_bundle_on_gadget(self.GADGET_PEDESTAL_2)
            
            # Pick up the tablet we dropped earlier and use on pedestal 3
            self.update_status("Picking up dropped tablet...")
            picked_up = yield from bot.items.pickup_item_by_model_id(
                model_id=self.ITEM_STONE_TABLET,
                max_range=2500
            )
            
            self.update_status("Using tablet on second Trial 2 pedestal...")
            yield from bot.interaction.use_bundle_on_gadget(self.GADGET_PEDESTAL_3)
            
            # Re-enable combat mode for heroes
            self._set_all_heroes_behavior(self.HERO_GUARD)
            
            obj_trial2.current_count = 2
            self.complete_objective("Trial 2: Retrieve Stone Tablets")
            
            # === PHASE 4: Trial 3 - Escort Kadash ===
            self.set_active_objective("Trial 3: Escort Kadash")
            self.update_status("Moving to Kadash...")
            
            yield from bot.combat.move_and_clear_path(self.PATH_TO_KADASH)
            yield from bot.movement.move_to(self.KADASH_START_POS[0], self.KADASH_START_POS[1])
            
            # Escort Kadash
            self.update_status("Escorting Kadash...")
            escort_success = yield from bot.movement.escort_npc(
                npc_model_id=self.NPC_KADASH_MODEL,
                path=self.PATH_ESCORT_KADASH,
                max_distance=self.ESCORT_MAX_DISTANCE,
                status_callback=lambda msg: self.update_status(msg)
            )
            
            if not escort_success:
                self.update_status("Warning: Escort may have failed!")
            
            # Wait for cutscene after escort
            self.update_status("Waiting for cutscene...")
            yield from bot.transition.wait_for_cinematic_end(timeout_ms=30000, auto_skip=True)
            
            self.complete_objective("Trial 3: Escort Kadash")
            
            # === PHASE 5: Final Boss - Apocryphia ===
            self.set_active_objective("Defeat Apocryphia")
            self.update_status("Hunting Apocryphia...")
            
            killed = yield from bot.combat.hunt_target_along_path(
                path=self.PATH_TO_APOCRYPHIA,
                target_model_id=self.BOSS_APOCRYPHIA_MODEL,
            )
            
            if killed:
                self.complete_objective("Defeat Apocryphia")
            else:
                self.update_status("Warning: Apocryphia not confirmed dead - clearing area...")
                yield from bot.combat.kill_all(radius=2500)
                self.complete_objective("Defeat Apocryphia")
            
            # === MISSION END ===
            self.update_status("Waiting for final cutscene...")
            yield from bot.transition.wait_for_cinematic_end(timeout_ms=30000, auto_skip=True)
            
            # Wait for teleport to Kamadan
            yield from bot.transition.wait_for_mission_end(self.MAP_ID_MISSION)
            self.update_status("Mission Complete!")
            
        except Exception as e:
            self.update_status(f"Mission Error: {str(e)}")
            import traceback
            import Py4GW
            Py4GW.Console.Log("MissionJokanur", traceback.format_exc(), Py4GW.Console.MessageType.Error)
            self.failed = True
            
        finally:
            # Ensure heroes are back to normal behavior
            self._set_all_heroes_behavior(self.HERO_GUARD)
            self.finished = True

    # ==================
    # HELPER METHODS
    # ==================
    
    def _set_all_heroes_behavior(self, behavior: int):
        """
        Set behavior for all heroes in party.
        
        Args:
            behavior: 0=Fight, 1=Guard, 2=Avoid
        """
        try:
            heroes = GLOBAL_CACHE.Party.GetHeroes()
            for hero in heroes:
                GLOBAL_CACHE.Party.Heroes.SetHeroBehavior(hero.agent_id, behavior)
            
            behavior_names = {0: "Fight", 1: "Guard", 2: "Avoid"}
            import Py4GW
            Py4GW.Console.Log(
                "MissionJokanur",
                f"Set all heroes to {behavior_names.get(behavior, behavior)} mode",
                Py4GW.Console.MessageType.Info
            )
        except Exception as e:
            import Py4GW
            Py4GW.Console.Log(
                "MissionJokanur",
                f"Error setting hero behavior: {e}",
                Py4GW.Console.MessageType.Warning
            )