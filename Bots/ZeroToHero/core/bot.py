"""
Zero To Hero Bot - Core controller.
Coordinates between systems, UI, and task execution.
"""
import Py4GW
from Py4GWCoreLib.Botting import BottingClass
from Py4GWCoreLib import ActionQueueManager

from core.constants import BOT_NAME, CAMPAIGN_ORDER, TASK_FILTER_OPTIONS
from core.task_registry import TaskRegistry
from core.task_executor import TaskExecutor, NotificationManager, SelectionState
from data.enums import TaskType, GameMode
from systems.team.manager import TeamManager
from systems.movement import Movement
from systems.combat import Combat
from systems.transition import Transition
from systems.interaction import Interaction
from ui.dashboard import DashboardUI
from ui.notification_window import NotificationWindow
from ui.queue_window import QueueWindow
from ui.task_info_window import TaskInfoWindow
from ui.progress_window import ProgressWindow


class ZeroToHeroBot(BottingClass):
    """
    Main bot controller - coordinates systems and UI.
    
    Task execution delegated to TaskExecutor.
    Notification handling delegated to NotificationManager.
    Selection state delegated to SelectionState.
    """
    
    def __init__(self):
        super().__init__(bot_name=BOT_NAME)
        
        # Core Systems
        self.task_registry = TaskRegistry()
        self.movement = Movement()
        self.combat = Combat()
        self.transition = Transition(self)
        self.interaction = Interaction(self)
        
        # Team Management
        self.team_manager = TeamManager(self)
        self._team_manager_initialized = False
        
        # Delegated State Management
        self.executor = TaskExecutor(self)
        self.notifications = NotificationManager(self)
        self.selection = SelectionState(self)
        self.selection.initialize(CAMPAIGN_ORDER, TASK_FILTER_OPTIONS)
        
        # UI Components
        self.dashboard = DashboardUI(self)
        self.notification_window = NotificationWindow(self)
        self.queue_window = QueueWindow(self)
        self.task_info_window = TaskInfoWindow(self)
        self.progress_window = ProgressWindow(self)
        
        # Bot State
        self.is_running = False
        self.is_paused = False
        
        # UI Visibility State
        self.show_queue_window = False
        self.show_task_info_window = False
        
        # FSM Setup
        self.config.FSM.AddState(
            name="Bot_Idle_Loop",
            execute_fn=lambda: None,
            exit_condition=lambda: False,
            run_once=False
        )
        
        Py4GW.Console.Log(BOT_NAME, "Bot initialized.", Py4GW.Console.MessageType.Info)
    
    # ==================
    # PROPERTIES (for backward compatibility with UI)
    # ==================
    
    @property
    def pending_notifications(self):
        """Access notifications list (for UI compatibility)."""
        return self.notifications.pending
    
    @property
    def current_task_name(self) -> str:
        """Current task name for status display."""
        if self.executor.current_task:
            return self.executor.current_task.name
        return "Ready."
    
    @property
    def current_task_instance(self):
        """Current task instance (for UI compatibility)."""
        return self.executor.current_task
    
    @property
    def use_hard_mode(self) -> bool:
        """Hard mode selection state."""
        return self.selection.hard_mode
    
    @use_hard_mode.setter
    def use_hard_mode(self, value: bool):
        self.selection.hard_mode = value
    
    @property
    def campaign_list(self) -> list:
        """List of available campaigns."""
        return self.selection.campaign_list
    
    @property
    def current_campaign(self) -> str:
        """Currently selected campaign."""
        return self.selection.current_campaign
    
    @property
    def task_list(self) -> list:
        """List of tasks for current campaign/filter."""
        return self.selection.task_list
    
    @property
    def selected_task_name(self) -> str:
        """Currently selected task name."""
        return self.selection.current_task_name
    
    @property
    def selected_campaign_idx(self) -> int:
        return self.selection.campaign_idx
    
    @selected_campaign_idx.setter
    def selected_campaign_idx(self, value: int):
        self.selection.set_campaign(value)
    
    @property
    def selected_filter_idx(self) -> int:
        return self.selection.filter_idx
    
    @selected_filter_idx.setter
    def selected_filter_idx(self, value: int):
        self.selection.set_filter(value, TASK_FILTER_OPTIONS)
    
    @property
    def selected_task_idx(self) -> int:
        return self.selection.task_idx
    
    @selected_task_idx.setter
    def selected_task_idx(self, value: int):
        self.selection.set_task(value)
    
    @property
    def filter_options(self) -> list:
        return TASK_FILTER_OPTIONS
    
    # ==================
    # PUBLIC API
    # ==================
    
    def start_bot(self):
        """Start bot execution."""
        if not self.team_manager.has_valid_config():
            Py4GW.Console.Log(
                BOT_NAME, 
                "Cannot start: Team Setup is required! Please configure your team.", 
                Py4GW.Console.MessageType.Error
            )
            return
        
        if not self.task_registry.task_queue and not self.executor.is_active:
            Py4GW.Console.Log(
                BOT_NAME, 
                "Cannot start: Queue is empty. Please add a task.", 
                Py4GW.Console.MessageType.Error
            )
            return
        
        self.is_running = True
        self.is_paused = False
        self.Start()
        Py4GW.Console.Log(BOT_NAME, "Bot started.", Py4GW.Console.MessageType.Info)
    
    def stop_bot(self):
        """Stop bot execution."""
        self.is_running = False
        self.is_paused = False
        self.Stop()
        self.movement.stop()
        self.executor.stop()
        Py4GW.Console.Log(BOT_NAME, "Bot stopped.", Py4GW.Console.MessageType.Warning)
    
    def toggle_pause(self):
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        if self.is_paused:
            Py4GW.Console.Log(BOT_NAME, "Bot paused.", Py4GW.Console.MessageType.Warning)
        else:
            Py4GW.Console.Log(BOT_NAME, "Bot resumed.", Py4GW.Console.MessageType.Info)
    
    def add_task_to_queue(self):
        """Add currently selected task to queue."""
        self.task_registry.add_task_to_queue(
            self.current_campaign, 
            self.selected_task_name, 
            self.use_hard_mode
        )
        
        # Check for mandatory requirements
        self.notifications.check_and_queue(
            self.current_campaign,
            self.selected_task_name,
            self.use_hard_mode
        )
    
    def clear_queue(self):
        """Clear the task queue."""
        self.task_registry.clear_queue()
    
    def refresh_task_list(self):
        """Refresh the task list based on current filters."""
        self.selection.refresh_task_list()
    
    def get_filtered_tasks(self) -> list:
        """Get tasks for current campaign filtered by type."""
        return self.selection.task_list
    
    # ==================
    # MAIN UPDATE LOOP
    # ==================
    
    def update(self):
        """Main update loop - called every frame."""
        # Initialize team manager (once character is loaded)
        if not self._team_manager_initialized:
            try:
                self.team_manager.initialize()
                if self.team_manager.config.character_name:
                    self._team_manager_initialized = True
            except:
                pass
        
        # Update managers
        self.team_manager.update()
        
        # Update base class
        super().Update()
        
        # Draw UI
        self._draw_ui()
        
        # Update task execution
        if not self.executor.update():
            # Queue finished
            self.stop_bot()
    
    def _draw_ui(self):
        """Draw all UI windows."""
        self.dashboard.draw()
        self.queue_window.draw()
        self.task_info_window.draw()
        self.team_manager.draw_window()
        self.notification_window.draw()
        self.progress_window.draw()
    
    # ==================
    # LEGACY COMPATIBILITY
    # ==================
    
    def Update(self):
        """Legacy method name - calls update()."""
        self.update()
    
    def Routine(self):
        """Override base Routine - not used."""
        pass


# Global instance
_bot_instance = None


def get_bot() -> ZeroToHeroBot:
    """Get or create the global bot instance."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = ZeroToHeroBot()
    return _bot_instance