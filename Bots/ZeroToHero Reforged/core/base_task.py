"""
Base Task - Abstract base class for all missions, quests, and tasks.

Provides:
- Task metadata via INFO class attribute
- Declarative build_routine() method for FSM construction
- Progress tracking for UI display
"""
from abc import abstractmethod
from typing import List, Callable, Any, Generator
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
    2. Implement build_routine(bot) method
    
    The build_routine() method is called ONCE when the task is queued.
    It declaratively adds states to the FSM using bot.Move.XY(), 
    bot.Wait.ForTime(), bot.States.AddCustomState(), etc.
    
    Example:
        class MyMission(BaseTask):
            INFO = TaskInfo(
                name="My Mission",
                description="Do the thing",
                task_type=TaskType.MISSION
            )
            
            def build_routine(self, bot):
                bot.States.AddHeader("Setup")
                bot.Map.Travel(target_map_id=123)
                bot.Wait.ForMapLoad(target_map_id=123)
                
                bot.States.AddHeader("Execute")
                bot.Move.XY(1000, 2000)
                bot.Interact.WithGadgetAtXY(1000, 2000)
                
                # For complex logic, use custom states
                bot.States.AddCustomState(
                    self._complex_logic,
                    "Complex Logic Step"
                )
                
                bot.Wait.ForMapToChange(target_map_id=456)
            
            def _complex_logic(self):
                # This is a generator for complex conditional logic
                from Py4GWCoreLib import Routines
                if some_condition:
                    yield from Routines.Yield.wait(1000)
                yield
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
    # ABSTRACT METHODS
    # ==================
    
    @abstractmethod
    def build_routine(self, bot) -> None:
        """
        Build the task routine by adding states to the FSM.
        
        This is called ONCE when the task is queued for execution.
        Does NOT yield - just calls declarative methods like:
        - bot.Move.XY(x, y)
        - bot.Wait.ForTime(ms)
        - bot.Interact.WithGadgetAtXY(x, y)
        - bot.States.AddCustomState(generator_fn, "name")
        
        For complex conditional logic that can't be expressed
        declaratively, use bot.States.AddCustomState() with a
        generator function.
        
        Args:
            bot: The BottingClass instance with access to all systems
        """
        pass
    
    # ==================
    # PROGRESS HELPERS
    # ==================

    def add_objective(self, name: str, total: int = 1) -> TaskObjective:
        """
        Adds a new objective to the tracker.
        
        Note: With the declarative pattern, objectives are primarily
        for UI display. Use AddCustomState() to update them during
        execution.
        
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
        Updates the global status message shown in the progress window.
        
        Args:
            message: New status message
        """
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
        
        Py4GW.Console.Log(
            BOT_NAME,
            f"Warning: Objective not found: {name}",
            Py4GW.Console.MessageType.Warning
        )

    def set_active_objective(self, name: str):
        """
        Highlights a specific objective as active (orange arrow in UI).
        
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
                obj.is_active = True
                
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
    
    # ==================
    # HELPER METHODS FOR CUSTOM STATES
    # ==================
    
    def create_status_updater(self, message: str) -> Callable[[], Generator]:
        """
        Creates a simple generator that updates status and yields once.
        
        Useful for adding status updates between declarative steps:
        
            bot.States.AddCustomState(
                self.create_status_updater("Doing the thing..."),
                "Update Status"
            )
        
        Args:
            message: Status message to display
            
        Returns:
            Generator function for AddCustomState
        """
        def updater():
            self.update_status(message)
            yield
        return updater
    
    def create_objective_completer(self, objective_name: str) -> Callable[[], Generator]:
        """
        Creates a generator that completes an objective and yields once.
        
        Useful for marking objectives complete during FSM execution:
        
            bot.States.AddCustomState(
                self.create_objective_completer("Kill Boss"),
                "Complete Objective"
            )
        
        Args:
            objective_name: Name of objective to complete
            
        Returns:
            Generator function for AddCustomState
        """
        def completer():
            self.complete_objective(objective_name)
            yield
        return completer
    
    def create_objective_activator(self, objective_name: str) -> Callable[[], Generator]:
        """
        Creates a generator that activates an objective and yields once.
        
        Args:
            objective_name: Name of objective to activate
            
        Returns:
            Generator function for AddCustomState
        """
        def activator():
            self.set_active_objective(objective_name)
            yield
        return activator