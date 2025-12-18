"""
Mission: Jokanur Diggings
Campaign: Nightfall

Investigate the ruins of Fahranur, The First City with Kormir to find what is killing the workers.
This is the second mission in the Nightfall campaign.
"""
from core.base_task import BaseTask
from models.task import TaskInfo
from models.loadout import LoadoutConfig, MandatoryLoadout, HeroRequirement
from data.enums import TaskType
from data.timing import Timing
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib import Routines
from Py4GWCoreLib.enums_src.Hero_enums import HeroType


class MissionJokanur(BaseTask):
    """Jokanur Diggings - Second Nightfall mission."""
    
    INFO = TaskInfo(
        name="Jokanur Diggings",
        description="Investigate the ruins of Fahranur, The First City with Kormir to find what is killing the workers.",
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
    MAP_ID_OUTPOST = 491              # Jokanur Diggings (outpost)
    MAP_ID_MISSION = 491              # Same ID, differentiated by IsOutpost
    MAP_ID_COMPLETION = 449           # Kamadan (after completion)
    
    # NPCs
    NPC_GATAH_MODEL = 4712
    NPC_GATAH_POS = (2888.00, 2207.00)
    NPC_GATAH_APPROACH = (2171.93, -184.73)  # Walk here first if NPC not visible
    DIALOG_START = 0x84
    
    # Bosses / Targets
    BOSS_DAREHK_MODEL = 5545          # Darehk the Quick (Trial 1)
    BOSS_APOCRYPHIA_MODEL = 4335      # Final boss
    
    # NPCs to escort
    NPC_KADASH_MODEL = 5546           # Escort target (Trial 3)
    
    # Items
    ITEM_STONE_TABLET = 17055         # Dropped by Darehk, used on pedestals
    
    # Gadgets (Stone Pedestals)
    GADGET_PEDESTAL_1 = 6472          # After Trial 1
    GADGET_PEDESTAL_2 = 6475          # Trial 2 - first pedestal
    GADGET_PEDESTAL_3 = 6474          # Trial 2 - second pedestal
    
    # Enemies to ignore (for Trial 2)
    ENEMY_GHOSTLY_SUNSPEAR = 5545     # Don't kill these during tablet retrieval
    
    # ==================
    # PATHS
    # ==================
    
    # Path to the Ancient Istani Ruins (before first gate)
    PATH_TO_RUINS = [
        (15590.30, 13267.24),
        (12465.50, 13480.69),
        (11329.49, 15380.10),
        (10470.48, 18107.08),
        (7927.25, 18685.61),
        (5945.47, 17288.90),
        (2793.44, 16898.92),
    ]
    
    # Gate position and waypoint after gate (for progress checking)
    GATE_POSITION = (-155.00, 14430.16)
    AFTER_GATE_POSITION = (-1505.30, 14471.92)
    
    # Path to engage Darehk the Quick (Trial 1)
    PATH_TO_DAREHK = [
        (-1505.30, 14471.92),
    ]
    
    # Position of first Stone Pedestal (after killing Darehk)
    PEDESTAL_1_POSITION = (-5934.00, 11249.00)
    
    # Trial 2 paths
    PATH_TRIAL2_TABLET1 = [
        (-9297.15, 11574.76),
    ]
    HERO_FLAG_POSITION_1 = (-9826.88, 7815.42)
    TABLET1_DROP_POSITION = (-11461.18, 6657.43)
    
    PATH_TRIAL2_TABLET2_APPROACH = [
        (-12266.74, 9621.60),
        (-12411.94, 11786.64),
    ]
    HERO_FLAG_POSITION_2 = (-12411.94, 11786.64)
    PATH_TRIAL2_RETURN = [
        (-12266.74, 9621.60),
        (-11965.52, 6699.59),
    ]
    
    # Trial 3 - Escort Kadash
    PATH_TO_KADASH = [
        (-11736.30, 4717.63),
        (-10536.60, 3467.35),
    ]
    KADASH_START_POSITION = (-10251.00, 1900.00)
    
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
    # TIMING OVERRIDES
    # ==================
    
    GATE_STUCK_TIMEOUT = 3.0          # Seconds without progress = blocked
    GATE_RETRY_DELAY = 5.0            # Seconds to wait before retry
    DAREHK_ENGAGE_RANGE = 3000        # Extended range to engage Darehk

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
            
            # Move to gate and wait for it to open
            self.update_status("Approaching gate...")
            yield from bot.movement.move_to(self.GATE_POSITION[0], self.GATE_POSITION[1])
            
            self.update_status("Waiting for gate to open...")
            gate_success = yield from bot.movement.move_with_gate_check(
                self.AFTER_GATE_POSITION[0],
                self.AFTER_GATE_POSITION[1],
                stuck_timeout_sec=self.GATE_STUCK_TIMEOUT,
                retry_delay_sec=self.GATE_RETRY_DELAY,
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
            
            # TODO: Need to implement extended engage range for this boss
            # For now, use hunt_target_along_path with default ranges
            killed = yield from bot.combat.hunt_target_along_path(
                path=self.PATH_TO_DAREHK,
                target_model_id=self.BOSS_DAREHK_MODEL,
                engage_range=self.DAREHK_ENGAGE_RANGE,
            )
            
            if not killed:
                self.update_status("Warning: Darehk not found - searching area...")
                yield from bot.combat.kill_all(radius=2500)
            
            # TODO: Pick up Stone Tablet dropped by Darehk
            # Needs: bot.items.find_item_by_model(self.ITEM_STONE_TABLET)
            # Needs: bot.items.pickup_item(item_id)
            # Needs: Check if holding bundle
            self.update_status("TODO: Pick up Stone Tablet")
            yield from Routines.Yield.wait(1000)  # Placeholder
            
            # TODO: Use tablet on first pedestal
            # yield from bot.interaction.use_bundle_on_gadget(self.GADGET_PEDESTAL_1)
            self.update_status("TODO: Use tablet on pedestal")
            yield from Routines.Yield.wait(1000)  # Placeholder
            
            self.complete_objective("Trial 1: Defeat Darehk the Quick")
            
            # === PHASE 3: Trial 2 - Retrieve Two Stone Tablets ===
            self.set_active_objective("Trial 2: Retrieve Stone Tablets")
            
            # --- Tablet 1 ---
            self.update_status("Trial 2: Retrieving first tablet...")
            
            # TODO: Flag heroes to avoid killing Ghostly Sunspears
            # Needs: bot.hero_control.flag_all_heroes(self.HERO_FLAG_POSITION_1)
            # TODO: Add Ghostly Sunspear to enemy ignore list
            # Needs: bot.combat.add_to_ignore_list(self.ENEMY_GHOSTLY_SUNSPEAR)
            
            # TODO: Find closest Stone Tablet item and pick it up
            # TODO: Move to drop position and drop tablet
            # TODO: Unflag heroes
            
            obj_trial2.current_count = 1
            self.update_status("TODO: First tablet retrieved (placeholder)")
            yield from Routines.Yield.wait(1000)  # Placeholder
            
            # --- Tablet 2 ---
            self.update_status("Trial 2: Retrieving second tablet...")
            
            # TODO: Similar process for second tablet
            # TODO: Use tablets on pedestals 2 and 3
            
            obj_trial2.current_count = 2
            self.complete_objective("Trial 2: Retrieve Stone Tablets")
            self.update_status("TODO: Second tablet retrieved (placeholder)")
            yield from Routines.Yield.wait(1000)  # Placeholder
            
            # === PHASE 4: Trial 3 - Escort Kadash ===
            self.set_active_objective("Trial 3: Escort Kadash")
            self.update_status("Moving to Kadash...")
            
            yield from bot.combat.move_and_clear_path(self.PATH_TO_KADASH)
            
            # TODO: Implement escort functionality
            # Needs: bot.movement.escort_npc(
            #     npc_model_id=self.NPC_KADASH_MODEL,
            #     path=self.PATH_ESCORT_KADASH,
            #     max_distance=1000
            # )
            self.update_status("TODO: Escort Kadash (placeholder)")
            yield from Routines.Yield.wait(1000)  # Placeholder
            
            # TODO: Wait for cutscene after escort completes
            # Needs: bot.wait_for_cutscene()
            
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
                self.update_status("Warning: Apocryphia not confirmed dead")
            
            # === MISSION END ===
            # Cutscene plays, then teleport to Kamadan
            yield from bot.transition.wait_for_mission_end(self.MAP_ID_MISSION)
            self.update_status("Mission Complete!")
            
        except Exception as e:
            self.update_status(f"Mission Error: {str(e)}")
            import traceback
            import Py4GW
            Py4GW.Console.Log("MissionJokanur", traceback.format_exc(), Py4GW.Console.MessageType.Error)
            self.failed = True
            
        finally:
            self.finished = True