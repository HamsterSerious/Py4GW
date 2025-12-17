"""
Base Task - Abstract base class for all missions, quests, and tasks.

Provides:
- Task metadata via INFO class attribute
- Execution lifecycle (started, finished, failed)
- Pre-run checks
- Mission Progress Tracking
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
                obj = self.add_objective("Go to X")
                yield from bot.movement.move_to(X)
                self.complete_objective("Go to X")
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
        """Updates the global status message shown at the top of the progress window."""
        # Prevent log spam by checking if the message is new
        if self.status_message == message:
            return

        self.status_message = message
        Py4GW.Console.Log(
            BOT_NAME, 
            f"Status Update: {message}", 
            Py4GW.Console.MessageType.Info
        )

    def complete_objective(self, name: str):
        """
        Marks an objective as complete by name.
        Also handles setting current_count to total_count.
        """
        for obj in self.objectives:
            if obj.name == name:
                obj.is_completed = True
                obj.current_count = obj.total_count
                obj.is_active = False
                
                Py4GW.Console.Log(
                    BOT_NAME, 
                    f"Objective Completed: {name}", 
                    Py4GW.Console.MessageType.Info
                )

    def set_active_objective(self, name: str):
        """Highlights a specific objective as active (orange arrow)."""
        for obj in self.objectives:
            is_new_active = (obj.name == name and not obj.is_active)
            obj.is_active = (obj.name == name)
            
            if is_new_active:
                Py4GW.Console.Log(
                    BOT_NAME, 
                    f"New Objective: {name}", 
                    Py4GW.Console.MessageType.Info
                )