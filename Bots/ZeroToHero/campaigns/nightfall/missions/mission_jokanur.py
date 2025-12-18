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
    BOSS_DAREHK_MODEL = 5545          # Darehk the Quick (Trial 1) - NOTE: Same as Ghostly Sunspear!
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
    PATH_TRIAL2_START = [
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
    LOOT_PICKUP_TIMEOUT = 5000        # Timeout for item pickup
    CLEAR_AREA_RADIUS = 2000          # Radius to clear enemies before pickup

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
            
            # === SETUP LOOT WHITELIST ===
            # Whitelist Stone Tablet so we can pick it up (non-yielding call)
            bot.items.add_to_whitelist(self.ITEM_STONE_TABLET)
            
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
            
            # hunt_target_along_path now correctly finds ENEMIES only
            # This distinguishes Darehk (enemy, ModelID 5545) from Gatah (ally, same ModelID)
            killed = yield from bot.combat.hunt_target_along_path(
                path=self.PATH_TO_DAREHK,
                target_model_id=self.BOSS_DAREHK_MODEL,
                engage_range=self.DAREHK_ENGAGE_RANGE,
            )
            
            # === SAVE OUR POSITION - we were in fighting range when he died ===
            from Py4GWCoreLib import Player
            import Py4GW
            fight_position = Player.GetXY()
            Py4GW.Console.Log("ZeroToHero", f"Darehk fight position saved: ({fight_position[0]:.0f}, {fight_position[1]:.0f})", Py4GW.Console.MessageType.Info)
            
            if not killed:
                self.update_status("Warning: Darehk not confirmed dead - searching area...")
                yield from bot.combat.kill_all(radius=self.CLEAR_AREA_RADIUS)
                
                # Double check using enemy-specific method
                if not bot.combat.is_enemy_dead(self.BOSS_DAREHK_MODEL):
                    self.update_status("ERROR: Darehk still alive!")
                    self.failed = True
                    return
            
            self.update_status("Darehk defeated!")
            
            # === Clear enemies, then return to fight position to pick up tablet ===
            self.update_status("Clearing remaining enemies...")
            yield from bot.combat.kill_all(radius=1500)  # Clear nearby first
            
            # Return to where we were when Darehk died (tablet should be nearby)
            self.update_status(f"Returning to fight area ({fight_position[0]:.0f}, {fight_position[1]:.0f})...")
            yield from bot.combat.move_and_clear_path([fight_position])
            
            # Wait for item to drop
            self.update_status("Waiting for Stone Tablet to drop...")
            yield from Routines.Yield.wait(2000)  # Longer wait for drop animation
            
            # Pick up Stone Tablet with larger search range (default is ~1012)
            self.update_status("Picking up Stone Tablet...")
            yield from bot.items.pickup_items(
                pickup_timeout_ms=self.LOOT_PICKUP_TIMEOUT,
                max_distance=2500  # Larger range to find tablet
            )
            
            # Check if we're holding the tablet
            if bot.interaction.is_holding_bundle():
                self.update_status("Stone Tablet acquired!")
            else:
                self.update_status("Warning: Could not confirm Stone Tablet pickup - continuing anyway...")
            
            # Move to and use tablet on first pedestal
            self.update_status("Moving to Stone Pedestal...")
            yield from bot.combat.move_and_clear_path([self.PEDESTAL_1_POSITION])
            
            # Use tablet on pedestal (interact while holding bundle)
            self.update_status("Using tablet on pedestal...")
            yield from bot.interaction.use_bundle_on_gadget(self.GADGET_PEDESTAL_1)
            
            self.complete_objective("Trial 1: Defeat Darehk the Quick")
            
            # === PHASE 3: Trial 2 - Retrieve Two Stone Tablets ===
            self.set_active_objective("Trial 2: Retrieve Stone Tablets")
            
            # Add Ghostly Sunspears to ignore list (same ModelID as Darehk!)
            bot.combat.add_to_ignore_list(self.ENEMY_GHOSTLY_SUNSPEAR)
            
            # --- Tablet 1 ---
            self.update_status("Trial 2: Retrieving first tablet...")
            
            # Move toward tablet area
            yield from bot.combat.move_and_clear_path(self.PATH_TRIAL2_START)
            
            # TODO: Flag heroes to avoid them killing Ghostly Sunspears
            # Needs: bot.hero.flag_all(self.HERO_FLAG_POSITION_1)
            self.update_status("TODO: Flag heroes to safe position")
            
            # Pick up nearest Stone Tablet using whitelist method
            self.update_status("Picking up first tablet...")
            yield from bot.items.pickup_items(
                pickup_timeout_ms=self.LOOT_PICKUP_TIMEOUT,
                max_distance=2500
            )
            
            if not bot.interaction.is_holding_bundle():
                self.update_status("Warning: Could not pick up tablet 1")
            
            # Move to drop position and drop tablet
            self.update_status("Carrying tablet to drop position...")
            yield from bot.movement.move_to(self.TABLET1_DROP_POSITION[0], self.TABLET1_DROP_POSITION[1])
            
            # Drop the tablet
            self.update_status("Dropping tablet...")
            yield from bot.interaction.drop_bundle()
            
            # TODO: Unflag heroes
            # Needs: bot.hero.unflag_all()
            
            obj_trial2.current_count = 1
            
            # --- Tablet 2 ---
            self.update_status("Trial 2: Retrieving second tablet...")
            
            # Move to second tablet area
            yield from bot.combat.move_and_clear_path(self.PATH_TRIAL2_TABLET2_APPROACH)
            
            # TODO: Flag heroes again
            # Needs: bot.hero.flag_all(self.HERO_FLAG_POSITION_2)
            self.update_status("TODO: Flag heroes for tablet 2")
            
            # Pick up nearest Stone Tablet using whitelist method
            self.update_status("Picking up second tablet...")
            yield from bot.items.pickup_items(
                pickup_timeout_ms=self.LOOT_PICKUP_TIMEOUT,
                max_distance=2500
            )
            
            if not bot.interaction.is_holding_bundle():
                self.update_status("Warning: Could not pick up tablet 2")
            
            # Return with tablet
            self.update_status("Returning with tablet...")
            yield from bot.combat.move_and_clear_path(self.PATH_TRIAL2_RETURN)
            
            # TODO: Unflag heroes
            # Needs: bot.hero.unflag_all()
            
            # Use tablet on pedestal 2
            self.update_status("Using tablet on first pedestal...")
            yield from bot.interaction.use_bundle_on_gadget(self.GADGET_PEDESTAL_2)
            
            # Pick up remaining tablet and use on pedestal 3
            self.update_status("Picking up final tablet...")
            yield from bot.items.pickup_items(
                pickup_timeout_ms=self.LOOT_PICKUP_TIMEOUT,
                max_distance=2500
            )
            
            self.update_status("Using tablet on second pedestal...")
            yield from bot.interaction.use_bundle_on_gadget(self.GADGET_PEDESTAL_3)
            
            # Clear ignore list now that Trial 2 is done
            bot.combat.clear_ignore_list()
            
            obj_trial2.current_count = 2
            self.complete_objective("Trial 2: Retrieve Stone Tablets")
            
            # === PHASE 4: Trial 3 - Escort Kadash ===
            self.set_active_objective("Trial 3: Escort Kadash")
            self.update_status("Moving to Kadash...")
            
            yield from bot.combat.move_and_clear_path(self.PATH_TO_KADASH)
            yield from bot.movement.move_to(self.KADASH_START_POSITION[0], self.KADASH_START_POSITION[1])
            
            # TODO: Implement escort functionality
            # Needs: yield from bot.movement.escort_npc(
            #     npc_model_id=self.NPC_KADASH_MODEL,
            #     path=self.PATH_ESCORT_KADASH,
            #     max_distance=1000,
            #     status_callback=lambda msg: self.update_status(msg)
            # )
            self.update_status("TODO: Escort Kadash along path")
            yield from bot.combat.move_and_clear_path(self.PATH_ESCORT_KADASH)
            yield from Routines.Yield.wait(1000)  # Placeholder
            
            # Wait for cutscene after escort completes
            # TODO: yield from bot.transition.wait_for_cutscene()
            self.update_status("TODO: Wait for cutscene")
            yield from Routines.Yield.wait(2000)  # Placeholder
            
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
                # Try to verify
                if bot.combat.is_enemy_dead(self.BOSS_APOCRYPHIA_MODEL):
                    self.complete_objective("Defeat Apocryphia")
            
            # === MISSION END ===
            # Cutscene plays, then teleport to Kamadan
            self.update_status("Waiting for mission completion...")
            yield from bot.transition.wait_for_mission_end(self.MAP_ID_MISSION)
            self.update_status("Mission Complete!")
            
        except Exception as e:
            self.update_status(f"Mission Error: {str(e)}")
            import traceback
            import Py4GW
            Py4GW.Console.Log("MissionJokanur", traceback.format_exc(), Py4GW.Console.MessageType.Error)
            self.failed = True
            
        finally:
            # Clean up
            bot.combat.clear_ignore_list()
            # Clear the whitelist to avoid picking up tablets in other missions
            bot.items.clear_whitelist()
            self.finished = True