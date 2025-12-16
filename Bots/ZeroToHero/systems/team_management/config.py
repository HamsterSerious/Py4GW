import os
import json
import copy
import Py4GW
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from data.enums import HeroID
from utils.string_utils import sanitize_string


class TeamConfigManager:
    """
    Handles all configuration file operations for team profiles.
    Responsibilities:
    - Loading/Saving JSON configs
    - Profile management (get, set, validate)
    - Custom hero name management
    - Mission-specific hero assignments
    """
    
    def __init__(self, character_name=None):
        self.config_path = ""
        self.character_name = character_name or ""
        
        # Configuration data
        self.profiles = {}
        self.custom_hero_names = {}
        self.mission_hero_assignments = {}
        
        # State
        self.is_new_config = True
        
        # Default profile template
        self.default_profile = {
            "heroes": [
                {"hero_id": 0, "build": ""} for _ in range(7)
            ]
        }
    
    def initialize(self):
        """
        Sets up the config path and loads existing configuration.
        Returns True if successful, False otherwise.
        """
        if not self.character_name:
            raw_name = GLOBAL_CACHE.Player.GetName()
            if not raw_name:
                return False
            self.character_name = sanitize_string(raw_name)
        
        # Setup paths
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        config_dir = os.path.join(base_dir, "configs")
        
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        self.config_path = os.path.join(config_dir, f"TeamConfig_{self.character_name}.json")
        
        # Load or create config
        if os.path.exists(self.config_path):
            self.is_new_config = False
            self.load()
        else:
            self.is_new_config = True
            self._initialize_default_profiles()
            self._populate_default_merc_names()
        
        return True
    
    def load(self):
        """Loads configuration from disk."""
        if not os.path.exists(self.config_path):
            self._initialize_default_profiles()
            return
        
        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
            
            # Load legacy format (slots + builds arrays)
            if "profiles" in data:
                legacy_profiles = data["profiles"]
                self.profiles = self._convert_legacy_profiles(legacy_profiles)
            
            self.custom_hero_names = data.get("custom_hero_names", {})
            self.mission_hero_assignments = data.get("mission_hero_assignments", {})
            
            Py4GW.Console.Log("TeamConfigManager", "Configuration loaded.", Py4GW.Console.MessageType.Success)
            
        except Exception as e:
            Py4GW.Console.Log("TeamConfigManager", f"Error loading config: {e}", Py4GW.Console.MessageType.Error)
            self._initialize_default_profiles()
    
    def save(self):
        """Saves configuration to disk."""
        if not self.config_path:
            Py4GW.Console.Log("TeamConfigManager", "No config path set!", Py4GW.Console.MessageType.Error)
            return False
        
        try:
            # Sanitize all string data
            sanitized_profiles = self._sanitize_profiles(self.profiles)
            sanitized_names = {k: sanitize_string(v) for k, v in self.custom_hero_names.items()}
            
            save_data = {
                "profiles": sanitized_profiles,
                "custom_hero_names": sanitized_names,
                "mission_hero_assignments": self.mission_hero_assignments
            }
            
            with open(self.config_path, "w") as f:
                json.dump(save_data, f, indent=4)
            
            self.is_new_config = False
            Py4GW.Console.Log("TeamConfigManager", "Configuration saved.", Py4GW.Console.MessageType.Success)
            return True
            
        except Exception as e:
            Py4GW.Console.Log("TeamConfigManager", f"Error saving config: {e}", Py4GW.Console.MessageType.Error)
            return False
    
    # --- Profile Access ---
    
    def get_profile(self, party_size, mode):
        """
        Gets a team profile for the specified party size and mode.
        Args:
            party_size: 4, 6, or 8
            mode: "NM" or "HM"
        Returns:
            Profile dict with hero list
        """
        key = f"{party_size}_{mode}"
        return self.profiles.get(key, copy.deepcopy(self.default_profile))
    
    def set_profile(self, party_size, mode, profile):
        """Updates a profile."""
        key = f"{party_size}_{mode}"
        self.profiles[key] = profile
    
    def get_all_profile_keys(self):
        """Returns all valid profile keys."""
        return ["4_NM", "4_HM", "6_NM", "6_HM", "8_NM", "8_HM"]
    
    # --- Hero Name Management ---
    
    def get_custom_hero_name(self, hero_id):
        """Gets the custom name for a hero ID, or None if not set."""
        return self.custom_hero_names.get(str(hero_id))
    
    def set_custom_hero_name(self, hero_id, name):
        """Sets a custom name for a hero."""
        self.custom_hero_names[str(hero_id)] = sanitize_string(name)
    
    # --- Mission Hero Assignment ---
    
    def get_assigned_hero(self, mission_name, slot_index, default_hero_id=0):
        """Gets the hero assigned to a specific mission slot."""
        key = f"{mission_name}_{slot_index}"
        return self.mission_hero_assignments.get(key, default_hero_id)
    
    def set_assigned_hero(self, mission_name, slot_index, hero_id):
        """Assigns a hero to a specific mission slot."""
        key = f"{mission_name}_{slot_index}"
        if self.mission_hero_assignments.get(key) != hero_id:
            self.mission_hero_assignments[key] = hero_id
            return True  # Changed
        return False  # No change
    
    # --- Validation ---
    
    def has_valid_config(self):
        """Returns True if configuration has been set up by the user."""
        return not self.is_new_config
    
    # --- Private Helpers ---
    
    def _initialize_default_profiles(self):
        """Creates default empty profiles for all party sizes."""
        for key in self.get_all_profile_keys():
            if key not in self.profiles:
                self.profiles[key] = copy.deepcopy(self.default_profile)
    
    def _populate_default_merc_names(self):
        """Adds default names for mercenary heroes."""
        if not self.custom_hero_names:
            from data.enums import HeroID
            for i in range(1, 9):
                enum_name = f"MercenaryHero{i}"
                if hasattr(HeroID, enum_name):
                    hero_id = getattr(HeroID, enum_name)
                    self.custom_hero_names[str(hero_id.value)] = f"Mercenary {i}"
    
    def _convert_legacy_profiles(self, legacy_profiles):
        """
        Converts old parallel array format to new hero object format.
        Old: {"slots": [1,2,3], "builds": ["A","B","C"]}
        New: {"heroes": [{"hero_id": 1, "build": "A"}, ...]}
        """
        converted = {}
        
        for key, profile in legacy_profiles.items():
            # Check if already in new format
            if "heroes" in profile:
                converted[key] = profile
                continue
            
            # Convert from legacy format
            slots = profile.get("slots", [])
            builds = profile.get("builds", [])
            
            heroes = []
            for i in range(max(len(slots), len(builds), 7)):
                hero_id = slots[i] if i < len(slots) else 0
                build = builds[i] if i < len(builds) else ""
                heroes.append({"hero_id": hero_id, "build": build})
            
            converted[key] = {"heroes": heroes}
        
        return converted
    
    def _sanitize_profiles(self, profiles):
        """Sanitizes all string data in profiles."""
        sanitized = {}
        for key, profile in profiles.items():
            sanitized[key] = {
                "heroes": [
                    {
                        "hero_id": h["hero_id"],
                        "build": sanitize_string(h["build"])
                    }
                    for h in profile["heroes"]
                ]
            }
        return sanitized