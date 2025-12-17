"""
Task information window displaying mission/quest details.
"""
import PyImGui
import Py4GW

from core.constants import BOT_NAME, Colors, TASK_INFO_WINDOW_SIZE
from data.enums import TaskType, GameMode
from data.heroes import get_hero_display_name
from models.requirements import TaskRequirementsAccessor, LoadoutRequirements
from ui.base_window import ClosableWindow


class TaskInfoWindow(ClosableWindow):
    """Displays detailed information about a selected task."""
    
    TITLE = "Task Details"
    SIZE = TASK_INFO_WINDOW_SIZE
    
    @property
    def is_visible(self) -> bool:
        return self.bot.show_task_info_window
    
    def set_visible(self, visible: bool):
        self.bot.show_task_info_window = visible
    
    def draw_body(self):
        """Draw the task information."""
        try:
            task_class = self._get_current_task_class()
            if task_class:
                info = task_class.get_info()
                self._draw_task_info(info)
            else:
                PyImGui.text_colored("Error: Task not found in registry.", Colors.ERROR)
        except Exception as e:
            PyImGui.text_colored(f"Error fetching info: {str(e)}", Colors.ERROR)
    
    def _get_current_task_class(self):
        """Get the task class for the currently selected task."""
        return self.bot.task_registry.get_task_class(
            self.bot.current_campaign,
            self.bot.selected_task_name
        )
    
    def _draw_task_info(self, info):
        """Draw the task information from TaskInfo."""
        # Header
        PyImGui.text_colored(info.name, Colors.HEADER)
        task_type_str = info.task_type.value
        PyImGui.text_colored(f"Type: {task_type_str}", Colors.MUTED)
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
            PyImGui.text_colored("Hard Mode Strategy:", Colors.HARD_MODE)
            PyImGui.text_wrapped(info.hm_tips)
            PyImGui.dummy(0, 5)
        
        # Mandatory requirements
        accessor = TaskRequirementsAccessor(info)
        if accessor.has_any_requirements():
            self._draw_requirements(accessor)
    
    def _draw_requirements(self, accessor: TaskRequirementsAccessor):
        """Draw mandatory loadout requirements."""
        PyImGui.separator()
        PyImGui.text_colored("Mandatory Requirements:", Colors.WARNING)
        
        # Normal mode
        nm_reqs = accessor.get_for_mode(GameMode.NORMAL)
        if nm_reqs and nm_reqs.has_requirements():
            if PyImGui.tree_node("Normal Mode Requirements"):
                self._draw_loadout_requirements(nm_reqs)
                PyImGui.tree_pop()
        
        # Hard mode
        hm_reqs = accessor.get_for_mode(GameMode.HARD)
        if hm_reqs and hm_reqs.has_requirements():
            if PyImGui.tree_node("Hard Mode Requirements"):
                self._draw_loadout_requirements(hm_reqs)
                PyImGui.tree_pop()
    
    def _draw_loadout_requirements(self, reqs: LoadoutRequirements):
        """Draw a single mode's requirements."""
        # Player builds
        if reqs.player and reqs.player.has_requirements():
            self._draw_player_requirements(reqs.player)
        
        # Required heroes
        if reqs.heroes:
            self._draw_hero_requirements(reqs.heroes)
        
        # Notes
        if reqs.notes:
            PyImGui.text_wrapped(f"Notes: {reqs.notes}")
    
    def _draw_player_requirements(self, player):
        """Draw player build requirements."""
        if player.builds:
            PyImGui.text("Player Builds:")
            for prof, code in player.builds.items():
                PyImGui.bullet()
                self._draw_clickable_build(code, prof)
        
        if player.equipment:
            PyImGui.text("Equipment:")
            PyImGui.bullet()
            PyImGui.text_wrapped(player.equipment)
        
        if player.weapons:
            PyImGui.text("Weapons:")
            for slot, desc in player.weapons.items():
                PyImGui.bullet()
                PyImGui.text_wrapped(f"{slot}: {desc}")
    
    def _draw_hero_requirements(self, heroes):
        """Draw required heroes list."""
        PyImGui.text("Required Heroes:")
        for h in heroes:
            PyImGui.bullet()
            if h.hero_id > 0:
                hero_name = get_hero_display_name(h.hero_id)
                hero_label = f"{hero_name}"
            else:
                hero_label = h.role or "Strategy Hero"
            self._draw_clickable_build(h.build, hero_label)
    
    def _draw_clickable_build(self, build_code: str, label: str):
        """Draw a build code that can be clicked to copy."""
        # Case 1: "Any" or empty - Draw colored text but NO copy interaction
        if not build_code or build_code == "Any":
            # Using Colors.BUILD_CODE ensures it looks consistent with other entries
            PyImGui.text_colored(f"{label}: Any", Colors.BUILD_CODE)
            return
        
        # Case 2: Actual Build Code - Draw colored + Clickable
        PyImGui.text_colored(f"{label}: {build_code}", Colors.BUILD_CODE)
        
        # Interaction Logic
        if PyImGui.is_item_hovered():
            PyImGui.set_tooltip("Click to Copy Build Code")
            
        if PyImGui.is_item_clicked(0):
            PyImGui.set_clipboard_text(build_code)
            Py4GW.Console.Log(
                BOT_NAME, 
                f"Build code for {label} copied to clipboard.", 
                Py4GW.Console.MessageType.Info
            )