"""
Task-related data structures.
Defines TaskInfo metadata and QueuedTask for the execution queue.
"""
from dataclasses import dataclass, field
from typing import Optional, Type, TYPE_CHECKING, List

from data.enums import TaskType, GameMode
from .loadout import LoadoutConfig

if TYPE_CHECKING:
    from core.base_task import BaseTask


@dataclass
class TaskInfo:
    """
    Immutable metadata about a task.
    
    Contains all static information about a mission/quest/task
    that doesn't change during execution.
    
    Attributes:
        name: Display name of the task
        description: Detailed description
        task_type: TaskType enum (MISSION, QUEST, TASK)
        start_map_id: Required starting map (0 = any map)
        requires_quest_id: Required active quest (0 = none)
        recommended_builds: List of recommended build descriptions
        hm_tips: Strategy tips for Hard Mode
        loadout: Mandatory loadout configuration (optional)
    """
    name: str
    description: str = ""
    task_type: TaskType = TaskType.TASK
    start_map_id: int = 0
    requires_quest_id: int = 0
    recommended_builds: List[str] = field(default_factory=list)
    hm_tips: str = ""
    loadout: Optional[LoadoutConfig] = None
    
    def has_mandatory_loadout(self) -> bool:
        """Returns True if this task has mandatory loadout requirements."""
        return self.loadout is not None and self.loadout.has_any_requirements()
    
    def is_mission(self) -> bool:
        """Returns True if this is a mission (supports HM toggle)."""
        return self.task_type == TaskType.MISSION
    
    def is_quest(self) -> bool:
        """Returns True if this is a quest."""
        return self.task_type == TaskType.QUEST


@dataclass
class QueuedTask:
    """
    A task instance in the execution queue.
    
    Wraps a task class with its execution settings (like hard mode).
    
    Attributes:
        task_class: The BaseTask subclass to instantiate
        hard_mode: Whether to run in Hard Mode (only applies to missions)
    """
    task_class: Type['BaseTask']
    hard_mode: bool = False
    
    # Cached values (populated in __post_init__)
    _name: str = field(default="", repr=False, compare=False)
    _task_type: TaskType = field(default=TaskType.TASK, repr=False, compare=False)
    
    def __post_init__(self):
        """Cache task info on creation for efficient access."""
        try:
            info = self.task_class.get_info()
            self._name = info.name
            self._task_type = info.task_type
            
            # Only missions can be Hard Mode - quests ignore the flag
            if self._task_type != TaskType.MISSION:
                self.hard_mode = False
        except Exception:
            self._name = "Unknown Task"
            self._task_type = TaskType.TASK
    
    @property
    def name(self) -> str:
        """Display name of the queued task."""
        return self._name
    
    @property
    def task_type(self) -> TaskType:
        """Type of the queued task."""
        return self._task_type
    
    @property
    def game_mode(self) -> GameMode:
        """Game mode for this queued task."""
        return GameMode.from_bool(self.hard_mode)
    
    @property 
    def mode_string(self) -> str:
        """Mode string ("NM" or "HM") for display."""
        return self.game_mode.value
    
    def create_instance(self) -> 'BaseTask':
        """
        Create a fresh task instance for execution.
        
        Returns:
            New instance of the task with use_hard_mode set
        """
        instance = self.task_class()
        instance.use_hard_mode = self.hard_mode
        return instance
    
    def get_info(self) -> TaskInfo:
        """Get the TaskInfo for this queued task."""
        return self.task_class.get_info()
