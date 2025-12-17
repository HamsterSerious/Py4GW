"""
Task Executor - Handles task execution lifecycle.

Extracted from bot.py to reduce its responsibilities.
"""
import Py4GW
from Py4GWCoreLib import Player  # Added for CancelMove

from core.constants import BOT_NAME
from data.enums import TaskType, GameMode
from models.requirements import TaskRequirementsAccessor


class TaskExecutor:
    """
    Manages task execution lifecycle.
    
    Responsibilities:
    - Starting tasks from queue
    - Monitoring task completion
    - Pre-run checks
    - Coroutine management
    """
    
    def __init__(self, bot):
        """
        Args:
            bot: Reference to ZeroToHeroBot instance
        """
        self.bot = bot
        self.current_task = None
    
    @property
    def is_active(self) -> bool:
        """True if a task is currently executing."""
        return self.current_task is not None
    
    @property
    def current_task_name(self) -> str:
        """Name of current task, or empty string."""
        if self.current_task:
            return self.current_task.name
        return ""
    
    def update(self):
        """
        Update task execution. Call every frame when bot is running.
        
        Returns:
            True if execution should continue, False if queue finished
        """
        # We allow update() to run even when paused to monitor state,
        # but we prevent starting NEW tasks.
        if not self.bot.is_running:
            return True
            
        if self.bot.is_paused:
            return True # Just wait, don't start new tasks
        
        # Get next task if none active
        if not self.current_task:
            next_task = self.bot.task_registry.get_next_task()
            
            if next_task:
                self._start_task(next_task)
            else:
                return False  # Queue finished
        
        # Check task completion
        if self.current_task:
            if self.current_task.finished:
                self._on_task_finished()
            elif self.current_task.failed:
                self._on_task_failed()
                return False  # Stop on failure
        
        return True
    
    def stop(self):
        """Stop current task execution."""
        if self.current_task:
            self.bot.config.FSM.RemoveManagedCoroutine("MainTask")
            self.current_task = None
    
    def _start_task(self, task):
        """Start execution of a task."""
        self.current_task = task
        
        # Log start
        if task.task_type == TaskType.MISSION:
            mode_str = task.mode_string
            Py4GW.Console.Log(
                BOT_NAME, 
                f"Starting Mission: {task.name} [{mode_str}]", 
                Py4GW.Console.MessageType.Info
            )
        else:
            Py4GW.Console.Log(
                BOT_NAME, 
                f"Starting Task: {task.name}", 
                Py4GW.Console.MessageType.Info
            )
        
        # Pre-run check
        ready, reason = task.pre_run_check(self.bot)
        if not ready:
            Py4GW.Console.Log(
                BOT_NAME, 
                f"Task Skipped ({reason})", 
                Py4GW.Console.MessageType.Warning
            )
            self.current_task = None
            return
        
        # Start execution coroutine WITH PAUSE WRAPPER
        self.bot.config.FSM.AddManagedCoroutine(
            "MainTask", 
            self._execute_with_pause_logic(task)
        )

    def _execute_with_pause_logic(self, task):
        """
        Generator wrapper that injects pause handling into any task.
        """
        # Get the original task generator
        task_generator = task.execute(self.bot)
        was_paused = False
        
        try:
            while True:
                # --- PAUSE LOGIC ---
                if self.bot.is_paused:
                    if not was_paused:
                        # Just entered pause state: Stop character immediately
                        Player.CancelMove()
                        was_paused = True
                        # Optional: Log to console if desired, but button feedback is usually enough
                    
                    yield # Yield control back to engine without advancing task
                    continue
                
                # Reset state if we just unpaused
                if was_paused:
                    was_paused = False
                
                # --- EXECUTE TASK STEP ---
                # Advance the actual task by one step
                yield next(task_generator)
                
        except StopIteration:
            # Task finished naturally
            pass
        except Exception as e:
            # Task crashed
            Py4GW.Console.Log(BOT_NAME, f"Task Exception: {e}", Py4GW.Console.MessageType.Error)
            task.failed = True
            raise e
    
    def _on_task_finished(self):
        """Handle task completion."""
        Py4GW.Console.Log(
            BOT_NAME, 
            f"Task Finished: {self.current_task.name}", 
            Py4GW.Console.MessageType.Info
        )
        self.bot.config.FSM.RemoveManagedCoroutine("MainTask")
        self.current_task = None
    
    def _on_task_failed(self):
        """Handle task failure."""
        Py4GW.Console.Log(
            BOT_NAME, 
            f"Task Failed: {self.current_task.name}", 
            Py4GW.Console.MessageType.Error
        )
        self.bot.config.FSM.RemoveManagedCoroutine("MainTask")
        self.current_task = None


class NotificationManager:
    """
    Manages pending requirement notifications.
    
    Extracted from bot.py to reduce its responsibilities.
    """
    
    def __init__(self, bot):
        """
        Args:
            bot: Reference to ZeroToHeroBot instance
        """
        self.bot = bot
        self.pending = []  # List of notification dicts
    
    def check_and_queue(self, campaign: str, task_name: str, hard_mode: bool):
        """
        Check if a task has mandatory requirements and queue notification.
        
        Args:
            campaign: Campaign name
            task_name: Task display name
            hard_mode: Whether hard mode is selected
        """
        try:
            task_info = self.bot.task_registry.get_task_info(campaign, task_name)
            if not task_info:
                return
            
            # Determine which mode to check
            if task_info.task_type == TaskType.MISSION:
                game_mode = GameMode.from_bool(hard_mode)
            else:
                game_mode = GameMode.NORMAL
            
            mode_key = game_mode.value
            
            # Check for requirements
            accessor = TaskRequirementsAccessor(task_info)
            requirements = accessor.get_for_mode(game_mode)
            
            if requirements and requirements.has_requirements():
                # Check if already pending
                already_pending = any(
                    item['name'] == task_name and item['mode'] == mode_key
                    for item in self.pending
                )
                
                if not already_pending:
                    self.pending.append({
                        'name': task_name,
                        'mode': mode_key,
                        'requirements': requirements
                    })
                    
        except Exception as e:
            Py4GW.Console.Log(
                BOT_NAME, 
                f"Error checking requirements: {e}", 
                Py4GW.Console.MessageType.Error
            )
    
    def dismiss_current(self):
        """Dismiss the current (first) notification."""
        if self.pending:
            self.pending.pop(0)
    
    def clear(self):
        """Clear all pending notifications."""
        self.pending.clear()
    
    @property
    def has_pending(self) -> bool:
        """True if there are pending notifications."""
        return len(self.pending) > 0
    
    @property
    def current(self):
        """Get current notification or None."""
        if self.pending:
            return self.pending[0]
        return None


class SelectionState:
    """
    Manages campaign/task selection state.
    
    Extracted from bot.py to reduce its responsibilities.
    """
    
    def __init__(self, bot):
        """
        Args:
            bot: Reference to ZeroToHeroBot instance
        """
        self.bot = bot
        
        # Campaign selection
        self.campaign_idx = 0
        self.campaign_list = []
        
        # Filter selection
        self.filter_idx = 0
        
        # Task selection
        self.task_idx = 0
        self.task_list = []
        
        # Mode
        self.hard_mode = False
    
    def initialize(self, campaign_order: list, filter_options: list):
        """
        Initialize selection state.
        
        Args:
            campaign_order: Ordered list of campaign names
            filter_options: List of filter option strings
        """
        raw_campaigns = self.bot.task_registry.get_campaigns()
        self.campaign_list = sorted(
            raw_campaigns, 
            key=lambda x: campaign_order.index(x) if x in campaign_order else 999
        )
        
        self.campaign_idx = 0
        self.filter_idx = 0
        self.refresh_task_list()
    
    @property
    def current_campaign(self) -> str:
        """Currently selected campaign name."""
        if self.campaign_list:
            return self.campaign_list[self.campaign_idx]
        return "None"
    
    @property
    def current_task_name(self) -> str:
        """Currently selected task name."""
        if self.task_list:
            return self.task_list[self.task_idx]
        return "None"
    
    def set_campaign(self, idx: int):
        """Set campaign selection and refresh tasks."""
        if 0 <= idx < len(self.campaign_list):
            self.campaign_idx = idx
            self.refresh_task_list()
    
    def set_filter(self, idx: int, filter_options: list):
        """Set filter selection and refresh tasks."""
        if 0 <= idx < len(filter_options):
            self.filter_idx = idx
            self.refresh_task_list()
    
    def set_task(self, idx: int):
        """Set task selection."""
        if 0 <= idx < len(self.task_list):
            self.task_idx = idx
    
    def refresh_task_list(self):
        """Refresh task list based on current campaign and filter."""
        from core.constants import TASK_FILTER_OPTIONS
        
        all_tasks = self.bot.task_registry.get_tasks_for_campaign(self.current_campaign)
        filter_type = TASK_FILTER_OPTIONS[self.filter_idx]
        
        if filter_type == "All":
            self.task_list = all_tasks
        else:
            filtered = []
            for task_name in all_tasks:
                try:
                    info = self.bot.task_registry.get_task_info(self.current_campaign, task_name)
                    if info and info.task_type.value == filter_type:
                        filtered.append(task_name)
                except:
                    continue
            self.task_list = filtered
        
        self.task_idx = 0