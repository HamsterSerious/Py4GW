import PyImGui
from Py4GWCoreLib.ImGui_src.IconsFontAwesome5 import IconsFontAwesome5

from core.constants import Colors, PROGRESS_WINDOW_SIZE
from ui.base_window import BaseWindow

class ProgressWindow(BaseWindow):
    TITLE = "Mission Progress"
    SIZE = PROGRESS_WINDOW_SIZE
    
    # 0 allows manual resizing
    FLAGS = 0
    
    @property
    def is_visible(self) -> bool:
        # Only show if the bot is "Active" (Start pressed) AND FSM is running
        return self.bot.is_bot_active and self.bot.is_running

    def draw_content(self):
        # FIX: Access current_task_instance directly from the bot
        task = self.bot.current_task_instance
        if not task:
            return

        # 1. Global Status Header
        PyImGui.text_colored(f"Task: {task.name}", Colors.HEADER)
        PyImGui.separator()
        PyImGui.text_wrapped(f"Status: {task.status_message}")
        PyImGui.dummy(0, 10)

        # 2. Objectives List
        if not task.objectives:
            PyImGui.text_disabled("No specific objectives tracked.")
        else:
            for obj in task.objectives:
                self._draw_objective(obj)

    def _draw_objective(self, obj):
        # Color & Icon Logic
        if obj.is_completed:
            color = Colors.SUCCESS     # Green
            icon = IconsFontAwesome5.ICON_CHECK
        elif obj.is_active:
            color = Colors.WARNING     # Yellow/Orange
            icon = IconsFontAwesome5.ICON_ARROW_RIGHT
        else:
            color = Colors.MUTED       # Gray
            icon = IconsFontAwesome5.ICON_CIRCLE

        # Left Side: Icon + Name
        PyImGui.text_colored(icon, color)
        PyImGui.same_line(0, 5)
        PyImGui.text_colored(obj.name, color)

        # Right Side: Text Status (No Bar)
        # Only show text if it's completed OR if total > 1
        # This hides the "0/1" for simple tasks like "Kill the corsairs"
        show_text = obj.is_completed or (obj.total_count > 1)
        
        if show_text:
            avail_w = PyImGui.get_content_region_avail()[0]
            status_txt = obj.status_text # "Done" or "x/y"
            
            text_w = PyImGui.calc_text_size(status_txt)[0]
            PyImGui.same_line(avail_w - text_w, 0)
            PyImGui.text_colored(status_txt, color)