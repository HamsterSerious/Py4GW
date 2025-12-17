"""
Notification window for displaying mandatory loadout requirements.
"""
import PyImGui
import Py4GW
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from core.constants import BOT_NAME, Colors, NOTIFICATION_WINDOW_SIZE
from data.enums import GameMode
from data.heroes import get_hero_display_name
from models.requirements import (
    LoadoutRequirements, 
    HeroRequirements,
    TaskRequirementsAccessor
)
from ui.base_window import BaseWindow


class NotificationWindow(BaseWindow):
    """Displays mandatory loadout warnings before missions."""
    
    TITLE = "REQUIREMENT WARNING"
    SIZE = NOTIFICATION_WINDOW_SIZE
    
    @property
    def is_visible(self) -> bool:
        return len(self.bot.pending_notifications) > 0
    
    def draw(self):
        """Override draw to add custom title bar colors."""
        if not self.is_visible:
            self._first_run = True
            return
        
        if self._first_run:
            PyImGui.set_next_window_size(*self.SIZE)
            self._first_run = False
        
        # Custom title bar colors for warning
        PyImGui.push_style_color(PyImGui.ImGuiCol.TitleBg, Colors.WARNING)
        PyImGui.push_style_color(PyImGui.ImGuiCol.TitleBgActive, Colors.WARNING)
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, (0, 0, 0, 1))
        
        if PyImGui.begin(self.TITLE, 0):
            PyImGui.pop_style_color(3)
            self.draw_content()
        else:
            PyImGui.pop_style_color(3)
        
        PyImGui.end()
    
    def draw_content(self):
        """Draw the notification content."""
        data = self.bot.pending_notifications[0]
        name = data['name']
        mode = data['mode']
        reqs = data['requirements']
        
        # Convert to unified format if needed
        if isinstance(reqs, LoadoutRequirements):
            requirements = reqs
        else:
            # It's a MandatoryLoadout dataclass
            from models.requirements import LoadoutRequirements as LR
            requirements = LR.from_mandatory_loadout(reqs)
        
        self._draw_header(name, mode)
        
        if requirements:
            self._draw_player_build(requirements, name)
            self._draw_required_heroes(requirements, name)
            self._draw_notes(requirements)
        
        self._draw_footer()
    
    def _draw_header(self, name: str, mode: str):
        """Draw notification header."""
        PyImGui.text_colored(f"Mission: {name} [{mode}]", Colors.HEADER)
        PyImGui.separator()
        PyImGui.dummy(0, 5)
        
        PyImGui.text_wrapped("This mission requires a specific loadout to succeed!")
        PyImGui.dummy(0, 5)
        
        PyImGui.text_colored("Requirements:", Colors.WARNING)
    
    def _draw_player_build(self, reqs: LoadoutRequirements, mission_name: str):
        """Draw player build requirements."""
        if not reqs.player or not reqs.player.has_requirements():
            return
        
        PyImGui.bullet()
        PyImGui.text("Player Build:")
        
        # Get player profession
        try:
            player_id = GLOBAL_CACHE.Player.GetAgentID()
            prim, _ = GLOBAL_CACHE.Agent.GetProfessionNames(player_id)
        except:
            prim = "Unknown"
        
        build_code = reqs.player.get_build_for_profession(prim)
        
        PyImGui.indent(0.0)
        if build_code and build_code != "Any":
            self._draw_clickable_build(build_code, prim)
            
            # Test button
            if len(build_code) > 10 and " " not in build_code:
                if PyImGui.button(f"Test Loadout ({prim})", -1, 0):
                    self.bot.team_manager.test_routine = self.bot.team_manager.TestPlayerLoadout(
                        build_code, reqs.player.expected_skills
                    )
                PyImGui.text_disabled("(Warning: Overwrites current skills)")
        else:
            PyImGui.text_colored("No mandatory build for your profession.", Colors.MUTED)
        
        # Equipment
        if reqs.player.equipment:
            PyImGui.dummy(0, 5)
            PyImGui.text("Equipment:")
            PyImGui.text_wrapped(reqs.player.equipment)
        
        # Weapons
        if reqs.player.weapons:
            PyImGui.dummy(0, 5)
            PyImGui.text("Weapon Sets:")
            for slot, desc in reqs.player.weapons.items():
                PyImGui.text_colored(f"[{slot}]:", Colors.BUILD_CODE)
                PyImGui.same_line(0.0, -1.0)
                PyImGui.text_wrapped(str(desc))
        
        PyImGui.unindent(0.0)
    
    def _draw_required_heroes(self, reqs: LoadoutRequirements, mission_name: str):
        """Draw required heroes section."""
        if not reqs.heroes:
            return
        
        PyImGui.dummy(0, 5)
        PyImGui.bullet()
        PyImGui.text("Required Heroes:")
        
        req_count = len(reqs.heroes)
        PyImGui.indent(0.0)
        PyImGui.text_colored(
            f"These heroes will replace the first {req_count} slots of your party.",
            (0.6, 0.6, 1.0, 1.0)
        )
        
        for idx, hero_req in enumerate(reqs.heroes):
            PyImGui.separator()
            self._draw_hero_requirement(hero_req, idx, mission_name)
        
        PyImGui.dummy(0, 5)
        if PyImGui.button("Test Team Loadout (Load All Heroes)", -1, 0):
            self.bot.team_manager.test_routine = self.bot.team_manager.TestMandatoryHeroes(
                reqs.heroes, mission_name
            )
        
        PyImGui.unindent(0.0)
    
    def _draw_hero_requirement(self, hero_req: HeroRequirements, slot_index: int, mission_name: str):
        """Draw a single hero requirement."""
        if hero_req.hero_id > 0:
            # Fixed hero requirement
            h_name = get_hero_display_name(hero_req.hero_id)
            PyImGui.text_colored(f"Slot {slot_index+1}: {h_name}", Colors.HEADER)
            PyImGui.same_line(0.0, -1.0)
            PyImGui.text_colored("(Mandatory)", Colors.WARNING)
        else:
            # Flexible hero requirement
            role_name = hero_req.role or f"Strategy Slot {slot_index+1}"
            PyImGui.text_colored(f"Slot {slot_index+1}: {role_name}", Colors.HEADER)
            
            # Hero selector dropdown
            self._draw_hero_selector(mission_name, slot_index)
        
        # Equipment, weapons, and build
        PyImGui.indent(0.0)
        if hero_req.equipment:
            PyImGui.text_wrapped(f"Armor: {hero_req.equipment}")
        if hero_req.weapons:
            PyImGui.text_wrapped(f"Weapons: {hero_req.weapons}")
        if hero_req.has_build:
            self._draw_clickable_build(hero_req.build, "Build")
        PyImGui.unindent(0.0)
    
    def _draw_hero_selector(self, mission_name: str, slot_index: int):
        """Draw hero selection dropdown for flexible slots."""
        current_assigned = self.bot.team_manager.GetAssignedHero(mission_name, slot_index, 0)
        display_val = "-- Select Hero --"
        
        for op_id, op_name in self.bot.team_manager.hero_options:
            if op_id == current_assigned:
                display_val = op_name
                break
        
        if PyImGui.begin_combo(f"##SelHero_{slot_index}", display_val, 0):
            for op_id, op_name in self.bot.team_manager.hero_options:
                is_sel = (op_id == current_assigned)
                if PyImGui.selectable(op_name, is_sel, 0, (0, 0)):
                    self.bot.team_manager.SetAssignedHero(mission_name, slot_index, op_id)
            PyImGui.end_combo()
    
    def _draw_notes(self, reqs: LoadoutRequirements):
        """Draw general notes section."""
        if not reqs.notes:
            return
        
        PyImGui.dummy(0, 5)
        PyImGui.text_colored("Notes:", Colors.HEADER)
        PyImGui.text_wrapped(reqs.notes)
    
    def _draw_clickable_build(self, build_code: str, label: str):
        """Draw a build code that can be clicked to copy."""
        PyImGui.text_colored(f"[{label}]: {build_code}", Colors.BUILD_CODE)
        if PyImGui.is_item_hovered():
            PyImGui.set_tooltip("Click to Copy Build Code")
        if PyImGui.is_item_clicked(0):
            PyImGui.set_clipboard_text(build_code)
            Py4GW.Console.Log(
                BOT_NAME, 
                "Build code copied to clipboard.", 
                Py4GW.Console.MessageType.Info
            )
    
    def _draw_footer(self):
        """Draw the dismiss button."""
        PyImGui.dummy(0, 10)
        PyImGui.separator()
        
        if PyImGui.button("I Understand", -1, 30):
            self.bot.team_manager.DisbandParty()
            self.bot.pending_notifications.pop(0)
