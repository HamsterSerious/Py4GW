import os
import sys
import importlib
import pkgutil
import inspect
import Py4GW

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
        
        # Root path for modules
        self.modules_path = os.path.join(os.path.dirname(__file__), "Modules")
        
        self.refresh_tasks()

    def refresh_tasks(self):
        """
        Scans Modules/ for task files.
        """
        self.available_tasks = {}
        
        if not os.path.exists(self.modules_path):
            Py4GW.Console.Log("TaskManager", f"Modules folder not found: {self.modules_path}", Py4GW.Console.MessageType.Error)
            return

        for item in os.listdir(self.modules_path):
            campaign_path = os.path.join(self.modules_path, item)
            
            if os.path.isdir(campaign_path) and item != "__pycache__" and item != "Common":
                campaign_name = item
                self.available_tasks[campaign_name] = {}
                base_import_path = f"Bots.ZeroToHero.Modules.{campaign_name}"
                
                scan_targets = [
                    ("Missions", f"{base_import_path}.Missions"),
                    ("Quests",   f"{base_import_path}.Quests"),
                    ("",         base_import_path)
                ]

                for subfolder, import_path in scan_targets:
                    target_dir = os.path.join(campaign_path, subfolder) if subfolder else campaign_path
                    if os.path.exists(target_dir):
                        self._scan_directory(target_dir, import_path, campaign_name)

    def _scan_directory(self, disk_path, import_path, campaign_name):
        try:
            for _, name, _ in pkgutil.iter_modules([disk_path]):
                if name.startswith("Mission_") or name.startswith("Quest_"):
                    full_module_name = f"{import_path}.{name}"
                    try:
                        task_module = importlib.import_module(full_module_name)
                        for attr_name in dir(task_module):
                            cls = getattr(task_module, attr_name)
                            if inspect.isclass(cls) and hasattr(cls, "GetInfo") and hasattr(cls, "Execution_Routine"):
                                if cls.__name__ == "BaseTask": continue
                                try:
                                    temp_inst = cls()
                                    info = temp_inst.GetInfo()
                                    task_display_name = info.get("Name", name)
                                    self.available_tasks[campaign_name][task_display_name] = cls
                                    Py4GW.Console.Log("TaskManager", f"[{campaign_name}] Loaded: {task_display_name}", Py4GW.Console.MessageType.Info)
                                except Exception as e:
                                    pass
                    except Exception as e:
                        pass
        except Exception as e:
            Py4GW.Console.Log("TaskManager", f"Scan error in {disk_path}: {e}", Py4GW.Console.MessageType.Error)

    def get_campaigns(self):
        return list(self.available_tasks.keys())

    def get_tasks_for_campaign(self, campaign_name):
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
        self.clear_queue()
        tasks = self.get_tasks_for_campaign(campaign_name)
        for t in tasks:
            self.add_task_to_queue(campaign_name, t, hard_mode)

    def clear_queue(self):
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
        """
        Returns info about the next task without removing it from queue.
        """
        if self.task_queue:
            return self.task_queue[0]
        return None

    def has_active_task(self):
        return self.current_task_instance is not None

    # --- Reordering Logic ---

    def remove_task_at_index(self, index):
        if 0 <= index < len(self.task_queue):
            removed = self.task_queue.pop(index)
            Py4GW.Console.Log("TaskManager", f"Removed from queue: {removed.name}", Py4GW.Console.MessageType.Info)

    def move_task_up(self, index):
        if index > 0 and index < len(self.task_queue):
            self.task_queue[index], self.task_queue[index - 1] = self.task_queue[index - 1], self.task_queue[index]
            Py4GW.Console.Log("TaskManager", f"Moved '{self.task_queue[index-1].name}' up.", Py4GW.Console.MessageType.Info)

    def move_task_down(self, index):
        if index < len(self.task_queue) - 1 and index >= 0:
            self.task_queue[index], self.task_queue[index + 1] = self.task_queue[index + 1], self.task_queue[index]
            Py4GW.Console.Log("TaskManager", f"Moved '{self.task_queue[index+1].name}' down.", Py4GW.Console.MessageType.Info)