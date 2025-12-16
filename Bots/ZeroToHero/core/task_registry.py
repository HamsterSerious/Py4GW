import os
import sys
import importlib
import pkgutil
import inspect
import Py4GW

from core.base_task import BaseTask


class QueuedTask:
    """Wrapper for a task in the queue with its settings."""
    def __init__(self, task_class, hard_mode=False):
        self.task_class = task_class
        self.hard_mode = hard_mode
        
        # Cache the name and type for display
        try:
            temp = task_class()
            self.name = temp.name
            self.task_type = temp.task_type
        except:
            self.name = "Unknown Task"
            self.task_type = "Task"
    
    def create_instance(self):
        """Creates a fresh instance of the task."""
        instance = self.task_class()
        instance.use_hard_mode = self.hard_mode
        return instance


class TaskRegistry:
    def __init__(self):
        self.available_tasks = {}  # { "Campaign": { "TaskName": TaskClass } }
        self.task_queue = []       # List of QueuedTask objects
        self.current_task_instance = None
        
        # Root path for campaigns - go up from core/ to ZeroToHero/, then to campaigns/
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
        
        if not os.path.exists(self.campaigns_path):
            Py4GW.Console.Log("TaskManager", f"Campaigns folder not found: {self.campaigns_path}", Py4GW.Console.MessageType.Error)
            return

        for item in os.listdir(self.campaigns_path):
            campaign_path = os.path.join(self.campaigns_path, item)
            
            if os.path.isdir(campaign_path) and item != "__pycache__":
                campaign_name = item
                self.available_tasks[campaign_name] = {}
                base_import_path = f"campaigns.{campaign_name}"
                
                # Determine scan strategy based on campaign
                if campaign_name == "extra":
                    # For 'extra', scan ALL subdirectories
                    self._scan_extra_campaign(campaign_path, base_import_path, campaign_name)
                else:
                    # For standard campaigns, scan missions/ and quests/
                    self._scan_standard_campaign(campaign_path, base_import_path, campaign_name)

    def _scan_standard_campaign(self, campaign_path, base_import_path, campaign_name):
        """
        Scans standard campaign structure (missions/ and quests/ folders).
        
        Args:
            campaign_path: Disk path to campaign folder
            base_import_path: Python import path (e.g., "campaigns.prophecies")
            campaign_name: Campaign name for logging
        """
        scan_targets = [
            ("missions", f"{base_import_path}.missions"),
            ("quests", f"{base_import_path}.quests"),
            ("", base_import_path)  # Also scan root
        ]

        for subfolder, import_path in scan_targets:
            target_dir = os.path.join(campaign_path, subfolder) if subfolder else campaign_path
            if os.path.exists(target_dir):
                self._scan_directory(target_dir, import_path, campaign_name)

    def _scan_extra_campaign(self, campaign_path, base_import_path, campaign_name):
        """
        Scans the 'extra' campaign by recursively scanning all subdirectories.
        This allows organizing extra tasks into categories like:
        - extra/skill_unlocks/
        - extra/farming/
        - extra/dailies/
        etc.
        
        Args:
            campaign_path: Disk path to extra campaign folder
            base_import_path: Python import path (e.g., "campaigns.extra")
            campaign_name: Always "extra"
        """
        # Scan all subdirectories in extra/
        for item in os.listdir(campaign_path):
            item_path = os.path.join(campaign_path, item)
            
            # Skip __pycache__ and non-directories
            if item == "__pycache__" or not os.path.isdir(item_path):
                continue
            
            # This is a category folder (e.g., "skill_unlocks")
            category_import_path = f"{base_import_path}.{item}"
            
            Py4GW.Console.Log(
                "TaskManager", 
                f"[{campaign_name}] Scanning category: {item}", 
                Py4GW.Console.MessageType.Info
            )
            
            # Scan this category folder for tasks
            self._scan_directory(item_path, category_import_path, campaign_name)

    def _scan_directory(self, disk_path, import_path, campaign_name):
        """
        Scans a directory for task modules (mission_*.py or quest_*.py).
        
        Args:
            disk_path: Full path to directory on disk
            import_path: Python import path for this directory
            campaign_name: Campaign name for logging
        """
        try:
            for _, name, _ in pkgutil.iter_modules([disk_path]):
                if name.startswith("mission_") or name.startswith("quest_"):
                    full_module_name = f"{import_path}.{name}"
                    try:
                        task_module = importlib.import_module(full_module_name)
                        
                        # Find task classes in the module
                        for attr_name in dir(task_module):
                            cls = getattr(task_module, attr_name)
                            
                            # Check if it's a valid task class
                            if (inspect.isclass(cls) and 
                                hasattr(cls, "GetInfo") and 
                                hasattr(cls, "Execution_Routine")):
                                
                                # Skip BaseTask itself
                                if cls is BaseTask or cls.__name__ == "BaseTask": 
                                    continue
                                
                                try:
                                    temp_inst = cls()
                                    info = temp_inst.GetInfo()
                                    task_display_name = info.get("Name", name)
                                    
                                    # Register the task
                                    self.available_tasks[campaign_name][task_display_name] = cls
                                    
                                    Py4GW.Console.Log(
                                        "TaskManager", 
                                        f"[{campaign_name}] Loaded: {task_display_name}", 
                                        Py4GW.Console.MessageType.Info
                                    )
                                except Exception as e:
                                    Py4GW.Console.Log(
                                        "TaskManager", 
                                        f"Failed to instantiate {attr_name}: {e}", 
                                        Py4GW.Console.MessageType.Warning
                                    )
                    except Exception as e:
                        Py4GW.Console.Log(
                            "TaskManager", 
                            f"Error loading {full_module_name}: {e}", 
                            Py4GW.Console.MessageType.Warning
                        )
        except Exception as e:
            Py4GW.Console.Log(
                "TaskManager", 
                f"Scan error in {disk_path}: {e}", 
                Py4GW.Console.MessageType.Error
            )

    def get_campaigns(self):
        """Returns list of available campaign names."""
        return list(self.available_tasks.keys())

    def get_tasks_for_campaign(self, campaign_name):
        """Returns list of task names for a campaign."""
        if campaign_name in self.available_tasks:
            return list(self.available_tasks[campaign_name].keys())
        return []

    # --- Queue Management ---

    def add_task_to_queue(self, campaign_name, task_name, hard_mode=False):
        """
        Adds a task to the queue.
        
        Args:
            campaign_name: The campaign the task belongs to
            task_name: The display name of the task
            hard_mode: Whether to run as Hard Mode (only applies to Missions)
        """
        if campaign_name in self.available_tasks and task_name in self.available_tasks[campaign_name]:
            task_class = self.available_tasks[campaign_name][task_name]
            
            # Create queued task wrapper
            queued = QueuedTask(task_class, hard_mode)
            
            # Only missions can be HM - quests ignore the flag
            if queued.task_type != "Mission":
                queued.hard_mode = False
            
            self.task_queue.append(queued)
            
            mode_str = "[HM]" if queued.hard_mode else "[NM]"
            if queued.task_type == "Mission":
                Py4GW.Console.Log("TaskManager", f"Enqueued {mode_str}: {task_name}", Py4GW.Console.MessageType.Info)
            else:
                Py4GW.Console.Log("TaskManager", f"Enqueued: {task_name}", Py4GW.Console.MessageType.Info)

    def set_queue_to_campaign(self, campaign_name, hard_mode=False):
        """Add all tasks from a campaign to the queue."""
        self.clear_queue()
        tasks = self.get_tasks_for_campaign(campaign_name)
        for t in tasks:
            self.add_task_to_queue(campaign_name, t, hard_mode)

    def clear_queue(self):
        """Clear the task queue."""
        self.task_queue.clear()
        self.current_task_instance = None
        Py4GW.Console.Log("TaskManager", "Queue cleared.", Py4GW.Console.MessageType.Info)

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

    def peek_next_task(self):
        """Returns info about the next task without removing it from queue."""
        if self.task_queue:
            return self.task_queue[0]
        return None

    def has_active_task(self):
        """Check if there's an active task running."""
        return self.current_task_instance is not None

    # --- Reordering Logic ---

    def remove_task_at_index(self, index):
        """Remove a task from the queue by index."""
        if 0 <= index < len(self.task_queue):
            removed = self.task_queue.pop(index)
            Py4GW.Console.Log("TaskManager", f"Removed from queue: {removed.name}", Py4GW.Console.MessageType.Info)

    def move_task_up(self, index):
        """Move a task up in the queue."""
        if index > 0 and index < len(self.task_queue):
            self.task_queue[index], self.task_queue[index - 1] = self.task_queue[index - 1], self.task_queue[index]
            Py4GW.Console.Log("TaskManager", f"Moved '{self.task_queue[index-1].name}' up.", Py4GW.Console.MessageType.Info)

    def move_task_down(self, index):
        """Move a task down in the queue."""
        if index < len(self.task_queue) - 1 and index >= 0:
            self.task_queue[index], self.task_queue[index + 1] = self.task_queue[index + 1], self.task_queue[index]
            Py4GW.Console.Log("TaskManager", f"Moved '{self.task_queue[index+1].name}' down.", Py4GW.Console.MessageType.Info)