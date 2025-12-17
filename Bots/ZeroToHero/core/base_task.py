"""
Base Task - Abstract base class for all missions, quests, and tasks.

Provides:
- Task metadata via INFO class attribute
- Execution lifecycle (started, finished, failed)
- Pre-run checks
- Mission Progress Tracking
- Background monitor management
"""
from typing import Generator, Tuple, List
import Py4GW

from core.constants import BOT_NAME
from data.enums import TaskType, GameMode
from models.task import TaskInfo
from models.progress import TaskObjective


class BaseTask:
    """
    Base class for all executable tasks (missions, quests, etc).
    
    Subclasses must:
    1. Override INFO with a TaskInfo instance
    2. Implement execute(bot) generator method
    3. Optionally override pre_run_check(bot)
    
    Example:
        class MyMission(BaseTask):
            INFO = TaskInfo(...)
            
            def execute(self, bot):
                # Setup objectives
                obj = self.add_objective("Go to X")
                
                # Register background monitor (auto-cleaned up)
                self.register_monitor(bot, "BonusMonitor", self._monitor_bonus())
                
                try:
                    # Mission logic
                    yield from bot.movement.move_to(X)
                    self.complete_objective("Go to X")
                finally:
                    # Monitors are auto-cleaned, but other cleanup goes here
                    self.finished = True
    """
    
    # Class-level task info - override in subclasses
    INFO: TaskInfo = TaskInfo(
        name="Unnamed Task",
        description="No description provided.",
        task_type=TaskType.TASK
    )
    
    def __init__(self):
        # Execution state
        self.started = False
        self.finished = False
        self.failed = False
        
        # Mode configuration (set by QueuedTask.create_instance)
        self.use_hard_mode = False

        # Progress Tracking
        self.objectives: List[TaskObjective] = []
        self.status_message: str = "Initializing..."
        
        # Background Monitor Management
        self._registered_monitors: List[str] = []
    
    # ==================
    # PROPERTIES
    # ==================
    
    @property
    def name(self) -> str:
        """Task display name."""
        return self.INFO.name
    
    @property
    def task_type(self) -> TaskType:
        """Task type enum."""
        return self.INFO.task_type
    
    @property
    def game_mode(self) -> GameMode:
        """Current game mode based on use_hard_mode flag."""
        return GameMode.from_bool(self.use_hard_mode)
    
    @property
    def mode_string(self) -> str:
        """Mode as string ('NM' or 'HM')."""
        return self.game_mode.value
    
    # ==================
    # CLASS METHODS
    # ==================
    
    @classmethod
    def get_info(cls) -> TaskInfo:
        """
        Returns the TaskInfo for this task class.
        
        Returns:
            TaskInfo dataclass with task metadata
        """
        return cls.INFO
    
    # ==================
    # INSTANCE METHODS
    # ==================
    
    def pre_run_check(self, bot) -> Tuple[bool, str]:
        """
        Called before task execution starts.
        Override to add custom pre-run validation.
        
        Args:
            bot: The bot instance
            
        Returns:
            Tuple of (ready: bool, reason: str)
            If not ready, reason explains why
        """
        return (True, "")
    
    def execute(self, bot) -> Generator:
        """
        Main execution generator. Override in subclasses.
        
        Args:
            bot: The bot instance with access to all systems
            
        Yields:
            Control back to the bot loop
        """
        # Default implementation - override in subclasses
        self.finished = True
        yield

    # ==================
    # MONITOR MANAGEMENT
    # ==================

    def register_monitor(self, bot, name: str, coroutine) -> str:
        """
        Registers a background coroutine that runs alongside the main task.
        
        Monitors are automatically cleaned up when the task finishes (via cleanup_monitors).
        This eliminates manual try/finally blocks for each monitor.
        
        Args:
            bot: The bot instance
            name: Unique identifier for this monitor (will be prefixed with task name)
            coroutine: Generator function to run in background
            
        Returns:
            The full monitor name (for manual removal if needed)
            
        Example:
            self.register_monitor(bot, "BonusTracker", self._track_bonus(obj))
        """
        # Create unique name to avoid collisions between tasks
        full_name = f"{self.name}_{name}"
        
        # Register with FSM
        bot.config.FSM.AddManagedCoroutine(full_name, coroutine)
        
        # Track for auto-cleanup
        self._registered_monitors.append(full_name)
        
        Py4GW.Console.Log(
            BOT_NAME,
            f"Monitor registered: {full_name}",
            Py4GW.Console.MessageType.Info
        )
        
        return full_name

    def unregister_monitor(self, bot, name: str):
        """
        Manually unregisters a specific monitor.
        
        Usually not needed - monitors are auto-cleaned on task end.
        Use this if you need to stop a monitor mid-task.
        
        Args:
            bot: The bot instance
            name: The monitor name (as returned by register_monitor, or just the short name)
        """
        # Handle both short name and full name
        full_name = name if name.startswith(self.name) else f"{self.name}_{name}"
        
        if full_name in self._registered_monitors:
            bot.config.FSM.RemoveManagedCoroutine(full_name)
            self._registered_monitors.remove(full_name)
            
            Py4GW.Console.Log(
                BOT_NAME,
                f"Monitor unregistered: {full_name}",
                Py4GW.Console.MessageType.Info
            )

    def cleanup_monitors(self, bot):
        """
        Cleans up all registered monitors.
        
        Called automatically by TaskExecutor when task finishes.
        Can also be called manually in finally block for extra safety.
        
        Args:
            bot: The bot instance
        """
        for monitor_name in self._registered_monitors:
            try:
                bot.config.FSM.RemoveManagedCoroutine(monitor_name)
            except Exception as e:
                Py4GW.Console.Log(
                    BOT_NAME,
                    f"Error cleaning up monitor {monitor_name}: {e}",
                    Py4GW.Console.MessageType.Warning
                )
        
        if self._registered_monitors:
            Py4GW.Console.Log(
                BOT_NAME,
                f"Cleaned up {len(self._registered_monitors)} monitor(s)",
                Py4GW.Console.MessageType.Info
            )
        
        self._registered_monitors.clear()

    # ==================
    # PROGRESS HELPERS
    # ==================

    def add_objective(self, name: str, total: int = 1) -> TaskObjective:
        """
        Adds a new objective to the tracker.
        
        Args:
            name: Display name of objective
            total: Total count required (default 1)
            
        Returns:
            The created TaskObjective instance
        """
        obj = TaskObjective(name=name, total_count=total)
        self.objectives.append(obj)
        return obj

    def update_status(self, message: str):
        """
        Updates the global status message shown at the top of the progress window.
        
        Args:
            message: New status message
        """
        # Prevent log spam by checking if the message is new
        if self.status_message == message:
            return

        self.status_message = message
        Py4GW.Console.Log(
            BOT_NAME, 
            f"Status: {message}", 
            Py4GW.Console.MessageType.Info
        )

    def complete_objective(self, name: str):
        """
        Marks an objective as complete by name.
        Also handles setting current_count to total_count.
        
        Args:
            name: Name of objective to complete
        """
        for obj in self.objectives:
            if obj.name == name:
                obj.is_completed = True
                obj.current_count = obj.total_count
                obj.is_active = False
                
                Py4GW.Console.Log(
                    BOT_NAME, 
                    f"Objective Complete: {name}", 
                    Py4GW.Console.MessageType.Info
                )
                return
        
        # Objective not found - log warning
        Py4GW.Console.Log(
            BOT_NAME,
            f"Warning: Objective not found: {name}",
            Py4GW.Console.MessageType.Warning
        )

    def set_active_objective(self, name: str):
        """
        Highlights a specific objective as active (orange arrow in UI).
        Deactivates all other objectives.
        
        Args:
            name: Name of objective to activate
        """
        found = False
        for obj in self.objectives:
            was_active = obj.is_active
            obj.is_active = (obj.name == name)
            
            if obj.is_active and not was_active:
                found = True
                Py4GW.Console.Log(
                    BOT_NAME, 
                    f"Active Objective: {name}", 
                    Py4GW.Console.MessageType.Info
                )
        
        if not found:
            Py4GW.Console.Log(
                BOT_NAME,
                f"Warning: Objective not found: {name}",
                Py4GW.Console.MessageType.Warning
            )

    def fail_objective(self, name: str, reason: str = ""):
        """
        Marks an objective as failed.
        
        Args:
            name: Name of objective that failed
            reason: Optional reason for failure
        """
        for obj in self.objectives:
            if obj.name == name:
                obj.is_completed = False
                obj.is_active = True  # Highlight as warning
                
                msg = f"Objective Failed: {name}"
                if reason:
                    msg += f" ({reason})"
                
                Py4GW.Console.Log(
                    BOT_NAME,
                    msg,
                    Py4GW.Console.MessageType.Warning
                )
                return

    def get_objective(self, name: str) -> TaskObjective:
        """
        Gets an objective by name.
        
        Args:
            name: Name of objective to find
            
        Returns:
            TaskObjective instance or None if not found
        """
        for obj in self.objectives:
            if obj.name == name:
                return obj
        return None