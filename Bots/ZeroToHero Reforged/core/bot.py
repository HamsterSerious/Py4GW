"""
Zero To Hero Bot - Core Controller
"""
import Py4GW
from Py4GWCoreLib.Botting import BottingClass

from core.constants import BOT_NAME, CAMPAIGN_ORDER, TASK_FILTER_OPTIONS
from core.task_registry import TaskRegistry
from core.team.manager import TeamManager  

# UI Components
from ui.dashboard import DashboardUI
from ui.notification_window import NotificationWindow
from ui.queue_window import QueueWindow
from ui.task_info_window import TaskInfoWindow
from ui.progress_window import ProgressWindow

class ZeroToHeroBot(BottingClass):
    """
    Main bot controller.
    Inherits from BottingClass to get all framework features (Movement, Combat, FSM).
    """
    
    def __init__(self):
        # 1. Initialize Base Framework with Safety & Pcons
        super().__init__(
            bot_name=BOT_NAME,
            config_halt_on_death=True,      # Stop execution if we die
            config_pause_on_danger=True,    # Pause automation if overwhelmed
            
            # Default Pcons (You can toggle these in code later if needed)
            upkeep_grail_of_might_active=False,
            upkeep_essence_of_celerity_active=False,
            upkeep_armor_of_salvation_active=False,
        )
        
        # 2. Core Data Managers
        self.task_registry = TaskRegistry()
        self.team_manager = TeamManager(self)
        self._team_manager_initialized = False
        
        # 3. Execution State
        self.is_bot_active = False  # True when the "Start" button is pressed
        
        # 4. UI Components
        self.dashboard = DashboardUI(self)
        self.notification_window = NotificationWindow(self)
        self.queue_window = QueueWindow(self)
        self.task_info_window = TaskInfoWindow(self)
        self.progress_window = ProgressWindow(self)
        self.selection = _SelectionState(self) # Helper class for UI dropdowns
        
        # UI Visibility
        self.show_queue_window = False
        self.show_task_info_window = False
        
        # 5. Idle State
        # Keeps the FSM valid when no specific task is running
        self.config.FSM.AddState(
            name="Bot_Idle_Loop",
            execute_fn=lambda: None,
            exit_condition=lambda: False,
            run_once=False
        )
        
        Py4GW.Console.Log(BOT_NAME, "Bot initialized.", Py4GW.Console.MessageType.Info)

    # ==================
    # MAIN LOOP (Called by Game)
    # ==================
    
    def Update(self):
        """Main update loop overridden from BottingClass."""
        # 1. Initialize Team Manager (Once character is loaded)
        if not self._team_manager_initialized:
            try:
                self.team_manager.initialize()
                if self.team_manager.config.character_name:
                    self._team_manager_initialized = True
            except:
                pass
        
        # 2. Update Subsystems
        self.team_manager.update()
        
        # 3. Framework Update (FSM, Pcons, Events)
        super().Update()
        
        # 4. Playlist Management (The "Executor" Logic)
        self._manage_playlist()
        
        # 5. Draw UI
        self._draw_ui()

    def Routine(self):
        """Required override for BottingClass, but we build routines dynamically."""
        pass

    def _manage_playlist(self):
        """Checks if the current task finished and loads the next one."""
        # Only manage playlist if we explicitly started the bot
        if not self.is_bot_active:
            return

        # If the Framework FSM is running, let it run
        if self.config.fsm_running:
            return

        # If FSM stopped, it means the previous task finished (or we just started)
        # Check if we have a task currently marked as "active" in registry
        # If so, it just finished
        if self.task_registry.current_task_instance:
            finished_task = self.task_registry.current_task_instance
            Py4GW.Console.Log(BOT_NAME, f"Finished: {finished_task.name}", Py4GW.Console.MessageType.Success)
            self.task_registry.current_task_instance = None # Clear it
        
        # Get next task
        next_task = self.task_registry.get_next_task()
        
        if next_task:
            self._load_and_start_task(next_task)
        else:
            # Queue empty
            Py4GW.Console.Log(BOT_NAME, "Queue complete. Stopping.", Py4GW.Console.MessageType.Info)
            self.stop_bot()

    def _load_and_start_task(self, task):
        """Compiles a task into the FSM and starts it."""
        Py4GW.Console.Log(BOT_NAME, f"Starting: {task.name}", Py4GW.Console.MessageType.Info)
        
        # 1. Reset FSM
        self.config.FSM.reset()
        
        # 2. Build the Routine (The "Builder Pattern")
        try:
            # This calls the method in your Mission file to add steps to the bot
            task.create_routine(self)
            
            # Add a final step to ensure FSM stops cleanly if task runs out of steps
            self.States.AddCustomState(self.Stop, "Task Cleanup")
            
        except Exception as e:
            Py4GW.Console.Log(BOT_NAME, f"Error building task {task.name}: {e}", Py4GW.Console.MessageType.Error)
            self.stop_bot()
            return

        # 3. Start Execution
        self.Start()

    # ==================
    # PUBLIC API (For UI Buttons)
    # ==================
    
    def start_bot(self):
        """Start the playlist."""
        if not self.team_manager.has_valid_config():
            Py4GW.Console.Log(BOT_NAME, "Team Setup Required!", Py4GW.Console.MessageType.Error)
            return
            
        if self.task_registry.get_queue_length() == 0:
            Py4GW.Console.Log(BOT_NAME, "Queue is empty!", Py4GW.Console.MessageType.Error)
            return

        self.is_bot_active = True
        # The _manage_playlist loop will pick up the first task on next Update()

    def stop_bot(self):
        """Stop everything."""
        self.is_bot_active = False
        self.Stop() # Stops the Framework FSM
        Py4GW.Console.Log(BOT_NAME, "Bot stopped.", Py4GW.Console.MessageType.Warning)

    def toggle_pause(self):
        if self.config.fsm_running:
            self.Stop() # Pause framework
            self.is_bot_active = False # Stop playlist
            Py4GW.Console.Log(BOT_NAME, "Paused.", Py4GW.Console.MessageType.Warning)
        else:
            self.start_bot()

    def add_task_to_queue(self):
        self.task_registry.add_task_to_queue(
            self.selection.current_campaign, 
            self.selection.current_task_name, 
            self.selection.hard_mode
        )
        self.notifications.check_and_queue(
             self.selection.current_campaign, 
             self.selection.current_task_name, 
             self.selection.hard_mode
        )

    def clear_queue(self):
        self.task_registry.clear_queue()
        self.stop_bot()

    def refresh_task_list(self):
        self.selection.refresh_task_list()

    # ==================
    # UI PROPERTIES (Binding for Dashboard/Windows)
    # ==================
    
    @property
    def is_running(self):
        return self.config.fsm_running

    @property
    def is_paused(self):
        return not self.config.fsm_running and self.is_bot_active

    @property
    def current_task_name(self) -> str:
        if self.task_registry.current_task_instance:
            return self.task_registry.current_task_instance.name
        return "Ready"
        
    @property
    def current_task_instance(self):
        return self.task_registry.current_task_instance
    
    @property
    def pending_notifications(self):
        return self.notifications.pending

    # Helpers for Selection State (Forwarding to selection helper)
    @property
    def use_hard_mode(self): return self.selection.hard_mode
    @use_hard_mode.setter
    def use_hard_mode(self, v): self.selection.hard_mode = v
    @property
    def campaign_list(self): return self.selection.campaign_list
    @property
    def current_campaign(self): return self.selection.current_campaign
    @property
    def task_list(self): return self.selection.task_list
    @property
    def selected_task_name(self): return self.selection.current_task_name
    @property
    def selected_campaign_idx(self): return self.selection.campaign_idx
    @selected_campaign_idx.setter
    def selected_campaign_idx(self, v): self.selection.set_campaign(v)
    @property
    def selected_filter_idx(self): return self.selection.filter_idx
    @selected_filter_idx.setter
    def selected_filter_idx(self, v): self.selection.set_filter(v, TASK_FILTER_OPTIONS)
    @property
    def selected_task_idx(self): return self.selection.task_idx
    @selected_task_idx.setter
    def selected_task_idx(self, v): self.selection.set_task(v)
    @property
    def filter_options(self): return TASK_FILTER_OPTIONS

    def _draw_ui(self):
        self.dashboard.draw()
        self.queue_window.draw()
        self.task_info_window.draw()
        self.team_manager.draw_window()
        self.notification_window.draw()
        self.progress_window.draw()

# =========================================================
# Helper Classes (Selection State) - Kept internal to clean up
# =========================================================

class _SelectionState:
    """Handles the UI dropdown state logic."""
    def __init__(self, bot):
        self.bot = bot
        self.campaign_idx = 0
        self.task_idx = 0
        self.filter_idx = 0
        self.hard_mode = False
        self.campaign_list = []
        self.task_list = []
        
        self.initialize(CAMPAIGN_ORDER, TASK_FILTER_OPTIONS)

    def initialize(self, campaign_order, filter_options):
        # Load campaigns
        available = self.bot.task_registry.get_campaigns()
        self.campaign_list = [c for c in campaign_order if c in available]
        # Add any extras not in order
        for c in available:
            if c not in self.campaign_list:
                self.campaign_list.append(c)
        
        self.refresh_task_list()

    @property
    def current_campaign(self):
        if 0 <= self.campaign_idx < len(self.campaign_list):
            return self.campaign_list[self.campaign_idx]
        return ""

    @property
    def current_task_name(self):
        if 0 <= self.task_idx < len(self.task_list):
            return self.task_list[self.task_idx]
        return ""

    def set_campaign(self, idx):
        self.campaign_idx = idx
        self.task_idx = 0
        self.refresh_task_list()

    def set_task(self, idx):
        self.task_idx = idx

    def set_filter(self, idx, options):
        self.filter_idx = idx
        self.task_idx = 0
        self.refresh_task_list()

    def refresh_task_list(self):
        campaign = self.current_campaign
        tasks = self.bot.task_registry.get_tasks_for_campaign(campaign)
        tasks.sort()
        self.task_list = tasks
        # Filter logic can be added here if needed based on filter_idx

# Global instance
_bot_instance = None
def get_bot():
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = ZeroToHeroBot()
    return _bot_instance