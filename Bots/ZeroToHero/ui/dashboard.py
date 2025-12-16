"""
Main dashboard UI for the Zero To Hero bot.
Handles the primary control interface.
"""
import PyImGui
from Py4GWCoreLib.ImGui_src.WindowModule import WindowModule
from Py4GWCoreLib.ImGui_src.IconsFontAwesome5 import IconsFontAwesome5
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from core.constants import (
    BOT_NAME, WINDOW_SIZE, BOT_VERSION, BOT_AUTHOR, Colors, 
    TASK_FILTER_OPTIONS, get_campaign_display_name
)
from data.enums import TaskType, GameMode
from ui.themes import Theme


class DashboardUI:
    """Main dashboard window for bot control and configuration."""
    
    def __init__(self, bot):
        """
        Args:
            bot: Reference to ZeroToHeroBot instance
        """
        self.bot = bot
        self.window_module = WindowModule(
            BOT_NAME, 
            window_name="Zero To Hero Dashboard", 
            window_size=WINDOW_SIZE
        )
    
    def draw(self):
        """Main draw function - call every frame."""
        if self.window_module.first_run:
            PyImGui.set_next_window_size(WINDOW_SIZE[0], WINDOW_SIZE[1])
            self.window_module.first_run = False

        Theme.push_styles()

        if self.window_module.begin():
            self._draw_header()
            self._draw_controls()
            PyImGui.separator()
            self._draw_configuration()
            PyImGui.separator()
            self._draw_status()

        self.window_module.end()
        Theme.pop_styles()
    
    def _draw_header(self):
        """Draws the header with title and version."""
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, Colors.ICON)
        PyImGui.text(IconsFontAwesome5.ICON_ROBOT)
        PyImGui.pop_style_color(1)
        
        PyImGui.same_line(0.0, 5.0)
        PyImGui.text_colored("Zero To Hero", Colors.INFO_COLOR)
        
        credit = f"v{BOT_VERSION} by {BOT_AUTHOR}"
        avail_w = PyImGui.get_content_region_avail()[0]
        text_w = PyImGui.calc_text_size(credit)[0]
        current_x = PyImGui.get_cursor_pos_x()
        PyImGui.same_line(current_x + avail_w - text_w, -1.0)
        PyImGui.text_colored(credit, (0.5, 0.5, 0.5, 1.0))
        
        PyImGui.separator()
        PyImGui.dummy(0, 5)
    
    def _draw_controls(self):
        """Draws Start/Stop/Pause buttons."""
        btn_width = (PyImGui.get_content_region_avail()[0] - 10) / 2
        btn_height = 40
        
        # Start/Stop Button
        if not self.bot.is_running:
            label = f"Start Bot  {IconsFontAwesome5.ICON_PLAY}"
            if PyImGui.button(label, btn_width, btn_height):
                self.bot.start_bot()
        else:
            label = f"Stop Bot  {IconsFontAwesome5.ICON_STOP}"
            if PyImGui.button(label, btn_width, btn_height):
                self.bot.stop_bot()
        
        PyImGui.same_line(0.0, -1.0)
        
        # Pause/Resume Button
        if not self.bot.is_running:
            PyImGui.begin_disabled(True)
            PyImGui.button(f"Pause  {IconsFontAwesome5.ICON_PAUSE}", btn_width, btn_height)
            PyImGui.end_disabled()
        else:
            if self.bot.is_paused:
                if PyImGui.button(f"Resume  {IconsFontAwesome5.ICON_PLAY_CIRCLE}", btn_width, btn_height):
                    self.bot.toggle_pause()
            else:
                if PyImGui.button(f"Pause  {IconsFontAwesome5.ICON_PAUSE}", btn_width, btn_height):
                    self.bot.toggle_pause()
        
        PyImGui.dummy(0, 5)
    
    def _draw_configuration(self):
        """Draws the configuration section."""
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, Colors.HEADER)
        PyImGui.text(f"{IconsFontAwesome5.ICON_COG} Configuration")
        PyImGui.pop_style_color(1)
        PyImGui.dummy(0, 2)
        
        # Campaign Selector
        self._draw_campaign_selector()
        PyImGui.dummy(0, 5)
        
        # Task Type Filter
        self._draw_task_filter()
        PyImGui.dummy(0, 5)
        
        # Task Selector
        self._draw_task_selector()
        PyImGui.dummy(0, 5)
        
        # Team Setup Button
        self._draw_team_setup_button()
        PyImGui.dummy(0, 5)
        
        # Queue Controls
        self._draw_queue_controls()
    
    def _draw_campaign_selector(self):
        """Campaign dropdown with display names."""
        PyImGui.text("Select Campaign:")
        if self.bot.campaign_list:
            # Build display names list
            display_names = [get_campaign_display_name(c) for c in self.bot.campaign_list]
            
            new_idx = PyImGui.combo("##Campaign", self.bot.selected_campaign_idx, display_names)
            if new_idx != self.bot.selected_campaign_idx:
                self.bot.selected_campaign_idx = new_idx
                self.bot.current_campaign = self.bot.campaign_list[new_idx]
                self.bot.refresh_task_list()
        else:
            PyImGui.text_colored("No Campaigns Found!", Colors.ERROR_COLOR)
    
    def _draw_task_filter(self):
        """Task type filter radio buttons."""
        PyImGui.text("Show:")
        for i, option in enumerate(TASK_FILTER_OPTIONS):
            new_val = PyImGui.radio_button(option, self.bot.selected_filter_idx, i)
            if new_val != self.bot.selected_filter_idx:
                self.bot.selected_filter_idx = new_val
                self.bot.refresh_task_list()
            
            if i < len(TASK_FILTER_OPTIONS) - 1:
                PyImGui.same_line(0.0, 10.0)
    
    def _draw_task_selector(self):
        """Task dropdown with info button."""
        PyImGui.text("Select Task:")
        if self.bot.task_list:
            avail_w = PyImGui.get_content_region_avail()[0]
            btn_w = 120
            combo_w = avail_w - btn_w - 5
            
            # Task combo
            PyImGui.set_next_item_width(combo_w)
            t_idx = PyImGui.combo("##Tasks", self.bot.selected_task_idx, self.bot.task_list)
            if t_idx != self.bot.selected_task_idx:
                self.bot.selected_task_idx = t_idx
                self.bot.selected_task_name = self.bot.task_list[t_idx]
            
            PyImGui.same_line(0.0, 5.0)
            
            # Info button
            btn_label = self._get_info_button_label()
            if PyImGui.button(f"{btn_label} {IconsFontAwesome5.ICON_INFO_CIRCLE}", btn_w, 0):
                self.bot.show_task_info_window = True
        else:
            PyImGui.text_disabled("No tasks found.")
    
    def _get_info_button_label(self):
        """Get appropriate label for info button based on task type."""
        try:
            info = self.bot.task_registry.get_task_info(
                self.bot.current_campaign,
                self.bot.selected_task_name
            )
            if info:
                if info.task_type == TaskType.MISSION:
                    return "Mission Info"
                elif info.task_type == TaskType.QUEST:
                    return "Quest Info"
        except:
            pass
        return "Task Info"
    
    def _draw_team_setup_button(self):
        """Team setup button with warning if not configured."""
        if self.bot.team_manager.is_new_config:
            PyImGui.push_style_color(PyImGui.ImGuiCol.Button, (0.8, 0.2, 0.2, 1.0))
            btn_label = f"Setup Team (Required) {IconsFontAwesome5.ICON_USERS}"
        else:
            btn_label = f"Setup Team {IconsFontAwesome5.ICON_USERS}"
        
        if PyImGui.button(btn_label, -1, 30):
            self.bot.team_manager.show_window = True
        
        if self.bot.team_manager.is_new_config:
            PyImGui.pop_style_color(1)
    
    def _draw_queue_controls(self):
        """Hard mode checkbox, add to queue, and queue management buttons."""
        # Hard Mode checkbox + current game mode indicator
        self.bot.use_hard_mode = PyImGui.checkbox("Hard Mode (Missions Only)", self.bot.use_hard_mode)
        
        PyImGui.same_line(0.0, 20.0)
        try:
            if GLOBAL_CACHE.Party.IsHardMode():
                PyImGui.text_colored("[Game: HM]", Colors.HM_COLOR)
            else:
                PyImGui.text_colored("[Game: NM]", Colors.NM_COLOR)
        except:
            PyImGui.text_disabled("[Game: ?]")
        
        PyImGui.dummy(0, 2)
        
        # Add to Queue button
        if PyImGui.button(f"Add to Queue {IconsFontAwesome5.ICON_PLUS}", -1, 30):
            self.bot.add_task_to_queue()
        
        PyImGui.dummy(0, 5)
        
        # Clear / Manage Queue buttons
        col_w = (PyImGui.get_content_region_avail()[0] - 10) / 2
        
        if PyImGui.button(f"Clear Queue {IconsFontAwesome5.ICON_TRASH}", col_w, 30):
            self.bot.clear_queue()
        
        PyImGui.same_line(0.0, -1.0)
        
        if PyImGui.button(f"Manage Queue {IconsFontAwesome5.ICON_LIST}", col_w, 30):
            self.bot.show_queue_window = not self.bot.show_queue_window
    
    def _draw_status(self):
        """Draws the status monitor panel."""
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, Colors.HEADER)
        PyImGui.text(f"{IconsFontAwesome5.ICON_INFO_CIRCLE} Status Monitor")
        PyImGui.pop_style_color(1)
        PyImGui.dummy(0, 2)
        
        if PyImGui.begin_child("StatusPanel", (0.0, 0.0), True, 0):
            # State indicator
            PyImGui.text("State:")
            PyImGui.same_line(0.0, 5.0)
            if self.bot.is_paused:
                PyImGui.text_colored("PAUSED", (1, 1, 0, 1))
            elif self.bot.is_running:
                PyImGui.text_colored("ACTIVE", Colors.SUCCESS_COLOR)
            else:
                PyImGui.text_colored("IDLE", (0.7, 0.7, 0.7, 1.0))
            
            # Current task
            PyImGui.dummy(0, 2)
            PyImGui.text_colored("Current Task:", Colors.HEADER)
            PyImGui.text(self.bot.current_task_name)
            
            # Mode indicator for current task
            if self.bot.current_task_instance:
                task_type = self.bot.current_task_instance.task_type
                if task_type == TaskType.MISSION:
                    PyImGui.same_line(0.0, 10.0)
                    if self.bot.current_task_instance.use_hard_mode:
                        PyImGui.text_colored("[HM]", Colors.HM_COLOR)
                    else:
                        PyImGui.text_colored("[NM]", Colors.NM_COLOR)
            
            # Queue length
            q_len = self.bot.task_registry.get_queue_length()
            PyImGui.text_colored(f"Tasks in Queue: {q_len}", (0.5, 0.5, 0.5, 1.0))
        
        PyImGui.end_child()