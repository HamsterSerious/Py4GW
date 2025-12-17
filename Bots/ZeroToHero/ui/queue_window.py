"""
Queue management window for reordering and removing tasks.
"""
import PyImGui
from Py4GWCoreLib.ImGui_src.IconsFontAwesome5 import IconsFontAwesome5

from core.constants import Colors, QUEUE_WINDOW_SIZE
from data.enums import TaskType
from ui.base_window import ClosableWindow


class QueueWindow(ClosableWindow):
    """Task queue management interface."""
    
    TITLE = "Queue Manager"
    SIZE = QUEUE_WINDOW_SIZE
    
    @property
    def is_visible(self) -> bool:
        return self.bot.show_queue_window
    
    def set_visible(self, visible: bool):
        self.bot.show_queue_window = visible
    
    def draw_body(self):
        """Draw the queue contents."""
        PyImGui.text_colored("Execution Queue", Colors.HEADER)
        PyImGui.separator()
        
        queue_len = self.bot.task_registry.get_queue_length()
        
        if queue_len == 0:
            PyImGui.text_disabled("Queue is empty.")
        else:
            self._draw_queue_items(queue_len)
    
    def _draw_queue_items(self, queue_len: int):
        """Draw all items in the queue with controls."""
        for i in range(queue_len):
            queued_task = self.bot.task_registry.task_queue[i]
            
            PyImGui.push_id(str(i))
            
            # Control buttons
            if self._draw_item_controls(i):
                PyImGui.pop_id()
                break  # Item was removed, list changed
            
            # Task info
            self._draw_item_info(i, queued_task)
            
            PyImGui.pop_id()
    
    def _draw_item_controls(self, index: int) -> bool:
        """
        Draw up/down/remove buttons for a queue item.
        
        Returns:
            True if item was removed (caller should break loop)
        """
        # Up button
        if PyImGui.button(IconsFontAwesome5.ICON_ARROW_UP):
            self.bot.task_registry.move_task_up(index)
        PyImGui.same_line(0.0, 5.0)
        
        # Down button
        if PyImGui.button(IconsFontAwesome5.ICON_ARROW_DOWN):
            self.bot.task_registry.move_task_down(index)
        PyImGui.same_line(0.0, 5.0)
        
        # Remove button
        if PyImGui.button(IconsFontAwesome5.ICON_TIMES):
            self.bot.task_registry.remove_task_at_index(index)
            return True
        
        PyImGui.same_line(0.0, 10.0)
        return False
    
    def _draw_item_info(self, index: int, queued_task):
        """Draw task number, mode, and name."""
        # Task number
        PyImGui.text(f"{index + 1}.")
        PyImGui.same_line(0.0, 5.0)
        
        # Mode indicator for missions
        if queued_task.task_type == TaskType.MISSION:
            if queued_task.hard_mode:
                PyImGui.text_colored("[HM]", Colors.HARD_MODE)
            else:
                PyImGui.text_colored("[NM]", Colors.NORMAL_MODE)
            PyImGui.same_line(0.0, 5.0)
        
        # Task name
        PyImGui.text(queued_task.name)
