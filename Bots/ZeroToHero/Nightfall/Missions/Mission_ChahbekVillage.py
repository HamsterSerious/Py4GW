import time
from Py4GWCoreLib import *
from Bots.ZeroToHero.Shared.MissionContext import BaseMission, MissionContext

# Import GLOBAL_CACHE safely
try:
    from Py4GWCoreLib import GLOBAL_CACHE
except ImportError:
    from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

class ChahbekVillage(BaseMission, MissionContext):
    def GetInfo(self):
        return {
            "Name": "Chahbek Village",
            "Description": "Save the village by defeating the corsairs and sinking their ships.",
            "Recommended_Builds": ["Any", "Koss Required"],
            "HM_Tips": "Make sure to have strong Healers, as the Sunspear Recruits tend to die easy."
        }

    # --- CONFIGURATION ---
    Outpost_Map_ID = 544
    Mission_Map_ID = 544
    
    # NPC Names (Dynamic Lookup)
    NPC_Starter_Name = "First Spear Jahdugar"
    
    # Gadgets (Static in Mission)
    Gadget_Oil = 9
    Gadget_Catapult_1 = 5
    Gadget_Catapult_2 = 6
    
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
        "ToCata1": [(-1713, -2533)],
        "ToCata2": [(-1751, -4124)],
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

    def FindAgentByName(self, name, logger=None):
        """Robustly find an agent by name, requesting names if missing."""
        agents = []
        if GLOBAL_CACHE:
            agents = GLOBAL_CACHE.AgentArray.GetAgentArray()
        else:
            agents = AgentArray.GetAgentArray()
            
        debug_names = []
        found_id = 0
        
        # DEBUG: Log total raw agents if logger is active
        if logger:
             logger.Add(f"Debug: Agent Array Size: {len(agents)}", (1, 1, 1, 0.5))

        for i, agent_id in enumerate(agents):
            # Debug: check first few items to ensure we are getting IDs
            if logger and i < 3:
                 try:
                     logger.Add(f"Debug Agent[{i}]: ID={agent_id}, Valid={Agent.IsValid(agent_id)}", (1, 1, 1, 0.5))
                 except:
                     pass

            if not Agent.IsValid(agent_id): 
                continue
            
            # Filter for Living Agents only (NPCs are living) to avoid crashes on Gadgets
            if not Agent.IsLiving(agent_id):
                continue

            # Check if NPC (Login Number == 0)
            if not Agent.IsNPC(agent_id): 
                continue
            
            agent_name = Agent.GetName(agent_id)
            
            # Handle unknown names
            if not agent_name or agent_name in ["Unknown", ""]:
                Agent.RequestName(agent_id)
                display_name = "Unknown"
            else:
                display_name = agent_name

            # If logger is present, collect names for debugging
            if logger:
                debug_names.append(f"[{agent_id}] {display_name}")

            # Check match only if name is valid
            if found_id == 0 and display_name != "Unknown" and name.lower() in display_name.lower():
                found_id = agent_id
                # If we are logging, we continue to collect names for debug. 
                # If not logging, we can return immediately.
                if not logger:
                    return found_id
        
        # Log visible NPCs if we didn't find the target and logging is requested
        if logger and found_id == 0:
            if debug_names:
                # Log in chunks to avoid truncation if list is long
                chunk_str = ', '.join(debug_names[:10]) # First 10
                logger.Add(f"Visible NPCs ({len(debug_names)}): {chunk_str}...", (1, 1, 1, 0.5))
            else:
                logger.Add(f"Scanning: No NPCs visible (out of {len(agents)} agents)", (1, 0.5, 0, 1))
            
        return found_id

    def Execution_Routine(self, bot, logger):
        # -----------------------------------------------------------------------
        # MAP STATE DETECTION
        # -----------------------------------------------------------------------
        current_map = Map.GetMapID()
        if current_map == 0: return # Loading/Invalid

        # 1. DETECT MISSION INSTANCE (Prioritize this check)
        # Even if IDs are same, IsExplorable() is the source of truth for "In Mission"
        if Map.IsExplorable():
            if self.step <= 2: # If we just loaded in, skip Outpost steps
                if self.step < 3:
                    logger.Add("Mission Instance Detected. Starting Logic...", (0, 1, 0, 1))
                    self.step = 3
                    self.sub_state = 0 # Reset any interaction states
            
            # Mission Loop
            self.ExecuteMissionLogic(bot, logger)
            return

        # 2. DETECT OUTPOST
        elif Map.IsOutpost():
            if current_map != self.Outpost_Map_ID:
                logger.Add(f"Wrong Map ({current_map}). Go to Chahbek Village Outpost.", (1, 0, 0, 1))
                bot.is_running = False
                return
            
            # Outpost Loop
            self.ExecuteOutpostLogic(bot, logger)
            return

    def ExecuteOutpostLogic(self, bot, logger):
        """Logic for the Outpost (Party Check, Dialogs)"""
        if self.step == 1:
            if self.sub_state == 0:
                # --- PARTY CHECKS ---
                party_size = 0
                if GLOBAL_CACHE:
                    party_size = len(GLOBAL_CACHE.Party.GetPlayers()) + len(GLOBAL_CACHE.Party.GetHeroes()) + len(GLOBAL_CACHE.Party.GetHenchmen())
                else:
                    party_size = Party.GetPartySize()
                
                if party_size < 2:
                    logger.Add("Party too small! Add Heroes.", (1, 0, 0, 1))
                    bot.is_running = False
                    return

                # --- KOSS CHECK ---
                has_koss = False
                if GLOBAL_CACHE:
                    heroes = GLOBAL_CACHE.Party.GetHeroes()
                else:
                    heroes = Party.GetHeroes()

                for hero in heroes:
                     try:
                         # 1. Try PyParty.Hero.hero_id (PyAgent object)
                         if hasattr(hero, 'hero_id'):
                             name = hero.hero_id.GetName()
                             if name and "Koss" in name:
                                 has_koss = True
                                 break
                         # 2. Try AgentID lookup if GLOBAL_CACHE is active
                         if not has_koss and GLOBAL_CACHE:
                             hero_agent_id = hero.agent_id
                             if hasattr(GLOBAL_CACHE.Party.Heroes, "GetNameByAgentID"):
                                name = GLOBAL_CACHE.Party.Heroes.GetNameByAgentID(hero_agent_id)
                                if name and "Koss" in name:
                                     has_koss = True
                                     break
                         # 3. Fallback: Check Agent Name directly
                         if not has_koss:
                             if Agent.IsValid(hero.agent_id):
                                 name = Agent.GetName(hero.agent_id)
                                 if name and "Koss" in name:
                                     has_koss = True
                                     break
                     except:
                         pass

                if not has_koss:
                    logger.Add("Koss is mandatory! Please add him.", (1, 0, 0, 1))
                    bot.is_running = False
                    return
                
                self.sub_state = 1 # Checks Passed

            elif self.sub_state == 1:
                # Find NPC ID Dynamically using robust local method
                should_log = self.timer.HasElapsed(1000)
                npc_id = self.FindAgentByName(self.NPC_Starter_Name, logger if should_log else None)
                
                if npc_id == 0:
                    if should_log:
                        logger.Add(f"Finding {self.NPC_Starter_Name}...", (1, 1, 0, 1))
                        self.timer.Reset()
                    return

                # Talk to Starter -> Send 0x81
                if self.ExecuteDialog(npc_id, self.Dialog_TakeQuest, 2000, 2, logger):
                    pass 

        elif self.step == 2:
            # Find NPC ID Dynamically (Re-check in case it changed/we moved)
            should_log = self.timer.HasElapsed(1000)
            npc_id = self.FindAgentByName(self.NPC_Starter_Name, logger if should_log else None)
            
            if npc_id == 0:
                 if should_log:
                    logger.Add(f"Finding {self.NPC_Starter_Name}...", (1, 1, 0, 1))
                    self.timer.Reset()
                 return

            # Send 0x84 to Enter Mission
            if self.ExecuteDialog(npc_id, self.Dialog_StartMission, 5000, 3, logger):
                logger.Add("Entering Mission...", (0, 1, 0, 1))

    def ExecuteMissionLogic(self, bot, logger):
        """Logic for the Mission Instance"""
        
        # --- COMBAT MOVEMENT ---
        if self.step == 3:
            self.ExecuteMove(self.paths["Step1"], 4, logger, "Clearing Group 1")
            
        elif self.step == 4:
            self.ExecuteMove(self.paths["Step2"], 5, logger, "Clearing Group 2")
            
        elif self.step == 5:
            self.ExecuteMove(self.paths["Step3"], 6, logger, "Moving to Gate")
            
        elif self.step == 6:
            self.ExecuteMove(self.paths["Step4"], 7, logger, "Moving to Docks")
            
        elif self.step == 7:
            self.ExecuteMove(self.paths["Step5"], 8, logger, "Approaching Oil")

        # --- MECHANICS (Oil & Catapults) ---
        elif self.step == 8:
            if self.ExecuteMove(self.paths["ToOil"], 9, logger, "Going to Oil"):
                pass

        elif self.step == 9:
            if self.ExecuteInteract(self.Gadget_Oil, 1500, 10, logger, "Picking up Oil"):
                agent_id = Player.GetAgentID()
                _, weapon_type = Agent.GetWeaponType(agent_id)
                if weapon_type not in ["Bundle", "Item", "Environmental"]:
                    logger.Add("Failed to pick up Oil. Retrying...", (1, 0.5, 0, 1))
                    self.step = 9 
                    self.sub_state = 0
                else:
                    logger.Add("Oil Acquired.", (0, 1, 0, 1))

        elif self.step == 10:
            self.ExecuteMove(self.paths["ToCata1"], 11, logger, "Running to Catapult 1")

        elif self.step == 11:
            if self.ExecuteInteract(self.Gadget_Catapult_1, 3000, 12, logger, "Loading Catapult"):
                pass

        elif self.step == 12:
            if self.ExecuteInteract(self.Gadget_Catapult_1, 1000, 13, logger, "Firing Catapult"):
                 logger.Add("Catapult 1 Fired!", (0, 1, 1, 1))

        # --- SECOND CATAPULT CYCLE ---
        elif self.step == 13:
             self.ExecuteMove(self.paths["ToOil"], 14, logger, "Back for more Oil")

        elif self.step == 14:
            if self.ExecuteInteract(self.Gadget_Oil, 1500, 15, logger, "Picking up Oil (2)"):
                 agent_id = Player.GetAgentID()
                 _, weapon_type = Agent.GetWeaponType(agent_id)
                 if weapon_type not in ["Bundle", "Item", "Environmental"]:
                    self.step = 14
                    self.sub_state = 0

        elif self.step == 15:
            self.ExecuteMove(self.paths["ToCata2"], 16, logger, "Running to Catapult 2")

        elif self.step == 16:
            if self.ExecuteInteract(self.Gadget_Catapult_2, 3000, 17, logger, "Loading Catapult 2"):
                pass

        elif self.step == 17:
             if self.ExecuteInteract(self.Gadget_Catapult_2, 1000, 18, logger, "Firing Catapult 2"):
                 logger.Add("Catapult 2 Fired!", (0, 1, 1, 1))

        # --- BOSS KILL ---
        elif self.step == 18:
            self.ExecuteMove(self.paths["ToBeach"], 19, logger, "Moving to Beach")

        elif self.step == 19:
            self.ExecuteMove(self.paths["ToCommander"], 20, logger, "Approaching Commander")

        elif self.step == 20:
            self.ExecuteMove(self.paths["KillCommander"], 21, logger, "Kill Commander!")

        elif self.step == 21:
            logger.Add("Mission Complete!", (0, 1, 0, 1))
            bot.is_running = False