"""
Task information window displaying mission/quest details.
"""
import PyImGui

from core.constants import Colors


class TaskInfoWindow:
    """Displays detailed information about a selected task."""
    
    def __init__(self, bot):
        """
        Args:
            bot: Reference to ZeroToHeroBot instance
        """
        self.bot = bot
    
    def draw(self):
        """Draw the task info window."""
        if not self.bot.show_task_info_window:
            return
        
        if PyImGui.begin("Task Details", 0):
            try:
                task_class = self._get_current_task_class()
                if task_class:
                    temp_inst = task_class()
                    info = temp_inst.GetInfo()
                    self._draw_task_info(info)
                else:
                    PyImGui.text_colored("Error: Task not found in registry.", Colors.ERROR_COLOR)
            except Exception as e:
                PyImGui.text_colored(f"Error fetching info: {str(e)}", Colors.ERROR_COLOR)
            
            PyImGui.separator()
            if PyImGui.button("Close", -1, 0):
                self.bot.show_task_info_window = False
        
        PyImGui.end()
    
    def _get_current_task_class(self):
        """Get the task class for the currently selected task."""
        campaign = self.bot.current_campaign
        task_name = self.bot.selected_task_name
        
        if (campaign in self.bot.task_registry.available_tasks and 
            task_name in self.bot.task_registry.available_tasks[campaign]):
            return self.bot.task_registry.available_tasks[campaign][task_name]
        return None
    
    def _draw_task_info(self, info):
        """Draw the task information."""
        # Title and type
        PyImGui.text_colored(f"{info.get('Name', 'Unknown')}", Colors.HEADER)
        PyImGui.text_colored(f"Type: {info.get('Type', 'Task')}", (0.6, 0.6, 0.6, 1.0))
        PyImGui.separator()
        
        # Description
        PyImGui.dummy(0, 5)
        PyImGui.text_wrapped(info.get('Description', 'No description.'))
        PyImGui.dummy(0, 5)
        
        # Recommended builds
        self._draw_recommended_builds(info)
        
        # Hard mode tips
        self._draw_hm_tips(info)
        
        # Mandatory requirements
        self._draw_mandatory_requirements(info)
    
    def _draw_recommended_builds(self, info):
        """Draw recommended builds section."""
        builds = info.get('Recommended_Builds', [])
        if builds and builds != ["Any"]:
            PyImGui.text_colored("Recommended Builds:", Colors.HEADER)
            for build in builds:
                PyImGui.bullet()
                PyImGui.text(str(build))
            PyImGui.dummy(0, 5)
    
    def _draw_hm_tips(self, info):
        """Draw hard mode strategy section."""
        hm_tips = info.get('HM_Tips', "")
        if hm_tips:
            PyImGui.separator()
            PyImGui.text_colored("Hard Mode Strategy:", Colors.HM_COLOR)
            PyImGui.text_wrapped(hm_tips)
            PyImGui.dummy(0, 5)
    
    def _draw_mandatory_requirements(self, info):
        """Draw mandatory loadout requirements."""
        mandatory = info.get("Mandatory_Loadout", {})
        if not mandatory:
            return
        
        PyImGui.separator()
        PyImGui.text_colored("Mandatory Requirements:", Colors.WARN_COLOR)
        
        if "NM" in mandatory and self._has_requirements(mandatory["NM"]):
            if PyImGui.tree_node("Normal Mode Requirements"):
                self._draw_requirements_simple(mandatory["NM"])
                PyImGui.tree_pop()
        
        if "HM" in mandatory and self._has_requirements(mandatory["HM"]):
            if PyImGui.tree_node("Hard Mode Requirements"):
                self._draw_requirements_simple(mandatory["HM"])
                PyImGui.tree_pop()
    
    def _has_requirements(self, reqs):
        """Check if requirements dict has any actual content."""
        return (reqs.get("Player_Build") or reqs.get("Required_Heroes") or 
                reqs.get("Notes") or reqs.get("Equipment") or reqs.get("Weapons"))
    
    def _draw_requirements_simple(self, reqs):
        """Draw requirements in simple list format."""
        # Player builds
        if "Player_Build" in reqs and reqs["Player_Build"]:
            pb = reqs['Player_Build']
            if isinstance(pb, dict):
                PyImGui.text("Player Builds:")
                for prof, code in pb.items():
                    PyImGui.bullet()
                    PyImGui.text(f"{prof}: {code}")
            else:
                PyImGui.text(f"Player: {pb}")
        
        # Equipment
        if "Equipment" in reqs and reqs["Equipment"]:
            PyImGui.text("Equipment:")
            eq = reqs["Equipment"]
            if isinstance(eq, dict):
                for k, v in eq.items():
                    PyImGui.bullet()
                    PyImGui.text_wrapped(f"{k}: {v}")
            else:
                PyImGui.text_wrapped(str(eq))
        
        # Weapons
        if "Weapons" in reqs and reqs["Weapons"]:
            PyImGui.text("Weapons:")
            wp = reqs["Weapons"]
            if isinstance(wp, dict):
                for k, v in wp.items():
                    PyImGui.bullet()
                    PyImGui.text_wrapped(f"{k}: {v}")
            else:
                PyImGui.text_wrapped(str(wp))
        
        # Required heroes
        if "Required_Heroes" in reqs and reqs["Required_Heroes"]:
            for h in reqs["Required_Heroes"]:
                h_id = h.get('HeroID', 0)
                if h_id > 0:
                    PyImGui.text(f"Hero {h_id}: {h.get('Build', 'Any')}")
                else:
                    role = h.get("Role", "Strategy Hero")
                    PyImGui.text(f"{role}: {h.get('Build', 'Any')}")
        
        # Notes
        if "Notes" in reqs and reqs["Notes"]:
            PyImGui.text_wrapped(f"Notes: {reqs['Notes']}")