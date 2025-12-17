"""
Task Registry - Discovery and queue management for tasks.

Handles:
- Scanning campaign folders for task files
- Managing the execution queue
- Task class lookup
"""
import os
import importlib
import pkgutil
import inspect
import Py4GW

from core.base_task import BaseTask
from data.enums import TaskType
from models.task import TaskInfo, QueuedTask


class TaskRegistry:
    """
    Manages task discovery and the execution queue.
    
    Scans campaign folders for mission_*.py and quest_*.py files,
    loads task classes, and manages the execution queue.
    """
    
    def __init__(self):
        self.available_tasks = {}  # { "Campaign": { "TaskName": TaskClass } }
        self.task_info_cache = {}  # { "Campaign": { "TaskName": TaskInfo } }
        self.task_queue = []       # List of QueuedTask objects
        self.current_task_instance = None
        
        # Root path for campaigns
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.campaigns_path = os.path.join(base_dir, "campaigns")
        
        self.refresh_tasks()

    def refresh_tasks(self):
        """
        Scans campaigns/ for task files.
        For standard campaigns: scans missions/ and quests/ folders
        For 'extra' campaign: scans ALL subdirectories recursively
        """
        self.available_tasks = {}
        self.task_info_cache = {}
        
        if not os.path.exists(self.campaigns_path):
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"Campaigns folder not found: {self.campaigns_path}", 
                Py4GW.Console.MessageType.Error
            )
            return

        for item in os.listdir(self.campaigns_path):
            campaign_path = os.path.join(self.campaigns_path, item)
            
            if os.path.isdir(campaign_path) and item != "__pycache__":
                campaign_name = item
                self.available_tasks[campaign_name] = {}
                self.task_info_cache[campaign_name] = {}
                base_import_path = f"campaigns.{campaign_name}"
                
                # Determine scan strategy based on campaign
                if campaign_name == "extra":
                    self._scan_extra_campaign(campaign_path, base_import_path, campaign_name)
                else:
                    self._scan_standard_campaign(campaign_path, base_import_path, campaign_name)

    def _scan_standard_campaign(self, campaign_path: str, base_import_path: str, campaign_name: str):
        """Scans standard campaign structure (missions/ and quests/ folders)."""
        scan_targets = [
            ("missions", f"{base_import_path}.missions"),
            ("quests", f"{base_import_path}.quests"),
            ("", base_import_path)  # Also scan root
        ]

        for subfolder, import_path in scan_targets:
            target_dir = os.path.join(campaign_path, subfolder) if subfolder else campaign_path
            if os.path.exists(target_dir):
                self._scan_directory(target_dir, import_path, campaign_name)

    def _scan_extra_campaign(self, campaign_path: str, base_import_path: str, campaign_name: str):
        """Scans the 'extra' campaign by recursively scanning all subdirectories."""
        for item in os.listdir(campaign_path):
            item_path = os.path.join(campaign_path, item)
            
            if item == "__pycache__" or not os.path.isdir(item_path):
                continue
            
            category_import_path = f"{base_import_path}.{item}"
            
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"[{campaign_name}] Scanning category: {item}", 
                Py4GW.Console.MessageType.Info
            )
            
            self._scan_directory(item_path, category_import_path, campaign_name)

    def _scan_directory(self, disk_path: str, import_path: str, campaign_name: str):
        """Scans a directory for task modules (mission_*.py or quest_*.py)."""
        try:
            for _, name, _ in pkgutil.iter_modules([disk_path]):
                if name.startswith("mission_") or name.startswith("quest_"):
                    full_module_name = f"{import_path}.{name}"
                    try:
                        task_module = importlib.import_module(full_module_name)
                        
                        for attr_name in dir(task_module):
                            cls = getattr(task_module, attr_name)
                            
                            if not self._is_valid_task_class(cls):
                                continue
                            
                            self._register_task(cls, campaign_name)
                            
                    except Exception as e:
                        Py4GW.Console.Log(
                            "TaskRegistry", 
                            f"Error loading {full_module_name}: {e}", 
                            Py4GW.Console.MessageType.Warning
                        )
        except Exception as e:
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"Scan error in {disk_path}: {e}", 
                Py4GW.Console.MessageType.Error
            )

    def _is_valid_task_class(self, cls) -> bool:
        """Check if a class is a valid task class."""
        if not inspect.isclass(cls):
            return False
        
        # Must be a subclass of BaseTask (but not BaseTask itself)
        if not issubclass(cls, BaseTask):
            return False
        
        if cls is BaseTask:
            return False
        
        # Must have get_info class method
        if not hasattr(cls, "get_info"):
            return False
        
        # Must have execute method
        if not hasattr(cls, "execute"):
            return False
        
        return True

    def _register_task(self, cls, campaign_name: str):
        """Register a task class and cache its info."""
        try:
            info = cls.get_info()
            task_display_name = info.name
            
            # Register the task
            self.available_tasks[campaign_name][task_display_name] = cls
            self.task_info_cache[campaign_name][task_display_name] = info
            
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"[{campaign_name}] Loaded: {task_display_name}", 
                Py4GW.Console.MessageType.Info
            )
            
        except Exception as e:
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"Failed to register {cls.__name__}: {e}", 
                Py4GW.Console.MessageType.Warning
            )

    # ==================
    # CAMPAIGN/TASK ACCESS
    # ==================

    def get_campaigns(self) -> list:
        """Returns list of available campaign names."""
        return list(self.available_tasks.keys())

    def get_tasks_for_campaign(self, campaign_name: str) -> list:
        """Returns list of task names for a campaign."""
        if campaign_name in self.available_tasks:
            return list(self.available_tasks[campaign_name].keys())
        return []

    def get_task_info(self, campaign_name: str, task_name: str) -> TaskInfo:
        """
        Get cached TaskInfo for a task.
        
        Args:
            campaign_name: Campaign the task belongs to
            task_name: Display name of the task
            
        Returns:
            TaskInfo or None if not found
        """
        if campaign_name in self.task_info_cache:
            return self.task_info_cache[campaign_name].get(task_name)
        return None

    def get_task_class(self, campaign_name: str, task_name: str):
        """
        Get the task class for a task.
        
        Returns:
            Task class or None if not found
        """
        if campaign_name in self.available_tasks:
            return self.available_tasks[campaign_name].get(task_name)
        return None

    # ==================
    # QUEUE MANAGEMENT
    # ==================

    def add_task_to_queue(self, campaign_name: str, task_name: str, hard_mode: bool = False):
        """
        Adds a task to the queue.
        
        Args:
            campaign_name: The campaign the task belongs to
            task_name: The display name of the task
            hard_mode: Whether to run as Hard Mode (only applies to Missions)
        """
        task_class = self.get_task_class(campaign_name, task_name)
        
        if task_class is None:
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"Task not found: {campaign_name}/{task_name}", 
                Py4GW.Console.MessageType.Error
            )
            return
        
        # Create queued task (handles HM flag validation internally)
        queued = QueuedTask(task_class=task_class, hard_mode=hard_mode)
        self.task_queue.append(queued)
        
        # Log
        if queued.task_type == TaskType.MISSION:
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"Enqueued [{queued.mode_string}]: {task_name}", 
                Py4GW.Console.MessageType.Info
            )
        else:
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"Enqueued: {task_name}", 
                Py4GW.Console.MessageType.Info
            )

    def set_queue_to_campaign(self, campaign_name: str, hard_mode: bool = False):
        """Add all tasks from a campaign to the queue."""
        self.clear_queue()
        tasks = self.get_tasks_for_campaign(campaign_name)
        for task_name in tasks:
            self.add_task_to_queue(campaign_name, task_name, hard_mode)

    def clear_queue(self):
        """Clear the task queue."""
        self.task_queue.clear()
        self.current_task_instance = None
        Py4GW.Console.Log("TaskRegistry", "Queue cleared.", Py4GW.Console.MessageType.Info)

    def get_next_task(self):
        """
        Gets the next task from the queue and creates a fresh instance.
        Returns the task instance with use_hard_mode already set.
        """
        if self.task_queue:
            queued = self.task_queue.pop(0)
            self.current_task_instance = queued.create_instance()
            return self.current_task_instance
        return None

    def peek_next_task(self) -> QueuedTask:
        """Returns the next QueuedTask without removing it from queue."""
        if self.task_queue:
            return self.task_queue[0]
        return None

    def has_active_task(self) -> bool:
        """Check if there's an active task running."""
        return self.current_task_instance is not None

    def get_queue_length(self) -> int:
        """Returns the number of tasks in the queue."""
        return len(self.task_queue)

    # ==================
    # QUEUE REORDERING
    # ==================

    def remove_task_at_index(self, index: int):
        """Remove a task from the queue by index."""
        if 0 <= index < len(self.task_queue):
            removed = self.task_queue.pop(index)
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"Removed from queue: {removed.name}", 
                Py4GW.Console.MessageType.Info
            )

    def move_task_up(self, index: int):
        """Move a task up in the queue."""
        if 0 < index < len(self.task_queue):
            self.task_queue[index], self.task_queue[index - 1] = \
                self.task_queue[index - 1], self.task_queue[index]
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"Moved '{self.task_queue[index-1].name}' up.", 
                Py4GW.Console.MessageType.Info
            )

    def move_task_down(self, index: int):
        """Move a task down in the queue."""
        if 0 <= index < len(self.task_queue) - 1:
            self.task_queue[index], self.task_queue[index + 1] = \
                self.task_queue[index + 1], self.task_queue[index]
            Py4GW.Console.Log(
                "TaskRegistry", 
                f"Moved '{self.task_queue[index+1].name}' down.", 
                Py4GW.Console.MessageType.Info
            )
