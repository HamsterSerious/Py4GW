import time
from Py4GWCoreLib import *
from Bots.ZeroToHero.Shared.MissionContext import BaseMission, MissionContext

# Import GLOBAL_CACHE safely
try:
    from Py4GWCoreLib import GLOBAL_CACHE
except ImportError:
    try:
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    except ImportError:
        GLOBAL_CACHE = None


class ChahbekVillage(BaseMission, MissionContext):
    """
    Chahbek Village Mission Bot
    """
    
    def GetInfo(self):
        return {
            "Name": "Chahbek Village",
            "Description": "Save the village by defeating the corsairs and sinking their ships.",
            "Recommended_Builds": ["Any", "Koss Required"],
            "HM_Tips": "Make sure to have strong Healers, as the Sunspear Recruits tend to die easily."
        }

    # --- CONFIGURATION ---
    Outpost_Map_ID = 544
    Mission_Map_ID = 544  # Same as outpost for Chahbek
    
    # NPC Position
    NPC_Jahdugar_Position = (3482, -5167)
    NPC_Starter_Name = "First Spear Jahdugar"
    
    # Gadgets positions in Mission
    Gadget_Oil_Position = (-4781, -1776)
    Gadget_Catapult_1_Position = (-1691, -2515)
    Gadget_Catapult_2_Position = (-1733, -4172)
    
    # Dialogs
    Dialog_TakeQuest = 0x81
    Dialog_StartMission = 0x84

    # Define Paths
    Path_Data = {
        "Step1": [(1672, -3500)],
        "Step2": [(51, -5261)],
        "Step3": [(-2201, -6408)],
        "Step4": [(-3847, -6360)],
        "Step5": [(-4500, -2856)],
        "ToOil": [(-4799, -1827)],
        "ToCata1": [(-2998, -2775), (-1720, -2520)],
        "ToCata2": [(-2998, -2775), (-1731, -4138)],
        "ToBeach": [(-531, -3264)],
        "ToCommander": [(-2196, -3)],
        "KillCommander": [(-1648, 1073)]
    }

    def __init__(self):
        super().__init__()
        
        # Initialize Path Handlers
        self.paths = {}
        for key, coords in self.Path_Data.items():
            self.paths[key] = Routines.Movement.PathHandler(coords)
        
        # Timers for throttling
        self._move_timer = Timer()
        self._move_timer.Start()
        self._interact_timer = Timer()
        self._interact_timer.Start()
        self._debug_timer = Timer()
        self._debug_timer.Start()
        
        # Track current target NPC
        self._current_npc_id = 0
        
        # Track if we're holding a bundle (for oil)
        self._holding_bundle = False
        
        # FIX: Track mission state
        self._mission_started = False  # True once we enter the mission instance
        self._last_map_id = 0
        self._cinematic_detected = False

    def Reset(self):
        """Reset mission state."""
        super().Reset()
        for path in self.paths.values():
            path.reset()
        self._move_timer.Reset()
        self._interact_timer.Reset()
        self._debug_timer.Reset()
        self._current_npc_id = 0
        self._holding_bundle = False
        self._mission_started = False
        self._last_map_id = 0
        self._cinematic_detected = False

    def _CheckHeroInParty(self, hero_name):
        """
        Check if a specific hero is in the party.
        Args:
            hero_name (str): The name of the hero to check for (e.g., "Koss")
        Returns:
            bool: True if hero is in party, False otherwise
        """
        try:
            heroes = Party.GetHeroes()
            if not heroes:
                return False
            
            for hero in heroes:
                # Get the hero's name from the hero_id object
                if hasattr(hero, 'hero_id'):
                    name = hero.hero_id.GetName()
                    if name.lower() == hero_name.lower():
                        return True
            return False
        except Exception as e:
            return False

    def FindNearestNPC(self, x, y, max_distance=300, logger=None):
        """Find the nearest NPC at given coordinates."""
        scan_pos = (x, y)
        
        try:
            all_agents = AgentArray.GetAgentArray()
        except Exception as e:
            if logger:
                logger.Add(f"Error getting agent array: {e}", (1, 0, 0, 1), prefix="[Error]")
            return 0
        
        npcs = []
        for agent_id in all_agents:
            try:
                if not Agent.IsValid(agent_id):
                    continue
                if not Agent.IsLiving(agent_id):
                    continue
                if Agent.GetLoginNumber(agent_id) != 0:
                    continue  # Player, not NPC
                
                agent_pos = Agent.GetXY(agent_id)
                dist = Utils.Distance(scan_pos, agent_pos)
                
                if dist <= max_distance:
                    npcs.append((agent_id, dist))
            except:
                continue
        
        if npcs:
            npcs.sort(key=lambda x: x[1])
            return npcs[0][0]
        
        return 0

    def FindNearestGadget(self, x, y, max_distance=300, logger=None):
        """Find the nearest gadget at given coordinates."""
        scan_pos = (x, y)
        
        try:
            gadget_array = AgentArray.GetGadgetArray()
            gadget_array = AgentArray.Filter.ByDistance(gadget_array, scan_pos, max_distance)
            gadget_array = AgentArray.Sort.ByDistance(gadget_array, scan_pos)
            return gadget_array[0] if gadget_array else 0
        except Exception as e:
            if logger:
                logger.Add(f"Error in FindNearestGadget: {e}", (1, 0, 0, 1), prefix="[Error]")
            return 0

    def IsHoldingBundle(self, logger=None):
        """
        Check if the player is currently holding a bundle item (like oil).
        Returns True if holding a bundle, False otherwise.
        """
        try:
            agent_id = Player.GetAgentID()
            weapon_type_id, weapon_type_name = Agent.GetWeaponType(agent_id)
            
            # Debug log the actual values
            if logger and self._debug_timer.HasElapsed(2000):
                logger.Add(f"Weapon type: ID={weapon_type_id}, Name='{weapon_type_name}'", (0.7, 0.7, 1, 1), prefix="[Debug]")
                self._debug_timer.Reset()
            
            # Bundle types that indicate we're holding something
            bundle_type_names = ["Bundle", "Item", "Environmental", "Unknown", ""]
            
            if weapon_type_name in bundle_type_names:
                return True
            
            if weapon_type_id == 0:
                return True
                
            return False
            
        except Exception as e:
            if logger:
                logger.Add(f"Error checking bundle: {e}", (1, 0, 0, 1), prefix="[Error]")
            return False

    def _CheckMissionCompletion(self, bot, logger):
        """
        IMPROVED: Check if mission was completed.
        Detects:
        - Map change to ANY different map (not just outposts)
        - Party defeat
        - End cinematics
        """
        current_map = Map.GetMapID()
        
        # First call - initialize tracking
        if self._last_map_id == 0:
            self._last_map_id = current_map
            return False
        
        # Check for party defeat first
        if Party.IsPartyDefeated():
            logger.Add("Party was defeated!", (1, 0, 0, 1), prefix="[Defeat]")
            return True
        
        # Check for end cinematic (missions often end with a cutscene)
        if Map.IsInCinematic():
            if not self._cinematic_detected:
                logger.Add("End cinematic detected...", (0, 1, 1, 1), prefix="[Cinematic]")
                self._cinematic_detected = True
            # Don't return True yet - wait for map transition after cinematic
            return False
        
        # FIX: Check if map changed to ANY different map while in mission
        if self._mission_started and current_map != self.Mission_Map_ID:
            # We left the mission map!
            map_name = Map.GetMapName(current_map)
            if Map.IsOutpost():
                logger.Add(f"Mission Complete! Arrived at {map_name} (ID: {current_map})", (0, 1, 0, 1), prefix="[Victory]")
            else:
                logger.Add(f"Mission ended. Transitioned to {map_name} (ID: {current_map})", (0, 1, 0, 1), prefix="[Complete]")
            return True
        
        # Update tracking
        self._last_map_id = current_map
        return False

    def _VerifyCorrectMap(self, bot, logger):
        """
        Verify we're on the correct map for the current phase.
        Returns False and stops the bot if on wrong map.
        """
        current_map = Map.GetMapID()
        
        # If we're in mission phase (step >= 3), we should be on the mission map
        if self.step >= 3 and Map.IsExplorable():
            if current_map != self.Mission_Map_ID:
                map_name = Map.GetMapName(current_map)
                logger.Add(f"Wrong map detected (ID: {current_map} - {map_name}). Mission may have ended.", (1, 0.5, 0, 1), prefix="[End]")
                return False
        
        # If we're in outpost phase, verify we're at the right outpost
        if self.step < 3 and Map.IsOutpost():
            if current_map != self.Outpost_Map_ID:
                logger.Add(f"Wrong Map ({current_map}). Go to Chahbek Village Outpost.", (1, 0, 0, 1))
                return False
        
        return True

    def Execution_Routine(self, bot, logger):
        """Main execution routine."""
        current_map = Map.GetMapID()
        if current_map == 0:
            return

        # Check for mission completion (map change, defeat, etc.)
        if self._mission_started and self._CheckMissionCompletion(bot, logger):
            bot.is_running = False
            return

        # Handle map loading state
        if Map.IsMapLoading():
            return

        if Map.IsExplorable():
            # VERIFY we're on the correct mission map
            if current_map != self.Mission_Map_ID:
                map_name = Map.GetMapName(current_map)
                logger.Add(f"Not on mission map. Current: {map_name} (ID: {current_map}). Mission ended or wrong location.", (1, 0.5, 0, 1), prefix="[End]")
                bot.is_running = False
                return
            
            if self.step <= 2:
                if self.step < 3:
                    logger.Add("Mission Instance Detected. Starting Logic...", (0, 1, 0, 1))
                    self.step = 3
                    self.sub_state = 0
                    self._mission_started = True  # Mark that we've entered the mission
            
            self.ExecuteMissionLogic(bot, logger)
            return

        elif Map.IsOutpost():
            if current_map != self.Outpost_Map_ID:
                # We're in a different outpost - mission might have completed
                if self._mission_started:
                    map_name = Map.GetMapName(current_map)
                    logger.Add(f"Mission Complete! Arrived at {map_name}", (0, 1, 0, 1), prefix="[Victory]")
                else:
                    logger.Add(f"Wrong Map ({current_map}). Go to Chahbek Village Outpost.", (1, 0, 0, 1))
                bot.is_running = False
                return
            
            self.ExecuteOutpostLogic(bot, logger)
            return

    def ExecuteOutpostLogic(self, bot, logger):
        """Outpost logic with proper dialog handling."""
        
        if self.step == 1:
            if self.sub_state == 0:
                # --- PARTY CHECKS ---
                party_size = Party.GetPartySize()
                
                if party_size < 2:
                    logger.Add("Party too small! Add Heroes/Henchmen.", (1, 0, 0, 1))
                    bot.is_running = False
                    return

                # Check if Koss is in the party
                if not self._CheckHeroInParty("Koss"):
                    logger.Add("Koss is required for this mission! Add Koss to your party.", (1, 0, 0, 1), prefix="[Error]")
                    bot.is_running = False
                    return

                logger.Add("Party validated (Koss found). Finding Jahdugar...", (0, 1, 0, 1))
                self.sub_state = 1
                self.timer.Reset()
                self._move_timer.Reset()

            elif self.sub_state == 1:
                # FIND NPC
                npc_id = self.FindNearestNPC(
                    self.NPC_Jahdugar_Position[0],
                    self.NPC_Jahdugar_Position[1],
                    500,
                    logger
                )
                
                if npc_id == 0:
                    if self.timer.HasElapsed(2000):
                        logger.Add(f"Searching for {self.NPC_Starter_Name}...", (1, 1, 0, 1))
                        self.timer.Reset()
                    return
                
                self._current_npc_id = npc_id
                logger.Add(f"Found NPC ID: {npc_id}. Moving to talk...", (0, 1, 0, 1))
                self.sub_state = 2
                self._move_timer.Reset()

            elif self.sub_state == 2:
                # MOVE TO NPC
                npc_id = self._current_npc_id
                
                if not Agent.IsValid(npc_id):
                    logger.Add("NPC became invalid, re-searching...", (1, 0.5, 0, 1))
                    self.sub_state = 1
                    return
                
                player_pos = Player.GetXY()
                npc_pos = Agent.GetXY(npc_id)
                distance = Utils.Distance(player_pos, npc_pos)
                
                if distance > 250:
                    if self._move_timer.HasElapsed(1000):
                        logger.Add(f"Moving to NPC (distance: {distance:.0f})...", (0.7, 0.7, 1, 1), prefix="[Move]")
                        Player.Move(npc_pos[0], npc_pos[1])
                        self._move_timer.Reset()
                    return
                else:
                    logger.Add("Close enough to NPC. Targeting...", (0, 1, 0, 1))
                    self.sub_state = 3
                    self.timer.Reset()

            elif self.sub_state == 3:
                # TARGET NPC
                npc_id = self._current_npc_id
                Player.ChangeTarget(npc_id)
                logger.Add("Interacting with NPC...", (0, 1, 0, 1))
                self.sub_state = 4
                self.timer.Reset()

            elif self.sub_state == 4:
                # INTERACT TO OPEN DIALOG
                npc_id = self._current_npc_id
                
                if self.timer.HasElapsed(500):
                    Player.Interact(npc_id)
                    logger.Add("Waiting for dialog...", (0.7, 0.7, 1, 1))
                    self.sub_state = 5
                    self.timer.Reset()

            elif self.sub_state == 5:
                # SEND DIALOG
                if self.timer.HasElapsed(1500):
                    logger.Add(f"Sending dialog 0x{self.Dialog_TakeQuest:X}...", (0, 1, 0, 1))
                    Player.SendDialog(self.Dialog_TakeQuest)
                    self.sub_state = 6
                    self.timer.Reset()

            elif self.sub_state == 6:
                # WAIT FOR DIALOG RESPONSE
                if self.timer.HasElapsed(2000):
                    logger.Add("First dialog complete. Proceeding to step 2...", (0, 1, 0, 1))
                    self.step = 2
                    self.sub_state = 0
                    self.timer.Reset()

        elif self.step == 2:
            if self.sub_state == 0:
                # RE-FIND NPC
                npc_id = self.FindNearestNPC(
                    self.NPC_Jahdugar_Position[0],
                    self.NPC_Jahdugar_Position[1],
                    500,
                    logger
                )
                
                if npc_id == 0:
                    if self.timer.HasElapsed(2000):
                        logger.Add(f"Searching for {self.NPC_Starter_Name}...", (1, 1, 0, 1))
                        self.timer.Reset()
                    return
                
                self._current_npc_id = npc_id
                self.sub_state = 1
                self._move_timer.Reset()

            elif self.sub_state == 1:
                # MOVE TO NPC (if needed)
                npc_id = self._current_npc_id
                
                if not Agent.IsValid(npc_id):
                    self.sub_state = 0
                    return
                
                player_pos = Player.GetXY()
                npc_pos = Agent.GetXY(npc_id)
                distance = Utils.Distance(player_pos, npc_pos)
                
                if distance > 250:
                    if self._move_timer.HasElapsed(1000):
                        Player.Move(npc_pos[0], npc_pos[1])
                        self._move_timer.Reset()
                    return
                else:
                    self.sub_state = 2
                    self.timer.Reset()

            elif self.sub_state == 2:
                # TARGET AND INTERACT
                npc_id = self._current_npc_id
                Player.ChangeTarget(npc_id)
                self.sub_state = 3
                self.timer.Reset()

            elif self.sub_state == 3:
                # INTERACT
                if self.timer.HasElapsed(500):
                    Player.Interact(self._current_npc_id)
                    self.sub_state = 4
                    self.timer.Reset()

            elif self.sub_state == 4:
                # SEND MISSION START DIALOG
                if self.timer.HasElapsed(1500):
                    logger.Add(f"Sending dialog 0x{self.Dialog_StartMission:X} to start mission...", (0, 1, 0, 1))
                    Player.SendDialog(self.Dialog_StartMission)
                    self.sub_state = 5
                    self.timer.Reset()

            elif self.sub_state == 5:
                # WAIT FOR MISSION TO LOAD
                if self.timer.HasElapsed(3000):
                    logger.Add("Waiting for mission to load...", (0, 1, 0, 1))
                    self.step = 3
                    self.sub_state = 0

    def ExecuteMissionLogic(self, bot, logger):
        """Mission instance logic."""
        
        # Verify we're still on the mission map
        current_map = Map.GetMapID()
        if current_map != self.Mission_Map_ID:
            map_name = Map.GetMapName(current_map)
            logger.Add(f"Left mission map. Now at {map_name} (ID: {current_map})", (0, 1, 0, 1), prefix="[Complete]")
            bot.is_running = False
            return
        
        # Check for party defeat
        if Party.IsPartyDefeated():
            logger.Add("Party was defeated!", (1, 0, 0, 1), prefix="[Defeat]")
            bot.is_running = False
            return
        
        # --- COMBAT MOVEMENT PHASE ---
        if self.step == 3:
            self.ExecuteMove(self.paths["Step1"], 4, logger, "Clearing Group 1")
            
        elif self.step == 4:
            self.ExecuteMove(self.paths["Step2"], 5, logger, "Clearing Group 2")
            
        elif self.step == 5:
            self.ExecuteMove(self.paths["Step3"], 6, logger, "Moving to Gate")
            
        elif self.step == 6:
            self.ExecuteMove(self.paths["Step4"], 7, logger, "Moving to Docks")
            
        elif self.step == 7:
            self.ExecuteMove(self.paths["Step5"], 8, logger, "Approaching Oil Storage")

        # --- FIRST CATAPULT CYCLE ---
        elif self.step == 8:
            self.ExecuteMove(self.paths["ToOil"], 9, logger, "Going to Oil")

        elif self.step == 9:
            self._ExecuteOilPickup(10, logger, "Picking up Oil")

        elif self.step == 10:
            self.ExecuteMove(self.paths["ToCata1"], 11, logger, "Running to Catapult 1")

        elif self.step == 11:
            self._ExecuteGadgetInteract(
                self.Gadget_Catapult_1_Position,
                12,
                logger,
                "Loading Catapult 1",
                wait_ms=3000
            )

        elif self.step == 12:
            self._ExecuteGadgetInteract(
                self.Gadget_Catapult_1_Position,
                13,
                logger,
                "Firing Catapult 1!",
                wait_ms=1500
            )
            if self.step == 13:
                logger.Add("Catapult 1 Fired!", (0, 1, 1, 1))

        # --- SECOND CATAPULT CYCLE ---
        elif self.step == 13:
            self.ExecuteMove(self.paths["ToOil"], 14, logger, "Back for more Oil")

        elif self.step == 14:
            self._ExecuteOilPickup(15, logger, "Picking up Oil (2)")

        elif self.step == 15:
            self.ExecuteMove(self.paths["ToCata2"], 16, logger, "Running to Catapult 2")

        elif self.step == 16:
            self._ExecuteGadgetInteract(
                self.Gadget_Catapult_2_Position,
                17,
                logger,
                "Loading Catapult 2",
                wait_ms=3000
            )

        elif self.step == 17:
            self._ExecuteGadgetInteract(
                self.Gadget_Catapult_2_Position,
                18,
                logger,
                "Firing Catapult 2!",
                wait_ms=1500
            )
            if self.step == 18:
                logger.Add("Catapult 2 Fired!", (0, 1, 1, 1))

        # --- BOSS KILL PHASE ---
        elif self.step == 18:
            self.ExecuteMove(self.paths["ToBeach"], 19, logger, "Moving to Beach")

        elif self.step == 19:
            self.ExecuteMove(self.paths["ToCommander"], 20, logger, "Approaching Commander")

        elif self.step == 20:
            self.ExecuteMove(self.paths["KillCommander"], 21, logger, "Engaging Commander!")

        elif self.step == 21:
            # Stay in this step - map change detection will handle completion
            # The mission completes automatically when objectives are met
            if not hasattr(self, '_final_phase_logged') or not self._final_phase_logged:
                logger.Add("Commander area reached. Waiting for mission completion...", (0, 1, 1, 1), prefix="[Final]")
                self._final_phase_logged = True

    def _ExecuteOilPickup(self, next_step, logger, log_msg):
        """
        Special handler for picking up oil with proper bundle detection.
        """
        if self.sub_state == 0:
            # Find the oil gadget
            gadget_id = self.FindNearestGadget(
                self.Gadget_Oil_Position[0], 
                self.Gadget_Oil_Position[1], 
                300, 
                logger
            )
            
            if gadget_id == 0:
                if self._interact_timer.HasElapsed(2000):
                    logger.Add(f"Searching for oil gadget...", (1, 1, 0, 0.7))
                    self._interact_timer.Reset()
                return
            
            logger.Add(f"{log_msg}...", prefix="[Interact]")
            Player.Interact(gadget_id)
            self.timer.Reset()
            self.sub_state = 1
            
        elif self.sub_state == 1:
            # Wait a moment for pickup animation
            if self.timer.HasElapsed(1500):
                self.sub_state = 2
                self.timer.Reset()
                
        elif self.sub_state == 2:
            # Check if we're holding the oil
            if self.IsHoldingBundle(logger):
                logger.Add("Oil acquired!", (0, 1, 0, 1))
                self._holding_bundle = True
                self.sub_state = 0
                self.step = next_step
            else:
                # Not holding - retry
                if self._interact_timer.HasElapsed(2000):
                    logger.Add("Failed to pick up oil. Retrying...", (1, 0.5, 0, 1))
                    self._interact_timer.Reset()
                    self.sub_state = 0  # Go back to find and interact

    def _ExecuteGadgetInteract(self, position, next_step, logger, log_msg, wait_ms=1500):
        """Handle gadget interaction (for catapults)."""
        if self.sub_state == 0:
            gadget_id = self.FindNearestGadget(position[0], position[1], 300, logger)
            
            if gadget_id == 0:
                if self._interact_timer.HasElapsed(2000):
                    logger.Add(f"Searching for gadget near {position}...", (1, 1, 0, 0.7))
                    self._interact_timer.Reset()
                return
            
            logger.Add(f"{log_msg}...", prefix="[Interact]")
            Player.Interact(gadget_id)
            self.timer.Reset()
            self.sub_state = 1
            
        elif self.sub_state == 1:
            if self.timer.HasElapsed(wait_ms):
                # For catapult loading - we no longer hold the bundle after loading
                if "Loading" in log_msg:
                    self._holding_bundle = False
                
                self.sub_state = 0
                self.step = next_step
