"""
Base Task - Abstract base class for all missions, quests, and tasks.

Provides:
- Task metadata via INFO class attribute
- Execution lifecycle (started, finished, failed)
- Pre-run checks
"""
from typing import Generator, Tuple

from data.enums import TaskType, GameMode
from models.task import TaskInfo


class BaseTask:
    """
    Base class for all executable tasks (missions, quests, etc).
    
    Subclasses must:
    1. Override INFO with a TaskInfo instance
    2. Implement execute(bot) generator method
    3. Optionally override pre_run_check(bot)
    
    Example:
        class MyMission(BaseTask):
            INFO = TaskInfo(
                name="My Mission",
                description="Does something cool",
                task_type=TaskType.MISSION,
                start_map_id=123
            )
            
            def execute(self, bot):
                yield from bot.transition.travel_to(123)
                # ... mission logic
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
            
        Example:
            def execute(self, bot):
                yield from bot.transition.travel_to(self.INFO.start_map_id)
                yield from bot.movement.move_to(1000, 2000)
                self.finished = True
        """
        # Default implementation - override in subclasses
        self.finished = True
        yield
