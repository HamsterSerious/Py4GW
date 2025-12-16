"""
Team Manager UI - Handles all UI rendering for team management.

Responsibilities:
- Main team setup window
- Profile editor tabs
- Hero renaming interface
- Hero selection dropdowns
"""
import PyImGui
from Py4GWCoreLib.enums_src.Hero_enums import HeroType
from utils.string_utils import sanitize_string


class TeamManagerUI:
    """
    Handles all UI rendering for team management.
    """
    
    def __init__(self, config_manager, on_save_callback, on_test_load_callback):
        """
        Args:
            config_manager: TeamConfigManager instance
            on_save_callback: Function to call when user clicks Save
            on_test_load_callback: Function(party_size, mode) when user tests a profile
        """
        self.config = config_manager
        self.on_save = on_save_callback
        self.on_test_load = on_test_load_callback
        
        # UI State
        self.show_window = False
        self.selected_rename_hero_id = HeroType.Norgu.value
        self.hero_options = []  # [(hero_id, display_name), ...]
        
        self.refresh_hero_list()
    
    def draw(self):
        """Main draw function - call this every frame."""
        if not self.show_window:
            return
        
        if PyImGui.begin("Team Setup", 0):
            # Warning for new configs
            if self.config.is_new_config:
                PyImGui.text_colored("Please configure and Save your teams!", (1, 0, 0, 1))
                PyImGui.separator()
            
            # Tabbed interface
            if PyImGui.begin_tab_bar("Profiles"):
                # Party size tabs
                for size in [4, 6, 8]:
                    if PyImGui.begin_tab_item(f"{size}-Man"):
                        self._draw_party_size_tab(size)
                        PyImGui.end_tab_item()
                
                # Hero rename tab
                if PyImGui.begin_tab_item("Hero Rename"):
                    self._draw_rename_tab()
                    PyImGui.end_tab_item()
                
                PyImGui.end_tab_bar()
            
            PyImGui.separator()
            
            # Save & Close button
            if PyImGui.button("Save & Close", -1, 30):
                self.on_save()
                self.show_window = False
        
        PyImGui.end()
    
    def refresh_hero_list(self):
        """
        Rebuilds the hero options list with custom names.
        Call this after custom names are changed.
        """
        self.hero_options = []
        
        for hero in HeroType:
            if hero.value == 0:
                continue
            
            original_name = self.config.get_hero_nice_name(hero.value)
            custom_name = self.config.get_custom_hero_name(hero.value)
            
            if custom_name:
                display_name = f"{custom_name} ({original_name})"
            else:
                display_name = original_name
            
            self.hero_options.append((hero.value, display_name))
        
        # Sort alphabetically
        self.hero_options.sort(key=lambda x: x[1])
    
    def get_hero_display_name(self, hero_id):
        """Gets the display name for a hero ID."""
        if hero_id == 0:
            return "None"
        
        for id_val, name in self.hero_options:
            if id_val == hero_id:
                return name
        
        return f"Hero {hero_id}"
    
    # ==================
    # PRIVATE: TAB DRAWING
    # ==================
    
    def _draw_party_size_tab(self, size):
        """Draws the content for a party size tab (4, 6, or 8)."""
        PyImGui.text_colored("How to configure your team:", (0.7, 0.7, 0.7, 1.0))
        PyImGui.bullet()
        PyImGui.same_line(0.0, 0.0)
        PyImGui.text("Select a hero for each slot from the dropdown.")
        PyImGui.bullet()
        PyImGui.same_line(0.0, 0.0)
        PyImGui.text("Paste a build template code (optional) to auto-load skills.")
        PyImGui.dummy(0, 10)
        
        PyImGui.text_colored("Note:", (1.0, 0.5, 0.3, 1.0))
        PyImGui.same_line(0.0, 5.0)
        PyImGui.text("Mandatory heroes (from missions) will automatically")
        PyImGui.text("replace the first available hero slots (1, 2, etc).")
        PyImGui.separator()
        PyImGui.dummy(0, 5)
        
        # Normal and Hard Mode sections
        if PyImGui.collapsing_header(f"{size}-Man Normal Mode", PyImGui.TreeNodeFlags.DefaultOpen):
            self._draw_profile_editor(size, "NM")
        
        if PyImGui.collapsing_header(f"{size}-Man Hard Mode", PyImGui.TreeNodeFlags.DefaultOpen):
            self._draw_profile_editor(size, "HM")
    
    def _draw_profile_editor(self, party_size, mode):
        """Draws the profile editor for a specific party size and mode."""
        profile = self.config.get_profile(party_size, mode)
        
        # Test Load button
        if PyImGui.button(f"Test Load ({party_size}-Man {mode})", 0, 0):
            self.on_test_load(party_size, mode)
        
        PyImGui.dummy(0, 5)
        
        # Hero slots (party_size - 1 because player is slot 0)
        slots_needed = party_size - 1
        
        for i in range(slots_needed):
            # Ensure profile has enough hero entries
            while len(profile["heroes"]) <= i:
                profile["heroes"].append({"hero_id": 0, "build": ""})
            
            hero = profile["heroes"][i]
            
            PyImGui.push_id(f"{party_size}_{mode}_slot_{i}")
            
            # Slot number
            PyImGui.text(f"{i + 1}.")
            PyImGui.same_line(0.0, 10.0)
            
            # Hero dropdown
            current_hero_id = hero["hero_id"]
            current_name = self._get_hero_combo_label(current_hero_id)
            
            PyImGui.set_next_item_width(180)
            if PyImGui.begin_combo("##Hero", current_name, 0):
                # None option
                if PyImGui.selectable("-- None --", current_hero_id == 0, 0, (0, 0)):
                    hero["hero_id"] = 0
                
                PyImGui.separator()
                
                # All heroes
                for hero_id, hero_name in self.hero_options:
                    is_selected = (hero_id == current_hero_id)
                    if PyImGui.selectable(hero_name, is_selected, 0, (0, 0)):
                        hero["hero_id"] = hero_id
                
                PyImGui.end_combo()
            
            # Build code input
            PyImGui.same_line(0.0, 10.0)
            PyImGui.set_next_item_width(200)
            new_build = PyImGui.input_text("##Build", hero["build"], 64)
            
            # Sanitize and update
            new_build = sanitize_string(new_build)
            if new_build != hero["build"]:
                hero["build"] = new_build
            
            PyImGui.pop_id()
        
        # Update profile back to config
        self.config.set_profile(party_size, mode, profile)
        
        PyImGui.dummy(0, 5)
        PyImGui.separator()
    
    def _draw_rename_tab(self):
        """Draws the hero renaming interface."""
        PyImGui.text("Give your heroes custom names (e.g. build names):")
        PyImGui.separator()
        
        # Hero selector
        current_display_name = self.config.get_hero_nice_name(self.selected_rename_hero_id)
        custom_name = self.config.get_custom_hero_name(self.selected_rename_hero_id)
        
        if custom_name:
            current_display_name = f"{custom_name} ({current_display_name})"
        
        if PyImGui.begin_combo("Select Hero", current_display_name, 0):
            for hero in HeroType:
                if hero.value == 0:
                    continue
                
                std_name = self.config.get_hero_nice_name(hero.value)
                is_selected = (hero.value == self.selected_rename_hero_id)
                
                if PyImGui.selectable(std_name, is_selected, 0, (0, 0)):
                    self.selected_rename_hero_id = hero.value
            
            PyImGui.end_combo()
        
        # Name input
        current_custom = custom_name or ""
        new_val = PyImGui.input_text("Custom Name", current_custom, 64)
        new_val = sanitize_string(new_val)
        
        if new_val != current_custom:
            self.config.set_custom_hero_name(self.selected_rename_hero_id, new_val)
        
        # Save button
        PyImGui.same_line(0, 5)
        if PyImGui.button("Save", 0, 0):
            self.on_save()
        
        PyImGui.separator()
        PyImGui.text_disabled("Note: Changes update the 'Setup Team' dropdowns after Saving.")
    
    # ==================
    # HELPER METHODS
    # ==================
    
    def _get_hero_combo_label(self, hero_id):
        """Gets the label to display in a hero combo box."""
        if hero_id == 0:
            return "-- Select Hero --"
        
        for id_val, name in self.hero_options:
            if id_val == hero_id:
                return name
        
        return f"Hero {hero_id}"