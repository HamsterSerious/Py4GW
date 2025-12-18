"""
Mission: Chahbek Village
Campaign: Nightfall

Save the village by defeating the corsairs and sinking their ships.
This is the first mission in the Nightfall campaign.
"""
from core.base_task import BaseTask
from models.task import TaskInfo
from models.loadout import LoadoutConfig, MandatoryLoadout, HeroRequirement
from data.enums import TaskType
from data.timing import Timing
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib import Routines, AgentArray
from Py4GWCoreLib.enums_src.Hero_enums import HeroType


class MissionChahbek(BaseTask):
    """Chahbek Village - First Nightfall mission."""
    
    INFO = TaskInfo(
        name="Chahbek Village",
        description="Save the village by defeating the corsairs and sinking their ships.",
        task_type=TaskType.MISSION,
        loadout=LoadoutConfig(
            normal_mode=MandatoryLoadout(
                required_heroes=[
                    HeroRequirement(hero_id=HeroType.Koss.value, role="Mandatory", build="Any")
                ],
                notes="Koss is mandatory for this mission."
            ),
            hard_mode=MandatoryLoadout(
                required_heroes=[
                    HeroRequirement(hero_id=HeroType.Koss.value, role="Mandatory", build="Any")
                ],
                notes="Koss is mandatory for this mission."
            )
        )
    )
    
    # ==================
    # MISSION CONSTANTS
    # ==================
    
    # Map IDs
    MAP_ID = 544                    # Chahbek Village (mission)
    MAP_ID_COMPLETION = 456         # Churrhir Fields (after completion)
    
    # NPCs
    NPC_DEHVAD_MODEL = 4700
    NPC_DEHVAD_POS = (3482.00, -5167.00)
    DIALOG_START = 0x84
    
    # Targets
    BOSS_BENNIS_MODEL = 5023
    
    # Gadgets
    GADGET_OIL = 6373
    GADGET_CATAPULT_1 = 6388
    GADGET_CATAPULT_2 = 6389
    
    # Positions
    OIL_POSITION = (-4781.00, -1776.00)
    CATAPULT_1_POSITION = (-1691.00, -2515.00)
    CATAPULT_2_POSITION = (-1733.00, -4172.00)
    
    # Timing (mission-specific)
    SHIP_DESTROY_DELAY = 2000       # Wait for ship destruction animation
    
    # Bonus tracking
    RECRUIT_MODELS = [4809, 4810]
    
    # ==================
    # PATHS
    # ==================
    
    PATH_TO_BENNIS = [
        (1628.69, -3524.50),
        (-238.17, -5863.46),
        (-1997.69, -6181.05),
        (-4212.00, -6730.00)
    ]
    
    PATH_CLEANUP = [
        (-865.51, -2144.52),
        (-1733.83, -264.36),
        (-1628.37, 710.30)
    ]

    # ==================
    # MAIN EXECUTION
    # ==================

    def execute(self, bot):
        """Main mission execution."""
        try:
            # === SETUP OBJECTIVES ===
            self.update_status("Initializing Chahbek Village...")
            
            obj_bennis = self.add_objective("Kill Midshipman Bennis")
            obj_ships = self.add_objective("Destroy Corsair Ships", total=2)
            obj_clear = self.add_objective("Clear remaining Corsairs")
            obj_bonus = self.add_objective("Bonus: Recruits Alive", total=3)
            
            # Start bonus optimistically
            obj_bonus.current_count = 3
            obj_bonus.is_completed = True
            
            # Register bonus monitor (auto-cleaned on task end)
            self.register_monitor(bot, "BonusTracker", self._monitor_recruits(obj_bonus))
            
            # === ENTER MISSION ===
            success = yield from bot.transition.enter_mission_from_outpost(
                outpost_map_id=self.MAP_ID,
                npc_model_id=self.NPC_DEHVAD_MODEL,
                dialog_id=self.DIALOG_START,
                npc_position=self.NPC_DEHVAD_POS,
                use_hard_mode=self.use_hard_mode
            )
            
            if not success:
                self.update_status("Failed to enter mission!")
                self.failed = True
                return
            
            self.update_status("Mission Started!")
            
            # === OBJECTIVE 1: Kill Bennis ===
            self.set_active_objective("Kill Midshipman Bennis")
            self.update_status("Hunting Midshipman Bennis...")
            
            killed = yield from bot.combat.hunt_target_along_path(
                path=self.PATH_TO_BENNIS,
                target_model_id=self.BOSS_BENNIS_MODEL
            )
            
            if killed:
                self.complete_objective("Kill Midshipman Bennis")
            else:
                self.update_status("Warning: Bennis not found on path")
            
            # === OBJECTIVE 2: Destroy Ships ===
            self.set_active_objective("Destroy Corsair Ships")
            
            # Ship 1
            self.update_status("Destroying Ship 1...")
            yield from self._fire_catapult(bot, self.GADGET_CATAPULT_1, self.CATAPULT_1_POSITION)
            obj_ships.current_count = 1
            
            # Ship 2
            self.update_status("Destroying Ship 2...")
            yield from self._fire_catapult(bot, self.GADGET_CATAPULT_2, self.CATAPULT_2_POSITION)
            self.complete_objective("Destroy Corsair Ships")
            
            # === OBJECTIVE 3: Cleanup ===
            self.set_active_objective("Clear remaining Corsairs")
            self.update_status("Clearing remaining Corsairs...")
            
            yield from bot.combat.move_and_clear_path(self.PATH_CLEANUP)
            yield from bot.combat.kill_all(radius=2500)
            
            self.complete_objective("Clear remaining Corsairs")
            
            # === MISSION END ===
            yield from bot.transition.wait_for_mission_end(self.MAP_ID)
            self.update_status("Mission Complete!")
            
        except Exception as e:
            self.update_status(f"Mission Error: {str(e)}")
            import traceback
            import Py4GW
            Py4GW.Console.Log("MissionChahbek", traceback.format_exc(), Py4GW.Console.MessageType.Error)
            self.failed = True
            
        finally:
            # Monitors are auto-cleaned by BaseTask, but we mark finished
            self.finished = True

    # ==================
    # MISSION-SPECIFIC METHODS
    # ==================
    
    def _fire_catapult(self, bot, catapult_model: int, catapult_pos: tuple):
        """
        Complete catapult firing sequence: get oil → load → fire.
        
        Args:
            bot: Bot instance
            catapult_model: Model ID of the catapult gadget
            catapult_pos: (x, y) position of the catapult
        """
        # Get oil and load catapult
        yield from bot.interaction.pickup_and_use_bundle(
            bundle_model_id=self.GADGET_OIL,
            bundle_position=self.OIL_POSITION,
            target_model_id=catapult_model,
            target_position=catapult_pos,
            post_use_delay_ms=Timing.GADGET_USE_DELAY
        )
        
        # Fire catapult (interact again)
        self.update_status("Firing Catapult!")
        catapult_agent = bot.interaction.find_gadget_by_id(catapult_model)
        if catapult_agent:
            yield from bot.interaction.move_to_and_interact(catapult_agent)
            yield from Routines.Yield.wait(self.SHIP_DESTROY_DELAY)

    def _monitor_recruits(self, obj_bonus):
        """
        Background coroutine monitoring Sunspear Recruit survival.
        
        Optimistic approach: Starts at 3/3 alive.
        Scans for recruits and updates count based on deaths.
        
        Args:
            obj_bonus: The TaskObjective to update
        """
        known_recruit_ids = set()
        
        while True:
            # Find recruit agents
            try:
                for agent_id in AgentArray.GetAgentArray():
                    if agent_id in known_recruit_ids:
                        continue
                    if not GLOBAL_CACHE.Agent.IsValid(agent_id):
                        continue
                    
                    model_id = GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id)
                    if model_id in self.RECRUIT_MODELS:
                        known_recruit_ids.add(agent_id)
            except:
                pass
            
            # Count dead recruits
            dead_count = 0
            for agent_id in known_recruit_ids:
                try:
                    if GLOBAL_CACHE.Agent.IsValid(agent_id) and GLOBAL_CACHE.Agent.IsDead(agent_id):
                        dead_count += 1
                except:
                    pass
            
            # Update objective (assume 3 total recruits)
            alive_count = max(0, 3 - dead_count)
            obj_bonus.current_count = alive_count
            
            if alive_count == 3:
                obj_bonus.name = "Bonus: Recruits Alive (3/3)"
                obj_bonus.is_completed = True
                obj_bonus.is_active = False
            else:
                obj_bonus.name = f"Bonus FAILED: Recruits ({alive_count}/3)"
                obj_bonus.is_completed = False
                obj_bonus.is_active = True  # Highlight as warning
            
            yield from Routines.Yield.wait(Timing.MONITOR_TICK)