"""
Base Task - Abstract base class for all missions, quests, and tasks.
Reforged for Builder Pattern (Py4GW Framework).
"""
from abc import ABC, abstractmethod
from typing import Tuple, List, Callable
import Py4GW

from core.constants import BOT_NAME
from data.enums import TaskType, GameMode
from models.task import TaskInfo
from models.progress import TaskObjective


class BaseTask(ABC):
    """
    Base class for all executable tasks.
    
    Subclasses must:
    1. Override INFO with a TaskInfo instance.
    2. Implement create_routine(bot) -> None.
    
    The create_routine method is a BUILDER. It does not run logic itself.
    It adds states to the bot's FSM queue.
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
        
        # Mode configuration
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
        return self.INFO.name
    
    @property
    def task_type(self) -> TaskType:
        return self.INFO.task_type
    
    @property
    def game_mode(self) -> GameMode:
        return GameMode.from_bool(self.use_hard_mode)
    
    @property
    def mode_string(self) -> str:
        return self.game_mode.value
    
    # ==================
    # CLASS METHODS
    # ==================
    
    @classmethod
    def get_info(cls) -> TaskInfo:
        return cls.INFO
    
    # ==================
    # ABSTRACT METHODS (The New Builder Contract)
    # ==================
    
    def pre_run_check(self, bot) -> Tuple[bool, str]:
        """
        Optional check before building the routine.
        """
        return (True, "")

    @abstractmethod
    def create_routine(self, bot) -> None:
        """
        The Builder Function.
        
        This method is called ONCE when the task starts.
        It should populate the bot's FSM with steps.
        
        Do NOT use 'yield' here.
        
        Example:
            bot.States.AddHeader("Step 1")
            bot.Move.XY(100, 200)
            bot.States.AddCustomState(self.my_custom_func, "My Logic")
        """
        pass

    # ==================
    # MONITOR MANAGEMENT (Compatible with FSM)
    # ==================

    def register_monitor(self, bot, name: str, coroutine) -> str:
        """
        Registers a background coroutine (like health monitoring).
        """
        full_name = f"{self.name}_{name}"
        
        # Safety check: Ensure FSM is accessible
        if hasattr(bot, 'config') and hasattr(bot.config, 'FSM'):
            bot.config.FSM.AddManagedCoroutine(full_name, coroutine)
            self._registered_monitors.append(full_name)
            Py4GW.Console.Log(BOT_NAME, f"Monitor started: {full_name}", Py4GW.Console.MessageType.Info)
        
        return full_name

    def cleanup_monitors(self, bot):
        """
        Cleans up all registered monitors.
        Call this in your final cleanup state if needed, though
        Bot.Stop() usually handles this.
        """
        for monitor_name in self._registered_monitors:
            try:
                if hasattr(bot, 'config') and hasattr(bot.config, 'FSM'):
                    bot.config.FSM.RemoveManagedCoroutine(monitor_name)
            except:
                pass
        self._registered_monitors.clear()

    # ==================
    # PROGRESS HELPERS
    # ==================

    def add_objective(self, name: str, total: int = 1) -> TaskObjective:
        obj = TaskObjective(name=name, total_count=total)
        self.objectives.append(obj)
        return obj

    def update_status(self, message: str):
        if self.status_message != message:
            self.status_message = message
            Py4GW.Console.Log(BOT_NAME, f"Status: {message}", Py4GW.Console.MessageType.Info)

    def complete_objective(self, name: str):
        for obj in self.objectives:
            if obj.name == name:
                obj.is_completed = True
                obj.current_count = obj.total_count
                obj.is_active = False
                Py4GW.Console.Log(BOT_NAME, f"Objective Complete: {name}", Py4GW.Console.MessageType.Info)
                return

    def set_active_objective(self, name: str):
        for obj in self.objectives:
            obj.is_active = (obj.name == name)

    def fail_objective(self, name: str, reason: str = ""):
        for obj in self.objectives:
            if obj.name == name:
                obj.is_completed = False
                obj.is_active = True
                Py4GW.Console.Log(BOT_NAME, f"Failed: {name} ({reason})", Py4GW.Console.MessageType.Warning)
                return