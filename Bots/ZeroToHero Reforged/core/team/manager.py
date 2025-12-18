"""
Team Manager - Coordinator for team management operations.
Location: core/team/manager.py
"""
import Py4GW
from Py4GWCoreLib import Routines
from data.heroes import get_hero_display_name, get_all_hero_options
from data.timing import Timing

# Relative imports for files in the same core/team/ folder
from .config import TeamConfigManager
from .composer import TeamComposer
from .validator import BuildValidator

# Import UI from the root ui package
from ui.team_window import TeamWindow

class TeamManager:
    """
    Coordinator for team management operations.
    """
    
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize components
        self.config = TeamConfigManager()
        self.composer = TeamComposer()
        self.validator = BuildValidator(self.composer)
        
        # UI reference
        self._ui = None
        
        # State
        self.is_party_ready = False
        self.test_routine = None
        self._initialized = False
        
        # Hero options cache
        self._hero_options = []
    
    # ==================
    # PROPERTIES
    # ==================
    
    @property
    def is_new_config(self) -> bool:
        return self.config.is_new_config
    
    @property
    def show_window(self) -> bool:
        if self._ui:
            return self._ui.show_window
        return False
    
    @show_window.setter
    def show_window(self, value: bool):
        if self._ui:
            self._ui.show_window = value
    
    @property
    def hero_options(self) -> list:
        return self._hero_options
    
    # ==================
    # PUBLIC API
    # ==================
    
    def initialize(self) -> bool:
        """Initializes the team manager."""
        if self._initialized:
            return True
        
        success = self.config.initialize()
        if success:
            self._refresh_hero_list()
            self._initialized = True
            
            # Create UI
            self._ui = TeamWindow(
                bot=self.bot,
                config_manager=self.config,
                on_save_callback=self.save_config,
                on_test_load_callback=self.start_test_load,
                hero_options=self._hero_options
            )
            
            Py4GW.Console.Log("TeamManager", "Initialized.", Py4GW.Console.MessageType.Info)
        
        return success
    
    def update(self):
        """Updates test routines."""
        if self.test_routine:
            try:
                next(self.test_routine)
            except StopIteration:
                self.test_routine = None
                Py4GW.Console.Log("TeamManager", "Test Sequence Complete.", Py4GW.Console.MessageType.Success)
            except Exception as e:
                self.test_routine = None
                Py4GW.Console.Log("TeamManager", f"Test Crash: {e}", Py4GW.Console.MessageType.Error)
    
    def draw_window(self):
        if self._ui:
            self._ui.draw()
    
    def has_valid_config(self) -> bool:
        return self.config.has_valid_config()
    
    def save_config(self):
        if self.config.save():
            self._refresh_hero_list()
            if self._ui:
                self._ui.refresh_hero_options(self._hero_options)
    
    # ==================
    # TEAM LOADING (Logic used in tasks)
    # ==================
    
    def load_team(self, party_size: int, mode: str = "NM"):
        """Loads a standard team from profile."""
        self.is_party_ready = False
        profile = self.config.get_profile(party_size, mode)
        
        Py4GW.Console.Log("TeamManager", f"Loading Profile: [{party_size}_{mode}]", Py4GW.Console.MessageType.Info)
        
        self.composer.disband_party()
        yield from Routines.Yield.wait(Timing.PARTY_DISBAND_WAIT)
        
        yield from self.composer.load_team(
            party_size=party_size,
            heroes=profile["heroes"],
            get_hero_name_fn=self._get_hero_display_name
        )
        
        self.is_party_ready = True
        Py4GW.Console.Log("TeamManager", "Party Assembled.", Py4GW.Console.MessageType.Success)
    
    def load_team_with_mandatory_heroes(self, party_size: int, mode: str, mandatory_list: list, mission_name: str = ""):
        """Loads team with mandatory hero requirements."""
        self.is_party_ready = False
        profile = self.config.get_profile(party_size, mode)
        
        Py4GW.Console.Log("TeamManager", f"Loading Profile: [{party_size}_{mode}] (Mandatory Override)", Py4GW.Console.MessageType.Info)
        
        self.composer.disband_party()
        yield from Routines.Yield.wait(Timing.PARTY_DISBAND_WAIT)
        
        yield from self.composer.load_team_with_mandatory_heroes(
            party_size=party_size,
            profile_heroes=profile["heroes"],
            mandatory_list=mandatory_list,
            mission_name=mission_name,
            get_assigned_hero_fn=self.config.get_assigned_hero,
            get_hero_name_fn=self._get_hero_display_name
        )
        
        self.is_party_ready = True
        Py4GW.Console.Log("TeamManager", "Party Assembled.", Py4GW.Console.MessageType.Success)

    def disband_party(self):
        self.composer.disband_party()
        self.is_party_ready = False

    # ==================
    # PRIVATE HELPERS
    # ==================
    
    def _refresh_hero_list(self):
        base_options = get_all_hero_options()
        self._hero_options = []
        for hero_id, base_name in base_options:
            custom_name = self.config.get_custom_hero_name(hero_id)
            display_name = f"{custom_name} ({base_name})" if custom_name else base_name
            self._hero_options.append((hero_id, display_name))
        self._hero_options.sort(key=lambda x: x[1])
    
    def _get_hero_display_name(self, hero_id: int) -> str:
        if hero_id == 0: return "None"
        for id_val, name in self._hero_options:
            if id_val == hero_id: return name
        return get_hero_display_name(hero_id)

    # ==================
    # TESTING (Used by UI)
    # ==================
    def start_test_load(self, party_size: int, mode: str):
        self.test_routine = self.load_team(party_size, mode)