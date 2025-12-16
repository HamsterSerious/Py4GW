"""
Zero To Hero Bot - Core business logic.
UI extracted to ui/ package.
"""
import Py4GW
from Py4GWCoreLib.Botting import BottingClass
from Py4GWCoreLib import ActionQueueManager

from core.constants import BOT_NAME, CAMPAIGN_ORDER, TASK_FILTER_OPTIONS
from core.task_registry import TaskRegistry
from data.enums import TaskType, GameMode
from systems.team_management.manager import TeamManager  
from systems.movement import Movement
from systems.combat import Combat
from systems.transition import Transition
from ui.dashboard import DashboardUI
from ui.notifications import NotificationWindow
from ui.queue_window import QueueWindow
from ui.task_info_window import TaskInfoWindow


class ZeroToHeroBot(BottingClass):
    """
    Main bot controller - handles business logic only.
    UI rendering delegated to ui/ package.
    """
    
    def __init__(self):
        super().__init__(bot_name=BOT_NAME)
        
        # UI Components
        self.dashboard = DashboardUI(self)
        self.notification_window = NotificationWindow(self)
        self.queue_window = QueueWindow(self)
        self.task_info_window = TaskInfoWindow(self)
        
        # Managers
        self.task_registry = TaskRegistry()
        self.team_manager = TeamManager(self)
        self.team_manager_initialized = False
        
        # Systems
        self.movement = Movement()
        self.combat = Combat()
        self.transition = Transition()
        
        # State
        self.is_running = False
        self.is_paused = False
        self.current_task_instance = None
        self.current_task_name = "Ready."
        
        # UI State
        self.show_queue_window = False
        self.show_task_info_window = False
        self.pending_notifications = []
        
        # Configuration State
        self.use_hard_mode = False
        
        # Campaign/Task Selection
        raw_campaigns = self.task_registry.get_campaigns()
        self.campaign_list = sorted(
            raw_campaigns, 
            key=lambda x: CAMPAIGN_ORDER.index(x) if x in CAMPAIGN_ORDER else 999
        )
        
        self.selected_campaign_idx = 0
        self.current_campaign = self.campaign_list[0] if self.campaign_list else "None"
        
        self.filter_options = TASK_FILTER_OPTIONS
        self.selected_filter_idx = 0
        
        self.task_list = self.get_filtered_tasks()
        self.selected_task_idx = 0
        self.selected_task_name = self.task_list[0] if self.task_list else "None"
        
        # FSM
        self.config.FSM.AddState(
            name="Bot_Idle_Loop",
            execute_fn=lambda: None,
            exit_condition=lambda: False,
            run_once=False
        )
        
        Py4GW.Console.Log(BOT_NAME, "Bot Initialized.", Py4GW.Console.MessageType.Info)
    
    # ==================
    # PUBLIC API
    # ==================
    
    def start_bot(self):
        """Start bot execution."""
        if not self.team_manager.HasValidConfig():
            Py4GW.Console.Log(
                BOT_NAME, 
                "Cannot start: Team Setup is required! Please configure your team.", 
                Py4GW.Console.MessageType.Error
            )
            return
        
        if not self.task_registry.task_queue and not self.current_task_instance:
            Py4GW.Console.Log(
                BOT_NAME, 
                "Cannot start: Queue is empty. Please add a task.", 
                Py4GW.Console.MessageType.Error
            )
            return
        
        self.is_running = True
        self.is_paused = False
        self.Start()
        Py4GW.Console.Log(BOT_NAME, "Bot Started.", Py4GW.Console.MessageType.Info)
    
    def stop_bot(self):
        """Stop bot execution."""
        self.is_running = False
        self.is_paused = False
        self.Stop()
        self.movement.Stop()
        self.config.FSM.RemoveManagedCoroutine("MainTask")
        self.current_task_instance = None
        self.current_task_name = "Stopped."
        Py4GW.Console.Log(BOT_NAME, "Bot Stopped.", Py4GW.Console.MessageType.Warning)
    
    def toggle_pause(self):
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        if self.is_paused:
            Py4GW.Console.Log(BOT_NAME, "Bot Paused.", Py4GW.Console.MessageType.Warning)
        else:
            Py4GW.Console.Log(BOT_NAME, "Bot Resumed.", Py4GW.Console.MessageType.Info)
    
    def add_task_to_queue(self):
        """Add currently selected task to queue and check for mandatory requirements."""
        # Add to queue
        self.task_registry.add_task_to_queue(
            self.current_campaign, 
            self.selected_task_name, 
            self.use_hard_mode
        )
        
        mode_indicator = " [HM]" if self.use_hard_mode else ""
        self.current_task_name = f"Added: {self.selected_task_name}{mode_indicator}"
        
        # Check for mandatory requirements
        self._check_mandatory_requirements()
    
    def clear_queue(self):
        """Clear the task queue."""
        self.task_registry.clear_queue()
        self.current_task_name = "Queue Cleared."
    
    def refresh_task_list(self):
        """Refresh the task list based on current filters."""
        self.task_list = self.get_filtered_tasks()
        self.selected_task_idx = 0
        self.selected_task_name = self.task_list[0] if self.task_list else "None"
    
    def get_filtered_tasks(self):
        """Get tasks for current campaign filtered by type."""
        all_tasks = self.task_registry.get_tasks_for_campaign(self.current_campaign)
        filter_type = self.filter_options[self.selected_filter_idx]
        
        if filter_type == "All":
            return all_tasks
        
        filtered_list = []
        for task_name in all_tasks:
            try:
                info = self.task_registry.get_task_info(self.current_campaign, task_name)
                if info:
                    # Compare enum value with filter string
                    if info.task_type.value == filter_type:
                        filtered_list.append(task_name)
            except:
                continue
        
        return filtered_list
    
    # ==================
    # INTERNAL LOGIC
    # ==================
    
    def Update(self):
        """Main update loop - called every frame."""
        # Initialize team manager
        if not self.team_manager_initialized:
            try:
                self.team_manager.Initialize()
                if self.team_manager.config.character_name:
                    self.team_manager_initialized = True
            except:
                pass
        
        # Update managers
        self.team_manager.Update()
        
        # Update bot
        super().Update()
        
        # Draw UI
        self.draw_ui()
        
        # Update task execution
        self.update_task_execution()
    
    def draw_ui(self):
        """Draw all UI windows."""
        self.dashboard.draw()
        self.queue_window.draw()
        self.task_info_window.draw()
        self.team_manager.DrawWindow()
        self.notification_window.draw()
    
    def update_task_execution(self):
        """Update the current task execution."""
        if not self.is_running or self.is_paused:
            return
        
        # Get next task if none active
        if not self.current_task_instance:
            next_task = self.task_registry.get_next_task()
            
            if next_task:
                self._start_task(next_task)
            else:
                self.current_task_name = "Queue Finished."
                self.stop_bot()
                return
        
        # Check task completion
        if self.current_task_instance:
            if self.current_task_instance.finished:
                Py4GW.Console.Log(
                    BOT_NAME, 
                    f"Task Finished: {self.current_task_instance.name}", 
                    Py4GW.Console.MessageType.Info
                )
                self.config.FSM.RemoveManagedCoroutine("MainTask")
                self.current_task_instance = None
            elif self.current_task_instance.failed:
                Py4GW.Console.Log(
                    BOT_NAME, 
                    f"Task Failed: {self.current_task_instance.name}", 
                    Py4GW.Console.MessageType.Error
                )
                self.stop_bot()
    
    def _start_task(self, task):
        """Start execution of a task."""
        self.current_task_instance = task
        self.current_task_name = task.name
        
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
        ready, reason = task.PreRunCheck(self)
        if not ready:
            Py4GW.Console.Log(
                BOT_NAME, 
                f"Task Skipped ({reason})", 
                Py4GW.Console.MessageType.Warning
            )
            self.current_task_instance = None
            return
        
        # Start execution - support both new execute() and legacy Execution_Routine()
        if hasattr(task, 'execute'):
            self.config.FSM.AddManagedCoroutine("MainTask", task.execute(self))
        else:
            self.config.FSM.AddManagedCoroutine("MainTask", task.Execution_Routine(self))
    
    def _check_mandatory_requirements(self):
        """Check if the added task has mandatory requirements and queue notification."""
        try:
            task_class = self.task_registry.get_task_class(
                self.current_campaign, 
                self.selected_task_name
            )
            if not task_class:
                return
            
            # Get task info
            info = self.task_registry.get_task_info(
                self.current_campaign,
                self.selected_task_name
            )
            
            if not info:
                return
            
            # Determine which mode to check
            game_mode = GameMode.from_bool(self.use_hard_mode) if info.task_type == TaskType.MISSION else GameMode.NORMAL
            req_mode_key = game_mode.value
            
            # Check for requirements using new dataclass format
            if info.loadout:
                loadout = info.loadout.get_for_mode(game_mode)
                if loadout and loadout.has_requirements():
                    # Check if already pending
                    already_pending = any(
                        item['name'] == self.selected_task_name and item['mode'] == req_mode_key
                        for item in self.pending_notifications
                    )
                    
                    if not already_pending:
                        self.pending_notifications.append({
                            'name': self.selected_task_name,
                            'mode': req_mode_key,
                            'requirements': loadout  # Pass the dataclass directly
                        })
                return
            
            # Fall back to legacy dict format
            temp_inst = task_class()
            legacy_info = temp_inst.GetInfo()
            mandatory = legacy_info.get("Mandatory_Loadout", {})
            
            if req_mode_key in mandatory:
                reqs = mandatory[req_mode_key]
                
                has_real_reqs = (
                    reqs.get("Player_Build") or 
                    reqs.get("Required_Heroes") or 
                    reqs.get("Notes") or 
                    reqs.get("Equipment") or 
                    reqs.get("Weapons")
                )
                
                if has_real_reqs:
                    already_pending = any(
                        item['name'] == self.selected_task_name and item['mode'] == req_mode_key
                        for item in self.pending_notifications
                    )
                    
                    if not already_pending:
                        self.pending_notifications.append({
                            'name': self.selected_task_name,
                            'mode': req_mode_key,
                            'requirements': reqs
                        })
                        
        except Exception as e:
            Py4GW.Console.Log(
                BOT_NAME, 
                f"Error checking requirements: {e}", 
                Py4GW.Console.MessageType.Error
            )
    
    def Routine(self):
        """Override base Routine - not used."""
        pass


# Global instance
_bot_instance = None

def get_bot():
    """Get or create the global bot instance."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = ZeroToHeroBot()
    return _bot_instance