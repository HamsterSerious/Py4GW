from core.base_task import BaseTask
from models.task import TaskInfo
from models.loadout import LoadoutConfig, MandatoryLoadout, HeroRequirement
from data.enums import TaskType
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib import Routines, Player, Utils, AgentArray
from Py4GWCoreLib.enums_src.Hero_enums import HeroType
import time
import Py4GW

# --- Helper Class for timers ---
class SimpleTimer:
    def __init__(self):
        self.start_time = time.time()
        
    def HasElapsed(self, milliseconds):
        return (time.time() - self.start_time) * 1000 >= milliseconds
        
    def Reset(self):
        self.start_time = time.time()

class MissionChahbek(BaseTask):
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
    
    # IDs and Constants
    MAP_ID_CHAHBEK = 544
    MAP_ID_CHURRHIR = 456
    NPC_DEHVAD_ID = 4700 
    DIALOG_START = 0x84
    
    BOSS_BENNIS_ID = 5023 
    GADGET_OIL_ID = 6373
    GADGET_CATAPULT1_ID = 6388
    GADGET_CATAPULT2_ID = 6389
    
    # Recruits: 2x Model 4809, 1x Model 4810
    RECRUIT_MODELS = [4809, 4810]
    
    def execute(self, bot):
        try:
            # 1. Setup Objectives
            self.update_status("Initializing Chahbek Village...")
            
            # Main Objectives
            obj_bennis = self.add_objective("Kill Midshipman Bennis", total=1)
            obj_ships = self.add_objective("Destroy Corsair Ships", total=2)
            obj_clear = self.add_objective("Clear remaining Corsairs", total=1)
            
            # Bonus Objective - OPTIMISTIC START (Green, 3/3)
            obj_bonus = self.add_objective("Bonus: Sunspear Recruits must survive (3/3 Alive)", total=3)
            obj_bonus.current_count = 3 
            obj_bonus.is_completed = True # Start Green
            
            # Start Bonus Monitor Coroutine
            bot.config.FSM.AddManagedCoroutine(
                "ChahbekBonusMonitor", 
                self._monitor_bonus_objectives(obj_bonus)
            )
            
            # 2. Travel / Start Logic
            current_map = GLOBAL_CACHE.Map.GetMapID()
            
            if current_map != self.MAP_ID_CHAHBEK:
                self.update_status("Traveling to Chahbek Village...")
                yield from bot.transition.travel_to(self.MAP_ID_CHAHBEK)
                
            # Start Mission if in Outpost
            if bot.transition.is_outpost:
                self.update_status("Starting Mission...")
                yield from bot.transition.setup_mission(bot, self.use_hard_mode)
                
                # Interact with Dehvad
                npc_x, npc_y = 3482.00, -5167.00
                
                npc_name = "Dehvad"
                temp_id = Routines.Agents.GetAgentIDByModelID(self.NPC_DEHVAD_ID)
                if temp_id != 0:
                    try:
                        name = GLOBAL_CACHE.Agent.GetName(temp_id)
                        if name: npc_name = name
                    except: pass
                
                self.update_status(f"Approaching {npc_name}...")
                yield from bot.movement.move_to(npc_x, npc_y)
                
                npc_agent_id = Routines.Agents.GetAgentIDByModelID(self.NPC_DEHVAD_ID)
                if npc_agent_id == 0:
                    self.update_status(f"Error: Could not find {npc_name} (AgentID 0)")
                    return

                self.update_status(f"Talking to {npc_name}...")
                
                yield from bot.transition.move_to_interact_and_dialog(
                    npc_id=npc_agent_id, 
                    dialog_id=self.DIALOG_START,
                    x=npc_x,
                    y=npc_y,
                    log_message="Starting Mission..."
                )
            
            if bot.transition.is_outpost:
                self.update_status("Error: Failed to enter mission!")
                return 

            self.update_status("Mission Started!")
            
            # 3. Path to Bennis
            path_to_bennis = [
                (1628.69, -3524.50),
                (-238.17, -5863.46),
                (-1997.69, -6181.05),
                (-4212.00, -6730.00)
            ]
            
            self.set_active_objective("Kill Midshipman Bennis")
            self.update_status("Hunting Midshipman Bennis...")
            
            yield from self._move_and_kill_boss(bot, path_to_bennis, self.BOSS_BENNIS_ID)
            
            self.complete_objective("Kill Midshipman Bennis")
            
            # 4. Ship 1
            self.set_active_objective("Destroy Corsair Ships")
            yield from self._handle_oil_mechanic(
                bot, 
                oil_location=(-4781.00, -1776.00),
                catapult_id=self.GADGET_CATAPULT1_ID,
                catapult_location=(-1691.00, -2515.00),
                ship_count=1
            )
            obj_ships.current_count = 1
            
            # 5. Ship 2
            yield from self._handle_oil_mechanic(
                bot, 
                oil_location=(-4781.00, -1776.00),
                catapult_id=self.GADGET_CATAPULT2_ID,
                catapult_location=(-1733.00, -4172.00),
                ship_count=2
            )
            self.complete_objective("Destroy Corsair Ships")
            
            # 6. Cleanup
            path_cleanup = [
                (-865.51, -2144.52),
                (-1733.83, -264.36),
                (-1628.37, 710.30)
            ]
            
            self.set_active_objective("Clear remaining Corsairs")
            self.update_status("Clearing remaining Corsairs...")
            
            yield from bot.combat.move_and_clear_path(path_cleanup)
            yield from bot.combat.kill_all(radius=2500)
            
            self.complete_objective("Clear remaining Corsairs")
            
            # 7. Wait for Completion
            self.update_status("Mission Complete! Waiting for travel...")
            
            exit_timeout = SimpleTimer()
            while True:
                if GLOBAL_CACHE.Map.IsMapLoading():
                    self.update_status("Loading screen detected...")
                    break
                
                curr_map = GLOBAL_CACHE.Map.GetMapID()
                if curr_map != self.MAP_ID_CHAHBEK and curr_map != 0:
                    self.update_status("Map ID change detected...")
                    break

                if exit_timeout.HasElapsed(60000): # 60s timeout
                     self.update_status("Warning: Timed out waiting for map exit.")
                     break
                yield 
            
            arrival_timeout = SimpleTimer()
            while True:
                is_loading = GLOBAL_CACHE.Map.IsMapLoading()
                is_ready = GLOBAL_CACHE.Map.IsMapReady()
                
                if not is_loading and is_ready:
                    break
                
                if arrival_timeout.HasElapsed(30000): # 30s timeout
                    self.update_status("Warning: Timed out waiting for map ready.")
                    break
                yield

            final_map = GLOBAL_CACHE.Map.GetMapID()
            if final_map == self.MAP_ID_CHURRHIR:
                self.update_status("Arrived in Churrhir Fields.")
            else:
                self.update_status(f"Transition Complete (Map ID: {final_map}).")

        except Exception as e:
            self.update_status(f"Task Exception: {str(e)}")
            import traceback
            Py4GW.Console.Log("MissionChahbek", traceback.format_exc(), Py4GW.Console.MessageType.Error)
            
        finally:
            # Clean up the bonus monitor
            bot.config.FSM.RemoveManagedCoroutine("ChahbekBonusMonitor")
            
            self.finished = True
            self.update_status("Task Finished.")

    def _monitor_bonus_objectives(self, obj_bonus):
        """
        Background coroutine to monitor Sunspear Recruits.
        Optimistic approach: Starts at 3/3.
        Scans for recruits and decrements count if any are found dead.
        """
        # IDs of recruits: 4809 (x2) and 4810 (x1)
        known_recruit_ids = set()
        
        while True:
            # 1. Scan for Recruits (Continuous scan to catch them as they stream in)
            # using GetAgentArray to find them even if dead or distant
            agents = AgentArray.GetAgentArray() 
            for agent_id in agents:
                if agent_id in known_recruit_ids:
                    continue
                
                if not GLOBAL_CACHE.Agent.IsValid(agent_id):
                    continue
                    
                model_id = GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id)
                if model_id in self.RECRUIT_MODELS:
                    known_recruit_ids.add(agent_id)
            
            # 2. Count Dead Recruits
            dead_count = 0
            for agent_id in known_recruit_ids:
                if GLOBAL_CACHE.Agent.IsValid(agent_id):
                    if GLOBAL_CACHE.Agent.IsDead(agent_id):
                        dead_count += 1
            
            # 3. Calculate Status
            # We assume 3 total recruits exist in the mission.
            alive_count = max(0, 3 - dead_count)
            
            obj_bonus.current_count = alive_count
            
            if alive_count == 3:
                obj_bonus.name = "Bonus: Sunspear Recruits must survive (3/3 Alive)"
                obj_bonus.is_completed = True # Green
                obj_bonus.is_active = False
            else:
                obj_bonus.name = f"Bonus failed: Recruits died ({alive_count}/3 Alive)"
                obj_bonus.is_completed = False # Remove Green
                obj_bonus.is_active = True # Warning color
            
            yield from Routines.Yield.wait(500)

    def _move_and_kill_boss(self, bot, path, boss_model_id):
        path_index = 0
        boss_dead = False
        
        while not boss_dead:
            if GLOBAL_CACHE.Map.GetMapID() != self.MAP_ID_CHAHBEK:
                return

            boss_id = Routines.Agents.GetAgentIDByModelID(boss_model_id)
            engaging_boss = False
            
            if boss_id != 0:
                if GLOBAL_CACHE.Agent.IsDead(boss_id):
                    boss_dead = True
                    Player.CancelMove()
                    self.update_status("Boss eliminated.")
                    return

                boss_pos = GLOBAL_CACHE.Agent.GetXY(boss_id)
                my_pos = Player.GetXY()
                dist = Utils.Distance(my_pos, boss_pos)
                
                if dist < 2000:
                    engaging_boss = True
                    
                    try:
                        boss_name = GLOBAL_CACHE.Agent.GetName(boss_id)
                    except:
                        boss_name = "Boss"

                    if dist < 1200:
                        Player.CancelMove()
                        self.update_status(f"Fighting {boss_name}...")
                        yield from bot.combat.kill_target(boss_id)
                        continue 
                    else:
                        self.update_status(f"Approaching {boss_name}...")
                        Player.Move(boss_pos[0], boss_pos[1])

            if not engaging_boss:
                if path_index < len(path):
                    target_pos = path[path_index]
                    Player.Move(target_pos[0], target_pos[1])
                    if Utils.Distance(Player.GetXY(), target_pos) < 150:
                        path_index += 1
                else:
                    if boss_id != 0:
                        self.update_status("Path complete. Moving to Boss...")
                        boss_pos = GLOBAL_CACHE.Agent.GetXY(boss_id)
                        Player.Move(boss_pos[0], boss_pos[1])
                    else:
                        self.update_status("Searching for boss...")
            
            if bot.combat.in_combat():
                Player.CancelMove()
                yield from bot.combat.kill_all(radius=1500)
            
            yield

    def _handle_oil_mechanic(self, bot, oil_location, catapult_id, catapult_location, ship_count):
        self.update_status(f"Fetching Oil for Ship {ship_count}...")
        yield from bot.combat.move_and_clear_path([oil_location])
        
        oil_id = 0
        wait_timer = SimpleTimer()
        wait_timer.Reset()
        
        while oil_id == 0 and not wait_timer.HasElapsed(5000):
            oil_id = bot.interaction.find_gadget_by_id(self.GADGET_OIL_ID)
            if oil_id == 0: yield
        
        if oil_id != 0:
            yield from bot.interaction.move_to_and_interact(oil_id)
            yield from Routines.Yield.wait(1000)
            
            if not bot.interaction.is_holding_item():
                self.update_status("Failed to pickup oil, retrying...")
                yield from bot.interaction.move_to_and_interact(oil_id)
        else:
             self.update_status("Error: Oil gadget not found!")

        self.update_status(f"Moving to Catapult {ship_count}...")
        yield from bot.combat.move_and_clear_path([catapult_location])
        
        cat_agent_id = 0
        wait_timer.Reset()
        while cat_agent_id == 0 and not wait_timer.HasElapsed(5000):
            cat_agent_id = bot.interaction.find_gadget_by_id(catapult_id)
            if cat_agent_id == 0: yield

        if cat_agent_id != 0:
            self.update_status("Loading Catapult...")
            yield from bot.interaction.move_to_and_interact(cat_agent_id)
            yield from Routines.Yield.wait(1000)
            
            self.update_status("Firing Catapult!")
            yield from bot.interaction.move_to_and_interact(cat_agent_id)
            yield from Routines.Yield.wait(2000)
        else:
            self.update_status("Error: Catapult gadget not found!")