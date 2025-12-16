import Py4GW
import PyImGui
from Py4GWCoreLib import *
from Py4GWCoreLib.Botting import BottingClass
from Py4GWCoreLib.ImGui_src.WindowModule import WindowModule
from Py4GWCoreLib.ImGui_src.IconsFontAwesome5 import IconsFontAwesome5
from Py4GWCoreLib.py4gwcorelib_src.Color import Color
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

# --- Import Managers ---
try:
    from Bots.ZeroToHero.TaskManager import TaskRegistry
    from Bots.ZeroToHero.Modules.Common.TeamManager import TeamManager
except ImportError:
    from TaskManager import TaskRegistry
    from Modules.Common.TeamManager import TeamManager

# --- Import Common Modules ---
try:
    from Bots.ZeroToHero.Modules.Common.Movement import Movement
    from Bots.ZeroToHero.Modules.Common.Combat import Combat
    from Bots.ZeroToHero.Modules.Common.Transition import Transition
except ImportError:
    from Modules.Common.Movement import Movement
    from Modules.Common.Combat import Combat
    from Modules.Common.Transition import Transition

# --- Configuration ---
BOT_NAME = "ZeroToHero"
WINDOW_SIZE = (400, 700) 

# --- Theme Colors ---
WINDOW_BG_COLOR       = Color(28,  28,  28, 230).to_tuple_normalized()
FRAME_BG_COLOR        = Color(48,  48,  48, 230).to_tuple_normalized()
FRAME_HOVER_COLOR     = Color(68,  68,  68, 230).to_tuple_normalized()
FRAME_ACTIVE_COLOR    = Color(58,  58,  58, 230).to_tuple_normalized()
BODY_TEXT_COLOR       = Color(139, 131, 99, 255).to_tuple_normalized()
HEADER_COLOR          = Color(136, 117, 44, 255).to_tuple_normalized()
ICON_COLOR            = Color(177, 152, 55, 255).to_tuple_normalized()
DISABLED_TEXT_COLOR   = Color(140, 140, 140, 255).to_tuple_normalized()
SEPARATOR_COLOR       = Color(90,  90,  90, 255).to_tuple_normalized()
BUTTON_COLOR          = Color(33, 51, 58, 255).to_tuple_normalized()
BUTTON_HOVER_COLOR    = Color(140, 140, 140, 255).to_tuple_normalized()
BUTTON_ACTIVE_COLOR   = Color(90,  90,  90, 255).to_tuple_normalized()

# Mode indicator colors
HM_COLOR = (1.0, 0.3, 0.3, 1.0)  # Red for Hard Mode
NM_COLOR = (0.3, 1.0, 0.3, 1.0)  # Green for Normal Mode
WARN_COLOR = (1.0, 0.7, 0.0, 1.0) # Orange for Warnings

# --- Sorting Order ---
CAMPAIGN_ORDER = ["Prophecies", "Factions", "Nightfall", "Eye of the North", "EyeOfTheNorth", "Extra"]

class ZeroToHeroBot(BottingClass):
    def __init__(self):
        super().__init__(bot_name=BOT_NAME)
        
        # --- UI Setup ---
        self.window_module = WindowModule(BOT_NAME, window_name="Zero To Hero Dashboard", window_size=WINDOW_SIZE)
        self.show_queue_window = False
        self.show_task_info_window = False 
        
        # --- Notification Queue ---
        self.pending_notifications = [] 
        
        # --- Managers ---
        self.task_manager = TaskRegistry()
        self.team_manager = TeamManager(self)
        self.team_manager_initialized = False
        
        # --- Common Behavior Modules ---
        self.movement = Movement()
        self.combat = Combat()
        self.transition = Transition()
        
        # --- State Management ---
        self.is_running = False
        self.is_paused = False
        self.current_task_instance = None
        self.current_task_name = "Ready."
        self.current_step_name = "Idle"
        
        # --- Settings ---
        self.use_hard_mode = False
        
        # --- UI Selections ---
        raw_campaigns = self.task_manager.get_campaigns()
        self.campaign_list = sorted(raw_campaigns, key=lambda x: CAMPAIGN_ORDER.index(x) if x in CAMPAIGN_ORDER else 999)
        
        self.selected_campaign_idx = 0
        self.current_campaign = self.campaign_list[0] if self.campaign_list else "None"
        
        self.filter_options = ["All", "Mission", "Quest"]
        self.selected_filter_idx = 0 
        
        self.task_list = self.GetFilteredTasks()
        self.selected_task_idx = 0
        self.selected_task_name = self.task_list[0] if self.task_list else "None"

        # --- FSM Initialization ---
        self.config.FSM.AddState(
            name="Bot_Idle_Loop",
            execute_fn=lambda: None,
            exit_condition=lambda: False,
            run_once=False
        )

        Py4GW.Console.Log(BOT_NAME, "Bot Initialized.", Py4GW.Console.MessageType.Info)

    def GetFilteredTasks(self):
        all_tasks = self.task_manager.get_tasks_for_campaign(self.current_campaign)
        filter_type = self.filter_options[self.selected_filter_idx]
        
        if filter_type == "All":
            return all_tasks
            
        filtered_list = []
        for task_name in all_tasks:
            try:
                task_class = self.task_manager.available_tasks[self.current_campaign][task_name]
                if task_class().task_type == filter_type:
                    filtered_list.append(task_name)
            except:
                continue
                
        return filtered_list

    def Routine(self):
        pass

    def UpdateTaskExecution(self):
        if not self.is_running or self.is_paused:
            return

        if not self.current_task_instance:
            next_task = self.task_manager.get_next_task()
            
            if next_task:
                self.current_task_instance = next_task
                self.current_task_name = next_task.name
                
                if next_task.task_type == "Mission":
                    mode_str = "HM" if next_task.use_hard_mode else "NM"
                    Py4GW.Console.Log(BOT_NAME, f"Starting Mission: {next_task.name} [{mode_str}]", Py4GW.Console.MessageType.Info)
                else:
                    Py4GW.Console.Log(BOT_NAME, f"Starting Task: {next_task.name}", Py4GW.Console.MessageType.Info)
                
                ready, reason = next_task.PreRunCheck(self)
                if not ready:
                    Py4GW.Console.Log(BOT_NAME, f"Task Skipped ({reason})", Py4GW.Console.MessageType.Warning)
                    self.current_task_instance = None
                    return

                self.config.FSM.AddManagedCoroutine("MainTask", next_task.Execution_Routine(self))
            else:
                self.current_task_name = "Queue Finished."
                self.StopBot()
                return

        if self.current_task_instance:
            if self.current_task_instance.finished:
                Py4GW.Console.Log(BOT_NAME, f"Task Finished: {self.current_task_instance.name}", Py4GW.Console.MessageType.Info)
                self.config.FSM.RemoveManagedCoroutine("MainTask")
                self.current_task_instance = None
            elif self.current_task_instance.failed:
                Py4GW.Console.Log(BOT_NAME, f"Task Failed: {self.current_task_instance.name}", Py4GW.Console.MessageType.Error)
                self.StopBot()

    def DrawUI(self):
        if self.window_module.first_run:
            PyImGui.set_next_window_size(WINDOW_SIZE[0], WINDOW_SIZE[1])
            self.window_module.first_run = False

        self.PushStyles()

        if self.window_module.begin():
            self.DrawHeader()
            self.DrawControls()
            PyImGui.separator()
            self.DrawConfiguration()
            PyImGui.separator()
            self.DrawStatus()

        self.window_module.end()
        
        if self.show_queue_window:
            self.DrawQueueWindow()

        if self.show_task_info_window:
            self.DrawTaskInfoWindow()
            
        self.team_manager.DrawWindow()
        
        # --- Notification Window (Priority) ---
        if self.pending_notifications:
            self.DrawNotificationWindow()
            
        self.PopStyles()

    def DrawNotificationWindow(self):
        """Draws the mandatory loadout warning window."""
        PyImGui.push_style_color(PyImGui.ImGuiCol.TitleBg, WARN_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.TitleBgActive, WARN_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, (0, 0, 0, 1)) 
        
        if PyImGui.begin("REQUIREMENT WARNING", 0):
            PyImGui.pop_style_color(3) 
            
            data = self.pending_notifications[0]
            name = data['name']
            mode = data['mode']
            reqs = data['requirements']
            
            PyImGui.text_colored(f"Mission: {name} [{mode}]", HEADER_COLOR)
            PyImGui.separator()
            PyImGui.dummy(0, 5)
            
            PyImGui.text_wrapped("This mission requires a specific loadout to succeed!")
            PyImGui.dummy(0, 5)
            
            PyImGui.text_colored("Requirements:", WARN_COLOR)
            
            # --- 1. Player Build ---
            if "Player_Build" in reqs and reqs["Player_Build"]:
                PyImGui.bullet()
                PyImGui.text("Player Build:")
                
                try:
                    player_id = GLOBAL_CACHE.Player.GetAgentID()
                    prim, sec = GLOBAL_CACHE.Agent.GetProfessionNames(player_id)
                except:
                    prim = "Unknown"

                build_code = None
                raw_build_data = reqs["Player_Build"]
                
                if isinstance(raw_build_data, dict):
                    if prim in raw_build_data:
                        build_code = raw_build_data[prim]
                    elif "Any" in raw_build_data:
                        build_code = raw_build_data["Any"]
                    else:
                        build_code = "No build for your profession"
                else:
                    build_code = str(raw_build_data)

                PyImGui.indent(0.0) 
                if build_code:
                    # Click to Copy Logic
                    PyImGui.text_colored(f"[{prim}]: {build_code}", (0.7, 1.0, 0.7, 1.0))
                    if PyImGui.is_item_hovered():
                        PyImGui.set_tooltip("Click to Copy Build Code")
                    if PyImGui.is_item_clicked(0): # Fix: Pass 0 for Left Click
                        PyImGui.set_clipboard_text(build_code)
                        Py4GW.Console.Log(BOT_NAME, "Build code copied to clipboard.", Py4GW.Console.MessageType.Info)
                    
                    if len(build_code) > 10 and " " not in build_code and build_code != "Any":
                        if PyImGui.button(f"Test Loadout ({prim})", -1, 0):
                            expected = reqs.get("Expected_Skills", 8)
                            self.team_manager.test_routine = self.team_manager.TestPlayerLoadout(build_code, expected)

                        PyImGui.text_disabled("(Warning: Overwrites current skills)")
                else:
                    PyImGui.text_colored("No mandatory build for your profession.", (0.7, 0.7, 0.7, 1.0))
                PyImGui.unindent(0.0) 
            
            # --- 2. Required Equipment (Runes/Insignias) ---
            if "Equipment" in reqs and reqs["Equipment"]:
                PyImGui.dummy(0, 5)
                PyImGui.bullet()
                PyImGui.text("Equipment / Runes:")
                PyImGui.indent(0.0)
                
                eq_data = reqs["Equipment"]
                if isinstance(eq_data, dict):
                    for k, v in eq_data.items():
                        PyImGui.text_colored(f"{k}:", (0.8, 0.8, 0.8, 1.0))
                        PyImGui.same_line(0.0, -1.0)
                        PyImGui.text_wrapped(str(v))
                else:
                    PyImGui.text_wrapped(str(eq_data))
                PyImGui.unindent(0.0)

            # --- 3. Required Weapons ---
            if "Weapons" in reqs and reqs["Weapons"]:
                PyImGui.dummy(0, 5)
                PyImGui.bullet()
                PyImGui.text("Weapon Sets:")
                PyImGui.indent(0.0)
                
                wep_data = reqs["Weapons"]
                if isinstance(wep_data, dict):
                    for slot, desc in wep_data.items():
                        PyImGui.text_colored(f"[{slot}]:", (0.7, 1.0, 0.7, 1.0))
                        PyImGui.same_line(0.0, -1.0)
                        PyImGui.text_wrapped(str(desc))
                elif isinstance(wep_data, list):
                    for item in wep_data:
                        PyImGui.bullet()
                        PyImGui.text_wrapped(str(item))
                else:
                    PyImGui.text_wrapped(str(wep_data))
                PyImGui.unindent(0.0)

            # --- 4. Required Heroes ---
            if "Required_Heroes" in reqs and reqs["Required_Heroes"]:
                PyImGui.dummy(0, 5)
                PyImGui.bullet()
                PyImGui.text("Required Heroes:")
                
                req_count = len(reqs["Required_Heroes"])
                PyImGui.indent(0.0)
                PyImGui.text_colored(f"These heroes will replace the first {req_count} slots of your party.", (0.6, 0.6, 1.0, 1.0))
                
                for idx, hero_req in enumerate(reqs["Required_Heroes"]):
                    PyImGui.separator()
                    
                    h_id_req = hero_req.get("HeroID", 0)
                    h_build = hero_req.get("Build", "")
                    h_eq = hero_req.get("Equipment", "")
                    h_wep = hero_req.get("Weapons", "")
                    
                    if h_id_req > 0:
                        try:
                            from Bots.ZeroToHero.Modules.Common.Enums import HeroID
                            h_name = HeroID.get_nice_name(h_id_req)
                        except:
                            h_name = f"Hero ID {h_id_req}"
                            
                        PyImGui.text_colored(f"Slot {idx+1}: {h_name}", HEADER_COLOR)
                        PyImGui.same_line(0.0, -1.0)
                        PyImGui.text_colored("(Mandatory)", WARN_COLOR)
                        
                    else:
                        role_name = hero_req.get("Role", f"Strategy Slot {idx+1}")
                        PyImGui.text_colored(f"Slot {idx+1}: {role_name}", HEADER_COLOR)
                        
                        current_assigned = self.team_manager.GetAssignedHero(name, idx, 0)
                        display_val = "-- Select Hero --"
                        for op_id, op_name in self.team_manager.hero_options:
                            if op_id == current_assigned:
                                display_val = op_name
                                break
                        
                        if PyImGui.begin_combo(f"##SelHero_{idx}", display_val, 0):
                            for op_id, op_name in self.team_manager.hero_options:
                                is_sel = (op_id == current_assigned)
                                if PyImGui.selectable(op_name, is_sel, 0, (0,0)):
                                    self.team_manager.SetAssignedHero(name, idx, op_id)
                                    current_assigned = op_id
                            PyImGui.end_combo()

                    PyImGui.indent(0.0)
                    if h_eq:
                         PyImGui.text_wrapped(f"Armor: {h_eq}")
                    if h_wep:
                         PyImGui.text_wrapped(f"Weapons: {h_wep}")
                    if h_build:
                         # Click to Copy Logic for Heroes
                         PyImGui.text_colored(f"Build: {h_build}", (0.7, 1.0, 0.7, 1.0))
                         if PyImGui.is_item_hovered():
                             PyImGui.set_tooltip("Click to Copy Build Code")
                         if PyImGui.is_item_clicked(0): # Fix: Pass 0 for Left Click
                             PyImGui.set_clipboard_text(h_build)
                             Py4GW.Console.Log(BOT_NAME, "Build code copied to clipboard.", Py4GW.Console.MessageType.Info)
                    
                    PyImGui.unindent(0.0)
                
                PyImGui.dummy(0, 5)
                if PyImGui.button("Test Team Loadout (Load All Heroes)", -1, 0):
                    self.team_manager.test_routine = self.team_manager.TestMandatoryHeroes(reqs["Required_Heroes"], name)
                
                PyImGui.unindent(0.0)
                
            # --- 5. General Notes ---
            if "Notes" in reqs and reqs["Notes"]:
                PyImGui.dummy(0, 5)
                PyImGui.text_colored("Notes:", HEADER_COLOR)
                PyImGui.text_wrapped(reqs["Notes"])
            
            PyImGui.dummy(0, 10)
            PyImGui.separator()
            
            if PyImGui.button("I Understand", -1, 30):
                self.team_manager.DisbandParty() 
                self.pending_notifications.pop(0)

        else:
            PyImGui.pop_style_color(3) 
            PyImGui.end()

    def DrawTaskInfoWindow(self):
        if PyImGui.begin("Task Details", 0):
            current_campaign = self.current_campaign
            current_task_name = self.selected_task_name
            
            try:
                if (current_campaign in self.task_manager.available_tasks and 
                    current_task_name in self.task_manager.available_tasks[current_campaign]):
                    
                    task_class = self.task_manager.available_tasks[current_campaign][current_task_name]
                    temp_inst = task_class()
                    info = temp_inst.GetInfo() 
                    
                    PyImGui.text_colored(f"{info.get('Name', 'Unknown')}", HEADER_COLOR)
                    PyImGui.text_colored(f"Type: {info.get('Type', 'Task')}", (0.6, 0.6, 0.6, 1.0))
                    PyImGui.separator()
                    
                    PyImGui.dummy(0, 5)
                    PyImGui.text_wrapped(info.get('Description', 'No description.'))
                    PyImGui.dummy(0, 5)
                    
                    builds = info.get('Recommended_Builds', [])
                    if builds and builds != ["Any"]:
                        PyImGui.text_colored("Recommended Builds:", HEADER_COLOR)
                        for build in builds:
                            PyImGui.bullet()
                            PyImGui.text(str(build))
                        PyImGui.dummy(0, 5)

                    hm_tips = info.get('HM_Tips', "")
                    if hm_tips:
                        PyImGui.separator()
                        PyImGui.text_colored("Hard Mode Strategy:", HM_COLOR)
                        PyImGui.text_wrapped(hm_tips)
                        PyImGui.dummy(0, 5)
                        
                    mandatory = info.get("Mandatory_Loadout", {})
                    if mandatory:
                        PyImGui.separator()
                        PyImGui.text_colored("Mandatory Requirements:", WARN_COLOR)
                        
                        if "NM" in mandatory and self._HasReqs(mandatory["NM"]):
                             if PyImGui.tree_node("Normal Mode Requirements"):
                                 self._DrawRequirementsSimple(mandatory["NM"])
                                 PyImGui.tree_pop()
                                 
                        if "HM" in mandatory and self._HasReqs(mandatory["HM"]):
                             if PyImGui.tree_node("Hard Mode Requirements"):
                                 self._DrawRequirementsSimple(mandatory["HM"])
                                 PyImGui.tree_pop()

                else:
                    PyImGui.text_colored("Error: Task not found in registry.", (1, 0, 0, 1))
                    
            except Exception as e:
                PyImGui.text_colored(f"Error fetching info: {str(e)}", (1, 0, 0, 1))

            PyImGui.separator()
            if PyImGui.button("Close", -1, 0):
                self.show_task_info_window = False
                
        PyImGui.end()

    def _HasReqs(self, reqs):
        return (reqs.get("Player_Build") or reqs.get("Required_Heroes") or 
                reqs.get("Notes") or reqs.get("Equipment") or reqs.get("Weapons"))

    def _DrawRequirementsSimple(self, reqs):
        if "Player_Build" in reqs and reqs["Player_Build"]:
             pb = reqs['Player_Build']
             if isinstance(pb, dict):
                 PyImGui.text("Player Builds:")
                 for prof, code in pb.items():
                     PyImGui.bullet()
                     PyImGui.text(f"{prof}: {code}")
             else:
                 PyImGui.text(f"Player: {pb}")

        if "Equipment" in reqs and reqs["Equipment"]:
            PyImGui.text("Equipment:")
            eq = reqs["Equipment"]
            if isinstance(eq, dict):
                for k,v in eq.items():
                    PyImGui.bullet()
                    PyImGui.text_wrapped(f"{k}: {v}")
            else:
                PyImGui.text_wrapped(str(eq))

        if "Weapons" in reqs and reqs["Weapons"]:
            PyImGui.text("Weapons:")
            wp = reqs["Weapons"]
            if isinstance(wp, dict):
                for k,v in wp.items():
                    PyImGui.bullet()
                    PyImGui.text_wrapped(f"{k}: {v}")
            else:
                PyImGui.text_wrapped(str(wp))

        if "Required_Heroes" in reqs and reqs["Required_Heroes"]:
             for h in reqs["Required_Heroes"]:
                 h_id = h.get('HeroID', 0)
                 if h_id > 0:
                    PyImGui.text(f"Hero {h_id}: {h.get('Build', 'Any')}")
                 else:
                    role = h.get("Role", "Strategy Hero")
                    PyImGui.text(f"{role}: {h.get('Build', 'Any')}")
        
        if "Notes" in reqs and reqs["Notes"]:
             PyImGui.text_wrapped(f"Notes: {reqs['Notes']}")

    def DrawQueueWindow(self):
        if PyImGui.begin("Queue Manager", 0):
            PyImGui.text_colored("Execution Queue", HEADER_COLOR)
            PyImGui.separator()
            
            queue_len = len(self.task_manager.task_queue)
            
            if queue_len == 0:
                PyImGui.text_disabled("Queue is empty.")
            else:
                for i in range(queue_len):
                    queued_task = self.task_manager.task_queue[i]
                    task_name = queued_task.name
                    task_type = queued_task.task_type
                    is_hm = queued_task.hard_mode
                    
                    PyImGui.push_id(str(i))
                    
                    if PyImGui.button(IconsFontAwesome5.ICON_ARROW_UP):
                        self.task_manager.move_task_up(i)
                    PyImGui.same_line(0.0, 5.0)
                    
                    if PyImGui.button(IconsFontAwesome5.ICON_ARROW_DOWN):
                        self.task_manager.move_task_down(i)
                    PyImGui.same_line(0.0, 5.0)
                    
                    if PyImGui.button(IconsFontAwesome5.ICON_TIMES):
                        self.task_manager.remove_task_at_index(i)
                        PyImGui.pop_id()
                        break
                    
                    PyImGui.same_line(0.0, 10.0)
                    
                    PyImGui.text(f"{i+1}.")
                    PyImGui.same_line(0.0, 5.0)
                    
                    if task_type == "Mission":
                        if is_hm:
                            PyImGui.text_colored("[HM]", HM_COLOR)
                        else:
                            PyImGui.text_colored("[NM]", NM_COLOR)
                        PyImGui.same_line(0.0, 5.0)
                    
                    PyImGui.text(task_name)
                    
                    PyImGui.pop_id()
            
            PyImGui.separator()
            if PyImGui.button("Close", -1, 0):
                self.show_queue_window = False
                
        PyImGui.end()

    def PushStyles(self):
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text,           BODY_TEXT_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.Separator,      SEPARATOR_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.Button,         BUTTON_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.ButtonHovered,  BUTTON_HOVER_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.ButtonActive,   BUTTON_ACTIVE_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.FrameBg,        FRAME_BG_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.FrameBgHovered, FRAME_HOVER_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.FrameBgActive,  FRAME_ACTIVE_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.Header,         BUTTON_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.HeaderHovered,  BUTTON_HOVER_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.HeaderActive,   BUTTON_ACTIVE_COLOR)

    def PopStyles(self):
        PyImGui.pop_style_color(11)

    def DrawHeader(self):
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, ICON_COLOR)
        PyImGui.text(IconsFontAwesome5.ICON_ROBOT)
        PyImGui.pop_style_color(1)
        
        PyImGui.same_line(0.0, 5.0)
        PyImGui.text_colored("Zero To Hero", (0, 1, 1, 1))
        
        credit = "v1.0 by Paul"
        avail_w = PyImGui.get_content_region_avail()[0]
        text_w = PyImGui.calc_text_size(credit)[0]
        current_x = PyImGui.get_cursor_pos_x()
        PyImGui.same_line(current_x + avail_w - text_w, -1.0)
        PyImGui.text_colored(credit, (0.5, 0.5, 0.5, 1.0))
        
        PyImGui.separator()
        PyImGui.dummy(0, 5)

    def DrawControls(self):
        btn_width = (PyImGui.get_content_region_avail()[0] - 10) / 2
        btn_height = 40
        
        if not self.is_running:
            label = f"Start Bot  {IconsFontAwesome5.ICON_PLAY}"
            if PyImGui.button(label, btn_width, btn_height):
                self.StartBot()
        else:
            label = f"Stop Bot  {IconsFontAwesome5.ICON_STOP}"
            if PyImGui.button(label, btn_width, btn_height):
                self.StopBot()
                
        PyImGui.same_line(0.0, -1.0)
        
        if not self.is_running:
            PyImGui.begin_disabled(True)
            PyImGui.button(f"Pause  {IconsFontAwesome5.ICON_PAUSE}", btn_width, btn_height)
            PyImGui.end_disabled()
        else:
            if self.is_paused:
                if PyImGui.button(f"Resume  {IconsFontAwesome5.ICON_PLAY_CIRCLE}", btn_width, btn_height):
                    self.TogglePause()
            else:
                if PyImGui.button(f"Pause  {IconsFontAwesome5.ICON_PAUSE}", btn_width, btn_height):
                    self.TogglePause()
                    
        PyImGui.dummy(0, 5)

    def DrawConfiguration(self):
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, HEADER_COLOR)
        PyImGui.text(f"{IconsFontAwesome5.ICON_COG} Configuration")
        PyImGui.pop_style_color(1)
        PyImGui.dummy(0, 2)
        
        # --- Campaign Selector ---
        PyImGui.text("Select Campaign:")
        if self.campaign_list:
            new_idx = PyImGui.combo("##Campaign", self.selected_campaign_idx, self.campaign_list)
            if new_idx != self.selected_campaign_idx:
                self.selected_campaign_idx = new_idx
                self.current_campaign = self.campaign_list[new_idx]
                
                # Update Tasks
                self.task_list = self.GetFilteredTasks()
                self.selected_task_idx = 0
                self.selected_task_name = self.task_list[0] if self.task_list else "None"
        else:
            PyImGui.text_colored("No Campaigns Found!", (1,0,0,1))

        PyImGui.dummy(0, 5)

        # --- Task Type Filter ---
        PyImGui.text("Show:")
        for i, option in enumerate(self.filter_options):
            new_val = PyImGui.radio_button(option, self.selected_filter_idx, i)
            if new_val != self.selected_filter_idx:
                self.selected_filter_idx = new_val
                self.task_list = self.GetFilteredTasks()
                self.selected_task_idx = 0
                self.selected_task_name = self.task_list[0] if self.task_list else "None"
            
            if i < len(self.filter_options) - 1:
                PyImGui.same_line(0.0, 10.0)

        PyImGui.dummy(0, 5)

        # --- Task Selector with Info Button ---
        PyImGui.text("Select Task:")
        if self.task_list:
            avail_w = PyImGui.get_content_region_avail()[0]
            btn_w = 120
            combo_w = avail_w - btn_w - 5 
            
            PyImGui.set_next_item_width(combo_w)
            t_idx = PyImGui.combo("##Tasks", self.selected_task_idx, self.task_list)
            if t_idx != self.selected_task_idx:
                self.selected_task_idx = t_idx
                self.selected_task_name = self.task_list[t_idx]
            
            PyImGui.same_line(0.0, 5.0)
            
            btn_label = "Task Info"
            try:
                if (self.current_campaign in self.task_manager.available_tasks and 
                    self.selected_task_name in self.task_manager.available_tasks[self.current_campaign]):
                    task_cls = self.task_manager.available_tasks[self.current_campaign][self.selected_task_name]
                    temp_inst = task_cls() 
                    if temp_inst.task_type == "Mission":
                        btn_label = "Mission Info"
                    elif temp_inst.task_type == "Quest":
                        btn_label = "Quest Info"
            except:
                pass
            
            if PyImGui.button(f"{btn_label} {IconsFontAwesome5.ICON_INFO_CIRCLE}", btn_w, 0):
                self.show_task_info_window = True
        else:
            PyImGui.text_disabled("No tasks found.")

        PyImGui.dummy(0, 5)
        
        # --- Team Setup Button ---
        if self.team_manager.is_new_config:
            PyImGui.push_style_color(PyImGui.ImGuiCol.Button, (0.8, 0.2, 0.2, 1.0)) 
            btn_label = f"Setup Team (Required) {IconsFontAwesome5.ICON_USERS}"
        else:
            btn_label = f"Setup Team {IconsFontAwesome5.ICON_USERS}"
            
        if PyImGui.button(btn_label, -1, 30):
            self.team_manager.show_window = True
            
        if self.team_manager.is_new_config:
            PyImGui.pop_style_color(1)
            
        PyImGui.dummy(0, 5)
        
        # --- Queue Controls ---
        self.use_hard_mode = PyImGui.checkbox("Hard Mode (Missions Only)", self.use_hard_mode)
        
        PyImGui.same_line(0.0, 20.0)
        try:
            if GLOBAL_CACHE.Party.IsHardMode():
                PyImGui.text_colored("[Game: HM]", HM_COLOR)
            else:
                PyImGui.text_colored("[Game: NM]", NM_COLOR)
        except:
            PyImGui.text_disabled("[Game: ?]")
            
        PyImGui.dummy(0, 2)

        # --- Add to Queue with Notification Logic ---
        if PyImGui.button(f"Add to Queue {IconsFontAwesome5.ICON_PLUS}", -1, 30):
            # 1. Add to Queue
            self.task_manager.add_task_to_queue(self.current_campaign, self.selected_task_name, self.use_hard_mode)
            mode_indicator = " [HM]" if self.use_hard_mode else ""
            self.current_task_name = f"Added: {self.selected_task_name}{mode_indicator}"
            
            # 2. Check for Mandatory Requirements
            try:
                task_class = self.task_manager.available_tasks[self.current_campaign][self.selected_task_name]
                temp_inst = task_class()
                info = temp_inst.GetInfo()
                
                mandatory = info.get("Mandatory_Loadout", {})
                req_mode_key = "HM" if self.use_hard_mode and temp_inst.task_type == "Mission" else "NM"
                
                # Check if requirements exist for the specific mode AND have content
                if req_mode_key in mandatory:
                    reqs = mandatory[req_mode_key]
                    
                    has_real_reqs = (
                        reqs.get("Player_Build") or 
                        reqs.get("Required_Heroes") or 
                        reqs.get("Notes") or 
                        reqs.get("Equipment") or 
                        reqs.get("Weapons")
                    )
                    
                    if has_real_reqs:
                        already_pending = False
                        for item in self.pending_notifications:
                            if item['name'] == self.selected_task_name and item['mode'] == req_mode_key:
                                already_pending = True
                                break
                        
                        if not already_pending:
                            self.pending_notifications.append({
                                'name': self.selected_task_name,
                                'mode': req_mode_key,
                                'requirements': reqs
                            })
            except Exception as e:
                Py4GW.Console.Log(BOT_NAME, f"Error checking requirements: {e}", Py4GW.Console.MessageType.Error)

        PyImGui.dummy(0, 5)
        
        col_w = (PyImGui.get_content_region_avail()[0] - 10) / 2
        
        if PyImGui.button(f"Clear Queue {IconsFontAwesome5.ICON_TRASH}", col_w, 30):
            self.task_manager.clear_queue()
            self.current_task_name = "Queue Cleared."
            
        PyImGui.same_line(0.0, -1.0)
        
        if PyImGui.button(f"Manage Queue {IconsFontAwesome5.ICON_LIST}", col_w, 30):
            self.show_queue_window = not self.show_queue_window

    def DrawStatus(self):
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, HEADER_COLOR)
        PyImGui.text(f"{IconsFontAwesome5.ICON_INFO_CIRCLE} Status Monitor")
        PyImGui.pop_style_color(1)
        PyImGui.dummy(0, 2)
        
        if PyImGui.begin_child("StatusPanel", (0.0, 0.0), True, 0):
            
            PyImGui.text("State:")
            PyImGui.same_line(0.0, 5.0)
            if self.is_paused:
                PyImGui.text_colored("PAUSED", (1, 1, 0, 1))
            elif self.is_running:
                PyImGui.text_colored("ACTIVE", (0, 1, 0, 1))
            else:
                PyImGui.text_colored("IDLE", (0.7, 0.7, 0.7, 1.0))
                
            PyImGui.dummy(0, 2)
            PyImGui.text_colored("Current Task:", HEADER_COLOR)
            PyImGui.text(self.current_task_name)
            
            if self.current_task_instance and self.current_task_instance.task_type == "Mission":
                PyImGui.same_line(0.0, 10.0)
                if self.current_task_instance.use_hard_mode:
                    PyImGui.text_colored("[HM]", HM_COLOR)
                else:
                    PyImGui.text_colored("[NM]", NM_COLOR)
            
            q_len = len(self.task_manager.task_queue)
            PyImGui.text_colored(f"Tasks in Queue: {q_len}", (0.5, 0.5, 0.5, 1.0))
            
        PyImGui.end_child()

    def StartBot(self):
        if not self.team_manager.HasValidConfig():
            Py4GW.Console.Log(BOT_NAME, "Cannot start: Team Setup is required! Please configure your team.", Py4GW.Console.MessageType.Error)
            return

        if not self.task_manager.task_queue and not self.current_task_instance:
            Py4GW.Console.Log(BOT_NAME, "Cannot start: Queue is empty. Please add a task.", Py4GW.Console.MessageType.Error)
            return

        self.is_running = True
        self.is_paused = False
        self.Start() 
        Py4GW.Console.Log(BOT_NAME, "Bot Started.", Py4GW.Console.MessageType.Info)

    def StopBot(self):
        self.is_running = False
        self.is_paused = False
        self.Stop()
        self.movement.Stop()
        self.config.FSM.RemoveManagedCoroutine("MainTask")
        self.current_task_instance = None
        self.current_task_name = "Stopped."
        Py4GW.Console.Log(BOT_NAME, "Bot Stopped.", Py4GW.Console.MessageType.Warning)
        
    def TogglePause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            Py4GW.Console.Log(BOT_NAME, "Bot Paused.", Py4GW.Console.MessageType.Warning)
        else:
            Py4GW.Console.Log(BOT_NAME, "Bot Resumed.", Py4GW.Console.MessageType.Info)

    def Update(self):
        if not self.team_manager_initialized:
            try:
                self.team_manager.Initialize()
                if self.team_manager.character_name:
                    self.team_manager_initialized = True
            except:
                pass 
                
        self.team_manager.Update()

        super().Update()
        self.DrawUI()
        self.UpdateTaskExecution()

try:
    if 'hero_bot' not in globals():
        hero_bot = ZeroToHeroBot()
except NameError:
    hero_bot = ZeroToHeroBot()

def main():
    try:
        hero_bot.Update()
        ActionQueueManager().ProcessQueue("ACTION")
    except Exception as e:
        Py4GW.Console.Log("ZeroToHero", f"Crash: {str(e)}", Py4GW.Console.MessageType.Error)

if __name__ == "__main__":
    main()