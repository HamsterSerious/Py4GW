from Py4GWCoreLib import *

class BaseTask:
    """
    The parent class for all Missions, Quests, and Tasks.
    Every executable piece of content must inherit from this.
    """
    def __init__(self):
        # --- Metadata ---
        self.name = "Unnamed Task"
        self.description = "No description provided."
        self.task_type = "Task" # Can be "Mission", "Quest", or "Task"
        self.recommended_builds = []
        self.hm_tips = ""
        
        # --- Requirements (Auto-Checked) ---
        self.start_map_id = 0  # 0 = No specific map required
        self.requires_quest_id = 0 # 0 = No specific quest required
        
        # --- State Tracking ---
        self.started = False
        self.finished = False
        self.failed = False
        
        # --- Mode Settings (Set by TaskManager when task is loaded) ---
        self.use_hard_mode = False  # Only applies to Missions

    def GetInfo(self):
        """
        Returns the metadata used by the Dashboard UI and TaskManager.
        """
        return {
            "Name": self.name,
            "Description": self.description,
            "Type": self.task_type,
            "Recommended_Builds": self.recommended_builds,
            "HM_Tips": self.hm_tips
        }

    def PreRunCheck(self, bot):
        """
        Logic to run BEFORE the task starts.
        automatically checks Map ID if self.start_map_id is set.
        """
        # 1. Check Map
        if self.start_map_id != 0:
            current_map = Map.GetMapID()
            if current_map != self.start_map_id:
                # We are in the wrong place. 
                # Ideally, we return False and a reason so the bot can try to travel there.
                return False, f"Wrong Map. Current: {current_map}, Needed: {self.start_map_id}"

        # 2. Check Quest (Placeholder - assumes Quest Log handling exists in CoreLib)
        # if self.requires_quest_id != 0:
        #     if not Quest.IsActive(self.requires_quest_id):
        #         return False, "Required quest not active."

        return True, "Ready"

    def Execution_Routine(self, bot):
        """
        The CORE LOGIC generator.
        Override this in your Mission/Quest files.
        """
        if False:
            yield 
        
        Py4GW.Console.Log(self.name, "Execution_Routine not implemented!", Py4GW.Console.MessageType.Error)
        return

    def Reset(self):
        """
        Resets the task state.
        """
        self.started = False
        self.finished = False
        self.failed = False
        self.use_hard_mode = False