"""
Queue management window for reordering and removing tasks.
"""
import PyImGui
from Py4GWCoreLib.ImGui_src.IconsFontAwesome5 import IconsFontAwesome5

from core.constants import Colors


class QueueWindow:
    """Task queue management interface."""
    
    def __init__(self, bot):
        """
        Args:
            bot: Reference to ZeroToHeroBot instance
        """
        self.bot = bot
    
    def draw(self):
        """Draw the queue window."""
        if not self.bot.show_queue_window:
            return
        
        if PyImGui.begin("Queue Manager", 0):
            PyImGui.text_colored("Execution Queue", Colors.HEADER)
            PyImGui.separator()
            
            queue_len = len(self.bot.task_registry.task_queue)
            
            if queue_len == 0:
                PyImGui.text_disabled("Queue is empty.")
            else:
                self._draw_queue_items(queue_len)
            
            PyImGui.separator()
            if PyImGui.button("Close", -1, 0):
                self.bot.show_queue_window = False
        
        PyImGui.end()
    
    def _draw_queue_items(self, queue_len):
        """Draw all items in the queue with controls."""
        for i in range(queue_len):
            queued_task = self.bot.task_registry.task_queue[i]
            task_name = queued_task.name
            task_type = queued_task.task_type
            is_hm = queued_task.hard_mode
            
            PyImGui.push_id(str(i))
            
            # Up button
            if PyImGui.button(IconsFontAwesome5.ICON_ARROW_UP):
                self.bot.task_registry.move_task_up(i)
            PyImGui.same_line(0.0, 5.0)
            
            # Down button
            if PyImGui.button(IconsFontAwesome5.ICON_ARROW_DOWN):
                self.bot.task_registry.move_task_down(i)
            PyImGui.same_line(0.0, 5.0)
            
            # Remove button
            if PyImGui.button(IconsFontAwesome5.ICON_TIMES):
                self.bot.task_registry.remove_task_at_index(i)
                PyImGui.pop_id()
                break
            
            PyImGui.same_line(0.0, 10.0)
            
            # Task number
            PyImGui.text(f"{i+1}.")
            PyImGui.same_line(0.0, 5.0)
            
            # Mode indicator for missions
            if task_type == "Mission":
                if is_hm:
                    PyImGui.text_colored("[HM]", Colors.HM_COLOR)
                else:
                    PyImGui.text_colored("[NM]", Colors.NM_COLOR)
                PyImGui.same_line(0.0, 5.0)
            
            # Task name
            PyImGui.text(task_name)
            
            PyImGui.pop_id()