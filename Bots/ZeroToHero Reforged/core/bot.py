"""
Zero To Hero Bot - Core controller.
Thin wrapper around BottingClass with task queue management.

Uses BottingClass's built-in systems:
- bot.Move.* for movement
- bot.Interact.* for interactions  
- bot.Wait.* for waiting/conditions
- bot.Map.* for travel
- bot.Dialogs.* for NPC dialogs
- bot.Party.* for party management
- bot.Items.* for loot
- bot.SkillBar.* for skill templates
- bot.States.* for custom logic
- bot.Templates.* for combat modes (Pacifist/Aggressive)
- bot.Properties.* for upkeep features
"""
import Py4GW
from Py4GWCoreLib.Botting import BottingClass

from core.constants import BOT_NAME, CAMPAIGN_ORDER, TASK_FILTER_OPTIONS
from core.task_registry import TaskRegistry
from core.task_executor import TaskExecutor, NotificationManager, SelectionState
from data.enums import TaskType, GameMode
from team.manager import TeamManager
from ui.dashboard import DashboardUI
from ui.notification_window import NotificationWindow
from ui.queue_window import QueueWindow
from ui.task_info_window import TaskInfoWindow
from ui.progress_window import ProgressWindow


class ZeroToHeroBot(BottingClass):
    """
    Main bot controller - thin wrapper around BottingClass.
    
    Task execution is handled by the FSM. Tasks use build_routine()
    to declaratively add states to the FSM.
    """
    
    def __init__(self):
        super().__init__(
            bot_name=BOT_NAME,
            # Enable built-in upkeep features
            upkeep_auto_combat_active=True,
            upkeep_auto_loot_active=True,
        )
        
        # Task Management
        self.task_registry = TaskRegistry()
        
        # Team Management (custom UI layer on top of bot.Party)
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
        
        Py4GW.Console.Log(BOT_NAME, "Bot initialized.", Py4GW.Console.MessageType.Info)
    
    # ==================
    # PROPERTIES
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
        
        # Build the FSM routine from queued tasks
        self._build_routine_from_queue()
        
        self.is_running = True
        self.is_paused = False
        self.Start()  # Start the BottingClass FSM
        Py4GW.Console.Log(BOT_NAME, "Bot started.", Py4GW.Console.MessageType.Info)
    
    def _build_routine_from_queue(self):
        """Build FSM routine from all queued tasks."""
        for queued_task in self.task_registry.task_queue:
            task_instance = queued_task.create_instance()
            self.executor.current_task = task_instance
            
            # Add header for this task
            mode_str = f" [{task_instance.mode_string}]" if task_instance.task_type == TaskType.MISSION else ""
            self.States.AddHeader(f"=== {task_instance.name}{mode_str} ===")
            
            # Each task's build_routine adds states to the FSM
            task_instance.build_routine(self)
        
        # Clear queue after building (tasks are now in FSM)
        self.task_registry.task_queue.clear()
    
    def stop_bot(self):
        """Stop bot execution."""
        self.is_running = False
        self.is_paused = False
        self.Stop()
        self.executor.stop()
        Py4GW.Console.Log(BOT_NAME, "Bot stopped.", Py4GW.Console.MessageType.Warning)
    
    def toggle_pause(self):
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.config.FSM.pause()
            Py4GW.Console.Log(BOT_NAME, "Bot paused.", Py4GW.Console.MessageType.Warning)
        else:
            self.config.FSM.resume()
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
        
        # Update team manager
        self.team_manager.update()
        
        # Let BottingClass handle FSM execution
        super().Update()
        
        # Check if FSM finished
        if self.is_running and not self.config.fsm_running:
            self.is_running = False
            Py4GW.Console.Log(BOT_NAME, "All tasks completed.", Py4GW.Console.MessageType.Success)
        
        # Draw UI
        self._draw_ui()
    
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