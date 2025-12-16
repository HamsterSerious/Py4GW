"""
Task information window displaying mission/quest details.
"""
import PyImGui
import Py4GW

from core.constants import BOT_NAME, Colors, TASK_INFO_WINDOW_SIZE
from data.enums import TaskType, GameMode


class TaskInfoWindow:
    """Displays detailed information about a selected task."""
    
    def __init__(self, bot):
        """
        Args:
            bot: Reference to ZeroToHeroBot instance
        """
        self.bot = bot
        self.first_run = True
    
    def draw(self):
        """Draw the task info window."""
        if not self.bot.show_task_info_window:
            self.first_run = True
            return
        
        # Set initial window size on first open
        if self.first_run:
            PyImGui.set_next_window_size(*TASK_INFO_WINDOW_SIZE)
            self.first_run = False
        
        if PyImGui.begin("Task Details", 0):
            try:
                task_class = self._get_current_task_class()
                if task_class:
                    self._draw_task_info(task_class)
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
        return self.bot.task_registry.get_task_class(
            self.bot.current_campaign,
            self.bot.selected_task_name
        )
    
    def _draw_clickable_build(self, build_code, label):
        """Draw a build code that can be clicked to copy."""
        if not build_code or build_code == "Any":
            PyImGui.text(f"{label}: Any")
            return
        
        PyImGui.text_colored(f"{label}: {build_code}", (0.7, 1.0, 0.7, 1.0))
        if PyImGui.is_item_hovered():
            PyImGui.set_tooltip("Click to Copy Build Code")
        if PyImGui.is_item_clicked(0):
            PyImGui.set_clipboard_text(build_code)
            Py4GW.Console.Log(BOT_NAME, "Build code copied to clipboard.", Py4GW.Console.MessageType.Info)
    
    def _draw_task_info(self, task_class):
        """Draw the task information."""
        # Try new-style get_info() first
        if hasattr(task_class, 'get_info'):
            info = task_class.get_info()
            self._draw_task_info_from_dataclass(info)
        else:
            # Fall back to legacy GetInfo()
            temp_inst = task_class()
            legacy_info = temp_inst.GetInfo()
            self._draw_task_info_from_dict(legacy_info)
    
    def _draw_task_info_from_dataclass(self, info):
        """Draw task info from TaskInfo dataclass."""
        # Title and type
        PyImGui.text_colored(info.name, Colors.HEADER)
        
        task_type_str = info.task_type.value if isinstance(info.task_type, TaskType) else str(info.task_type)
        PyImGui.text_colored(f"Type: {task_type_str}", (0.6, 0.6, 0.6, 1.0))
        PyImGui.separator()
        
        # Description
        PyImGui.dummy(0, 5)
        PyImGui.text_wrapped(info.description or "No description.")
        PyImGui.dummy(0, 5)
        
        # Recommended builds
        if info.recommended_builds and info.recommended_builds != ["Any"]:
            PyImGui.text_colored("Recommended Builds:", Colors.HEADER)
            for build in info.recommended_builds:
                PyImGui.bullet()
                PyImGui.text(str(build))
            PyImGui.dummy(0, 5)
        
        # Hard mode tips
        if info.hm_tips:
            PyImGui.separator()
            PyImGui.text_colored("Hard Mode Strategy:", Colors.HM_COLOR)
            PyImGui.text_wrapped(info.hm_tips)
            PyImGui.dummy(0, 5)
        
        # Mandatory requirements
        if info.loadout and info.loadout.has_any_requirements():
            self._draw_mandatory_requirements_dataclass(info.loadout)
    
    def _draw_task_info_from_dict(self, info):
        """Draw task info from legacy dict format."""
        # Title and type
        PyImGui.text_colored(info.get('Name', 'Unknown'), Colors.HEADER)
        PyImGui.text_colored(f"Type: {info.get('Type', 'Task')}", (0.6, 0.6, 0.6, 1.0))
        PyImGui.separator()
        
        # Description
        PyImGui.dummy(0, 5)
        PyImGui.text_wrapped(info.get('Description', 'No description.'))
        PyImGui.dummy(0, 5)
        
        # Recommended builds
        builds = info.get('Recommended_Builds', [])
        if builds and builds != ["Any"]:
            PyImGui.text_colored("Recommended Builds:", Colors.HEADER)
            for build in builds:
                PyImGui.bullet()
                PyImGui.text(str(build))
            PyImGui.dummy(0, 5)
        
        # Hard mode tips
        hm_tips = info.get('HM_Tips', "")
        if hm_tips:
            PyImGui.separator()
            PyImGui.text_colored("Hard Mode Strategy:", Colors.HM_COLOR)
            PyImGui.text_wrapped(hm_tips)
            PyImGui.dummy(0, 5)
        
        # Mandatory requirements
        mandatory = info.get("Mandatory_Loadout", {})
        if mandatory:
            self._draw_mandatory_requirements_dict(mandatory)
    
    def _draw_mandatory_requirements_dataclass(self, loadout):
        """Draw mandatory loadout requirements from LoadoutConfig dataclass."""
        PyImGui.separator()
        PyImGui.text_colored("Mandatory Requirements:", Colors.WARN_COLOR)
        
        if loadout.normal_mode and loadout.normal_mode.has_requirements():
            if PyImGui.tree_node("Normal Mode Requirements"):
                self._draw_loadout_dataclass(loadout.normal_mode)
                PyImGui.tree_pop()
        
        if loadout.hard_mode and loadout.hard_mode.has_requirements():
            if PyImGui.tree_node("Hard Mode Requirements"):
                self._draw_loadout_dataclass(loadout.hard_mode)
                PyImGui.tree_pop()
    
    def _draw_loadout_dataclass(self, loadout):
        """Draw a single MandatoryLoadout dataclass."""
        # Player builds
        if loadout.player_build and loadout.player_build.has_requirements():
            pb = loadout.player_build
            if pb.builds:
                PyImGui.text("Player Builds:")
                for prof, code in pb.builds.items():
                    PyImGui.bullet()
                    self._draw_clickable_build(code, prof)
            
            if pb.equipment:
                PyImGui.text("Equipment:")
                PyImGui.bullet()
                PyImGui.text_wrapped(pb.equipment)
            
            if pb.weapons:
                PyImGui.text("Weapons:")
                for slot, desc in pb.weapons.items():
                    PyImGui.bullet()
                    PyImGui.text_wrapped(f"{slot}: {desc}")
        
        # Required heroes
        if loadout.required_heroes:
            PyImGui.text("Required Heroes:")
            for h in loadout.required_heroes:
                PyImGui.bullet()
                if h.hero_id > 0:
                    hero_label = f"Hero {h.hero_id}"
                else:
                    hero_label = h.role or "Strategy Hero"
                self._draw_clickable_build(h.build, hero_label)
        
        # Notes
        if loadout.notes:
            PyImGui.text_wrapped(f"Notes: {loadout.notes}")
    
    def _draw_mandatory_requirements_dict(self, mandatory):
        """Draw mandatory loadout requirements from legacy dict format."""
        PyImGui.separator()
        PyImGui.text_colored("Mandatory Requirements:", Colors.WARN_COLOR)
        
        if "NM" in mandatory and self._has_requirements_dict(mandatory["NM"]):
            if PyImGui.tree_node("Normal Mode Requirements"):
                self._draw_requirements_simple(mandatory["NM"])
                PyImGui.tree_pop()
        
        if "HM" in mandatory and self._has_requirements_dict(mandatory["HM"]):
            if PyImGui.tree_node("Hard Mode Requirements"):
                self._draw_requirements_simple(mandatory["HM"])
                PyImGui.tree_pop()
    
    def _has_requirements_dict(self, reqs):
        """Check if requirements dict has any actual content."""
        return (reqs.get("Player_Build") or reqs.get("Required_Heroes") or 
                reqs.get("Notes") or reqs.get("Equipment") or reqs.get("Weapons"))
    
    def _draw_requirements_simple(self, reqs):
        """Draw requirements in simple list format (legacy dict format)."""
        # Player builds
        if "Player_Build" in reqs and reqs["Player_Build"]:
            pb = reqs['Player_Build']
            if isinstance(pb, dict):
                PyImGui.text("Player Builds:")
                for prof, code in pb.items():
                    PyImGui.bullet()
                    self._draw_clickable_build(code, prof)
            else:
                self._draw_clickable_build(pb, "Player")
        
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
            PyImGui.text("Required Heroes:")
            for h in reqs["Required_Heroes"]:
                h_id = h.get('HeroID', 0)
                PyImGui.bullet()
                if h_id > 0:
                    hero_label = f"Hero {h_id}"
                else:
                    hero_label = h.get("Role", "Strategy Hero")
                self._draw_clickable_build(h.get('Build', 'Any'), hero_label)
        
        # Notes
        if "Notes" in reqs and reqs["Notes"]:
            PyImGui.text_wrapped(f"Notes: {reqs['Notes']}")