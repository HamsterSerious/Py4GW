"""
Notification window for displaying mandatory loadout requirements.
"""
import PyImGui
import Py4GW
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.enums_src.Hero_enums import HeroType

from core.constants import BOT_NAME, Colors
from data.enums import TaskType, GameMode


class NotificationWindow:
    """Displays mandatory loadout warnings before missions."""
    
    def __init__(self, bot):
        """
        Args:
            bot: Reference to ZeroToHeroBot instance
        """
        self.bot = bot
    
    def draw(self):
        """Draw the notification window if there are pending notifications."""
        if not self.bot.pending_notifications:
            return
        
        PyImGui.push_style_color(PyImGui.ImGuiCol.TitleBg, Colors.WARN_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.TitleBgActive, Colors.WARN_COLOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, (0, 0, 0, 1))
        
        if PyImGui.begin("REQUIREMENT WARNING", 0):
            PyImGui.pop_style_color(3)
            
            data = self.bot.pending_notifications[0]
            name = data['name']
            mode = data['mode']
            reqs = data['requirements']
            
            self._draw_header(name, mode)
            self._draw_player_build(reqs)
            self._draw_equipment(reqs)
            self._draw_weapons(reqs)
            self._draw_required_heroes(reqs, name)
            self._draw_notes(reqs)
            
            self._draw_footer()
        else:
            PyImGui.pop_style_color(3)
        
        PyImGui.end()
    
    def _draw_header(self, name, mode):
        """Draw notification header."""
        PyImGui.text_colored(f"Mission: {name} [{mode}]", Colors.HEADER)
        PyImGui.separator()
        PyImGui.dummy(0, 5)
        
        PyImGui.text_wrapped("This mission requires a specific loadout to succeed!")
        PyImGui.dummy(0, 5)
        
        PyImGui.text_colored("Requirements:", Colors.WARN_COLOR)
    
    def _draw_player_build(self, reqs):
        """Draw player build requirements."""
        # Handle both dict and dataclass formats
        player_build = self._get_player_build(reqs)
        if not player_build:
            return
        
        PyImGui.bullet()
        PyImGui.text("Player Build:")
        
        try:
            player_id = GLOBAL_CACHE.Player.GetAgentID()
            prim, _ = GLOBAL_CACHE.Agent.GetProfessionNames(player_id)
        except:
            prim = "Unknown"
        
        build_code = self._get_player_build_code(player_build, prim)
        
        PyImGui.indent(0.0)
        if build_code and build_code != "No build for your profession":
            self._draw_clickable_build(build_code, prim)
            
            # Test button
            if len(build_code) > 10 and " " not in build_code and build_code != "Any":
                if PyImGui.button(f"Test Loadout ({prim})", -1, 0):
                    expected = self._get_expected_skills(reqs)
                    self.bot.team_manager.test_routine = self.bot.team_manager.TestPlayerLoadout(
                        build_code, expected
                    )
                PyImGui.text_disabled("(Warning: Overwrites current skills)")
        else:
            PyImGui.text_colored("No mandatory build for your profession.", (0.7, 0.7, 0.7, 1.0))
        PyImGui.unindent(0.0)
    
    def _get_player_build(self, reqs):
        """Extract player build from requirements (dict or dataclass)."""
        if isinstance(reqs, dict):
            return reqs.get("Player_Build")
        # Dataclass format
        if hasattr(reqs, 'player_build') and reqs.player_build:
            return reqs.player_build.builds
        return None
    
    def _get_expected_skills(self, reqs) -> int:
        """Extract expected skills from requirements."""
        if isinstance(reqs, dict):
            return reqs.get("Expected_Skills", 8)
        if hasattr(reqs, 'player_build') and reqs.player_build:
            return reqs.player_build.expected_skills
        return 8
    
    def _get_player_build_code(self, raw_build_data, profession):
        """Extract the appropriate build code for the player's profession."""
        if isinstance(raw_build_data, dict):
            if profession in raw_build_data:
                return raw_build_data[profession]
            elif "Any" in raw_build_data:
                return raw_build_data["Any"]
            else:
                return "No build for your profession"
        else:
            return str(raw_build_data)
    
    def _draw_clickable_build(self, build_code, label):
        """Draw a build code that can be clicked to copy."""
        PyImGui.text_colored(f"[{label}]: {build_code}", (0.7, 1.0, 0.7, 1.0))
        if PyImGui.is_item_hovered():
            PyImGui.set_tooltip("Click to Copy Build Code")
        if PyImGui.is_item_clicked(0):
            PyImGui.set_clipboard_text(build_code)
            Py4GW.Console.Log(BOT_NAME, "Build code copied to clipboard.", Py4GW.Console.MessageType.Info)
    
    def _draw_equipment(self, reqs):
        """Draw equipment requirements."""
        equipment = self._get_equipment(reqs)
        if not equipment:
            return
        
        PyImGui.dummy(0, 5)
        PyImGui.bullet()
        PyImGui.text("Equipment / Runes:")
        PyImGui.indent(0.0)
        
        if isinstance(equipment, dict):
            for k, v in equipment.items():
                PyImGui.text_colored(f"{k}:", (0.8, 0.8, 0.8, 1.0))
                PyImGui.same_line(0.0, -1.0)
                PyImGui.text_wrapped(str(v))
        else:
            PyImGui.text_wrapped(str(equipment))
        PyImGui.unindent(0.0)
    
    def _get_equipment(self, reqs):
        """Extract equipment from requirements."""
        if isinstance(reqs, dict):
            return reqs.get("Equipment")
        if hasattr(reqs, 'player_build') and reqs.player_build:
            return reqs.player_build.equipment
        return None
    
    def _draw_weapons(self, reqs):
        """Draw weapon requirements."""
        weapons = self._get_weapons(reqs)
        if not weapons:
            return
        
        PyImGui.dummy(0, 5)
        PyImGui.bullet()
        PyImGui.text("Weapon Sets:")
        PyImGui.indent(0.0)
        
        if isinstance(weapons, dict):
            for slot, desc in weapons.items():
                PyImGui.text_colored(f"[{slot}]:", (0.7, 1.0, 0.7, 1.0))
                PyImGui.same_line(0.0, -1.0)
                PyImGui.text_wrapped(str(desc))
        elif isinstance(weapons, list):
            for item in weapons:
                PyImGui.bullet()
                PyImGui.text_wrapped(str(item))
        else:
            PyImGui.text_wrapped(str(weapons))
        PyImGui.unindent(0.0)
    
    def _get_weapons(self, reqs):
        """Extract weapons from requirements."""
        if isinstance(reqs, dict):
            return reqs.get("Weapons")
        if hasattr(reqs, 'player_build') and reqs.player_build:
            return reqs.player_build.weapons
        return None
    
    def _draw_required_heroes(self, reqs, mission_name):
        """Draw required heroes section."""
        heroes = self._get_required_heroes(reqs)
        if not heroes:
            return
        
        PyImGui.dummy(0, 5)
        PyImGui.bullet()
        PyImGui.text("Required Heroes:")
        
        req_count = len(heroes)
        PyImGui.indent(0.0)
        PyImGui.text_colored(
            f"These heroes will replace the first {req_count} slots of your party.",
            (0.6, 0.6, 1.0, 1.0)
        )
        
        for idx, hero_req in enumerate(heroes):
            PyImGui.separator()
            self._draw_hero_requirement(hero_req, idx, mission_name)
        
        PyImGui.dummy(0, 5)
        if PyImGui.button("Test Team Loadout (Load All Heroes)", -1, 0):
            self.bot.team_manager.test_routine = self.bot.team_manager.TestMandatoryHeroes(
                heroes, mission_name
            )
        
        PyImGui.unindent(0.0)
    
    def _get_required_heroes(self, reqs):
        """Extract required heroes from requirements."""
        if isinstance(reqs, dict):
            return reqs.get("Required_Heroes")
        if hasattr(reqs, 'required_heroes'):
            return reqs.required_heroes
        return None
    
    def _draw_hero_requirement(self, hero_req, slot_index, mission_name):
        """Draw a single hero requirement."""
        # Handle both dict and dataclass formats
        h_id_req = self._get_hero_id(hero_req)
        h_build = self._get_hero_build(hero_req)
        h_eq = self._get_hero_equipment(hero_req)
        h_wep = self._get_hero_weapons(hero_req)
        
        if h_id_req > 0:
            # Fixed hero requirement
            h_name = self._get_hero_nice_name(h_id_req)
            PyImGui.text_colored(f"Slot {slot_index+1}: {h_name}", Colors.HEADER)
            PyImGui.same_line(0.0, -1.0)
            PyImGui.text_colored("(Mandatory)", Colors.WARN_COLOR)
        else:
            # Flexible hero requirement
            role_name = self._get_hero_role(hero_req) or f"Strategy Slot {slot_index+1}"
            PyImGui.text_colored(f"Slot {slot_index+1}: {role_name}", Colors.HEADER)
            
            # Hero selector dropdown
            self._draw_hero_selector(mission_name, slot_index)
        
        # Equipment, weapons, and build
        PyImGui.indent(0.0)
        if h_eq:
            PyImGui.text_wrapped(f"Armor: {h_eq}")
        if h_wep:
            PyImGui.text_wrapped(f"Weapons: {h_wep}")
        if h_build:
            self._draw_clickable_build(h_build, "Build")
        PyImGui.unindent(0.0)
    
    def _get_hero_id(self, hero_req) -> int:
        """Extract hero_id from dict or dataclass."""
        if isinstance(hero_req, dict):
            return hero_req.get("HeroID", 0)
        return getattr(hero_req, 'hero_id', 0)
    
    def _get_hero_build(self, hero_req) -> str:
        """Extract build from dict or dataclass."""
        if isinstance(hero_req, dict):
            return hero_req.get("Build", "")
        return getattr(hero_req, 'build', "")
    
    def _get_hero_equipment(self, hero_req) -> str:
        """Extract equipment from dict or dataclass."""
        if isinstance(hero_req, dict):
            return hero_req.get("Equipment", "")
        return getattr(hero_req, 'equipment', "")
    
    def _get_hero_weapons(self, hero_req) -> str:
        """Extract weapons from dict or dataclass."""
        if isinstance(hero_req, dict):
            return hero_req.get("Weapons", "")
        return getattr(hero_req, 'weapons', "")
    
    def _get_hero_role(self, hero_req) -> str:
        """Extract role from dict or dataclass."""
        if isinstance(hero_req, dict):
            return hero_req.get("Role", "")
        return getattr(hero_req, 'role', "")
    
    def _get_hero_nice_name(self, hero_id: int) -> str:
        """Get display name for a hero ID."""
        if hero_id == 0:
            return "None"
        try:
            return self.bot.team_manager.config.get_hero_nice_name(hero_id)
        except:
            return HeroType(hero_id).name if hero_id > 0 else "Unknown"
    
    def _draw_hero_selector(self, mission_name, slot_index):
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
                    current_assigned = op_id
            PyImGui.end_combo()
    
    def _draw_notes(self, reqs):
        """Draw general notes section."""
        notes = self._get_notes(reqs)
        if not notes:
            return
        
        PyImGui.dummy(0, 5)
        PyImGui.text_colored("Notes:", Colors.HEADER)
        PyImGui.text_wrapped(notes)
    
    def _get_notes(self, reqs) -> str:
        """Extract notes from requirements."""
        if isinstance(reqs, dict):
            return reqs.get("Notes", "")
        return getattr(reqs, 'notes', "")
    
    def _draw_footer(self):
        """Draw the dismiss button."""
        PyImGui.dummy(0, 10)
        PyImGui.separator()
        
        if PyImGui.button("I Understand", -1, 30):
            self.bot.team_manager.DisbandParty()
            self.bot.pending_notifications.pop(0)