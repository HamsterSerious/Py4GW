import sys
import os
import time
from collections import deque

# --- PATH SETUP ---
try:
    current_file_path = os.path.abspath(__file__)
except NameError:
    import inspect
    try:
        current_file_path = os.path.abspath(sys.argv[0])
    except:
        current_file_path = os.getcwd()

current_dir = os.path.dirname(current_file_path)

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
# ------------------

import Py4GW
import PyImGui
from Py4GWCoreLib import *

# Try importing GLOBAL_CACHE
try:
    from Py4GWCoreLib import GLOBAL_CACHE
except ImportError:
    try:
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    except ImportError:
        GLOBAL_CACHE = None
        Py4GW.Console.Log("MissionRunner", "Could not import GLOBAL_CACHE!", Py4GW.Console.MessageType.Error)


try:
    from Shared.MissionLoader import MissionLoader
except ImportError as e:
    Py4GW.Console.Log("MissionRunner", f"Import Error: {e}. Check folder structure.", Py4GW.Console.MessageType.Error)
    class MissionLoader:
        @staticmethod
        def GetMissionsForCampaign(c): return []

# Configuration
MODULE_NAME = "ZeroToHero Mission Runner"
WINDOW_SIZE = (600, 500)

class LogConsole:
    """
    A scrollable log console for ImGui.
    """
    def __init__(self, max_history=1000):
        self.logs = [] # List of (text, color_tuple)
        self.max_history = max_history
        self.auto_scroll = True
        self.scroll_to_bottom = False

    def Add(self, message, color=(1.0, 1.0, 1.0, 1.0), prefix="[Info]"):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        formatted_msg = f"[{timestamp}] {prefix} {message}"
        
        self.logs.append((formatted_msg, color))
        if len(self.logs) > self.max_history:
            self.logs.pop(0)
            
        self.scroll_to_bottom = True
        
        # Also log to main Py4GW console
        msg_type = Py4GW.Console.MessageType.Info
        if "Error" in prefix: msg_type = Py4GW.Console.MessageType.Error
        elif "Warn" in prefix: msg_type = Py4GW.Console.MessageType.Warning
        Py4GW.Console.Log("MissionRunner", formatted_msg, msg_type)

    def Draw(self):
        # Draw the logs
        for msg, color in self.logs:
            PyImGui.text_colored(msg, color)
            
        # Auto-scroll logic
        if self.auto_scroll and self.scroll_to_bottom:
            PyImGui.set_scroll_here_y(1.0)
            self.scroll_to_bottom = False

logger = LogConsole()

class BotState:
    def __init__(self):
        self.is_running = False
        self.selected_campaign = "Nightfall"
        self.selected_mission_index = 0
        self.is_hard_mode = False
        self.mission_list = []
        self.current_mission_module = None
        
        # UI State
        self.window_module = ImGui.WindowModule(MODULE_NAME, window_name=MODULE_NAME, window_size=WINDOW_SIZE)
        
        # Load Missions on Init
        self.RefreshMissions()

    def RefreshMissions(self):
        self.mission_list = MissionLoader.GetMissionsForCampaign(self.selected_campaign)
        if self.selected_mission_index >= len(self.mission_list):
            self.selected_mission_index = 0
        self.UpdateCurrentMission()

    def UpdateCurrentMission(self):
        if self.mission_list and self.selected_mission_index < len(self.mission_list):
            mission_name, module = self.mission_list[self.selected_mission_index]
            self.current_mission_module = module()
        else:
            self.current_mission_module = None

    def ToggleHardMode(self, target_state):
        """Attempts to set the game's Hard Mode state and updates UI accordingly."""
        if not GLOBAL_CACHE:
             logger.Add("GLOBAL_CACHE not available. Cannot toggle Hard Mode.", (1.0, 0.0, 0.0, 1.0), prefix="[Error]")
             return

        if GLOBAL_CACHE.Map.IsOutpost():
            self.is_hard_mode = target_state
            
            if target_state: # Enabling Hard Mode
                logger.Add("Attempting to switch to Hard Mode...", prefix="[System]")
                
                # Check if unlocked first using GLOBAL_CACHE
                if not GLOBAL_CACHE.Party.IsHardModeUnlocked():
                    logger.Add("Hard Mode is NOT unlocked for this character/campaign!", (1.0, 0.0, 0.0, 1.0), prefix="[Error]")
                    self.is_hard_mode = False # Revert UI checkbox
                    return

                try:
                    GLOBAL_CACHE.Party.SetHardMode()
                    logger.Add("Hard Mode enabled.", (0.0, 1.0, 0.0, 1.0), prefix="[System]")
                except Exception as e:
                    logger.Add(f"SetHardMode failed: {e}", (1.0, 0.0, 0.0, 1.0), prefix="[Error]")
                    self.is_hard_mode = False # Revert on failure
            else: # Disabling Hard Mode (Normal Mode)
                logger.Add("Switching to Normal Mode...", prefix="[System]")
                try:
                    GLOBAL_CACHE.Party.SetNormalMode()
                    logger.Add("Normal Mode enabled.", (0.0, 1.0, 0.0, 1.0), prefix="[System]")
                except Exception as e:
                    logger.Add(f"SetNormalMode failed: {e}", (1.0, 0.0, 0.0, 1.0), prefix="[Error]")
                
        else:
            logger.Add("Cannot switch Hard Mode while in Explorable/Mission.", (1.0, 0.5, 0.0, 1.0), prefix="[Warn]")
            if target_state != self.is_hard_mode:
                 self.is_hard_mode = not target_state # Revert state if map prevents change

bot_state = BotState()

def DrawBriefingPanel():
    """Displays the mission briefing text."""
    if not bot_state.current_mission_module:
        PyImGui.text_colored("No mission selected.", (1.0, 0.0, 0.0, 1.0))
        return

    info = bot_state.current_mission_module.GetInfo()
    
    # Title
    font_pushed = False
    if hasattr(bot_state.window_module, 'font_header') and bot_state.window_module.font_header:
        try:
            PyImGui.push_font(bot_state.window_module.font_header)
            font_pushed = True
        except: pass
            
    PyImGui.text_colored(info.get("Name", "Unknown Mission"), (1.0, 1.0, 0.0, 1.0))
    
    if font_pushed:
        PyImGui.pop_font()
    
    PyImGui.separator()
    PyImGui.text_wrapped(info.get("Description", "No description available."))
    PyImGui.spacing()
    
    if "Recommended_Builds" in info:
        PyImGui.text_colored("Recommended Setup:", (0.0, 1.0, 1.0, 1.0))
        for build in info["Recommended_Builds"]:
            PyImGui.bullet_text(build)
    
    PyImGui.spacing()
    
    if bot_state.is_hard_mode:
        PyImGui.text_colored("Hard Mode Tips:", (1.0, 0.5, 0.0, 1.0))
        PyImGui.text_wrapped(info.get("HM_Tips", "No specific HM tips."))
    else:
        PyImGui.text_disabled("Enable Hard Mode to see HM specific tips.")

def DrawWindow():
    global bot_state
    
    if bot_state.window_module.first_run:
        PyImGui.set_next_window_size(WINDOW_SIZE[0], WINDOW_SIZE[1])
        bot_state.window_module.first_run = False

    if PyImGui.begin(MODULE_NAME, bot_state.window_module.window_flags):
        
        # --- TOP SECTION ---
        available_height = PyImGui.get_content_region_avail()[1]
        top_section_height = max(200.0, available_height - 150.0) 

        # --- LEFT COLUMN: Settings ---
        PyImGui.begin_child("Settings", (250.0, top_section_height), True)
        
        PyImGui.text("Campaign Selection")
        campaigns = ["Nightfall", "Factions", "Prophecies", "EyeOfTheNorth"]
        
        if PyImGui.begin_combo("##CampaignCombo", bot_state.selected_campaign, 0):
            for camp in campaigns:
                if PyImGui.selectable(camp, camp == bot_state.selected_campaign, 0, (0, 0)):
                    bot_state.selected_campaign = camp
                    bot_state.RefreshMissions()
            PyImGui.end_combo()

        PyImGui.spacing()
        PyImGui.separator()
        PyImGui.spacing()

        PyImGui.text("Mission Selection")
        mission_names = [m[0] for m in bot_state.mission_list] if bot_state.mission_list else ["No Missions Found"]
        
        if mission_names:
            new_index = PyImGui.combo("##MissionCombo", bot_state.selected_mission_index, mission_names)
            if new_index != bot_state.selected_mission_index:
                bot_state.selected_mission_index = new_index
                bot_state.UpdateCurrentMission()

        PyImGui.spacing()
        PyImGui.separator()
        PyImGui.spacing()

        # Hard Mode Logic
        clicked = PyImGui.checkbox("Hard Mode (HM)", bot_state.is_hard_mode)
        if clicked != bot_state.is_hard_mode:
            bot_state.ToggleHardMode(clicked)

        PyImGui.spacing()
        PyImGui.separator()
        PyImGui.spacing()
        
        # Start/Stop Logic
        if not bot_state.is_running:
            if PyImGui.button("START MISSION", 230, 50):
                if bot_state.current_mission_module:
                    bot_state.is_running = True
                    # --- RESET MISSION STATE ---
                    if hasattr(bot_state.current_mission_module, "Reset"):
                        bot_state.current_mission_module.Reset()
                    
                    info = bot_state.current_mission_module.GetInfo()
                    mission_name = info.get("Name", "Unknown Mission")
                    logger.Add(f"Starting {mission_name}...", (0.0, 1.0, 0.0, 1.0), prefix="[Start]")
                else:
                    logger.Add("Cannot start: No mission selected.", (1.0, 0.0, 0.0, 1.0), prefix="[Error]")
                    bot_state.is_running = False
        else:
            if PyImGui.button("STOP BOT", 230, 50):
                bot_state.is_running = False
                logger.Add("Bot Stopped by User.", (1.0, 0.5, 0.0, 1.0), prefix="[Stop]")
            
            # Execute Routine
            if bot_state.current_mission_module:
                try:
                    bot_state.current_mission_module.Execution_Routine(bot_state, logger)
                except Exception as e:
                    logger.Add(f"Crash in Routine: {e}", (1.0, 0.0, 0.0, 1.0), prefix="[Crash]")
                    bot_state.is_running = False

        PyImGui.end_child()

        PyImGui.same_line(0.0, -1.0)

        # --- RIGHT COLUMN: Briefing ---
        PyImGui.begin_child("Briefing", (0.0, top_section_height), True)
        DrawBriefingPanel()
        PyImGui.end_child()
        
        # --- BOTTOM ROW: Logs ---
        PyImGui.separator()
        PyImGui.text("Mission Logs")
        
        PyImGui.begin_child("Logs", (0.0, 0.0), True) 
        logger.Draw()
        PyImGui.end_child()

    PyImGui.end()

def main():
    DrawWindow()
    # Process Action Queue for GLOBAL_CACHE commands
    ActionQueueManager().ProcessQueue("ACTION")

if __name__ == "__main__":
    main()