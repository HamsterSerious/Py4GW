"""
Team Manager - Coordinator for team management operations.

Delegates responsibilities to specialized classes:
- TeamConfigManager: Configuration persistence
- TeamComposer: Hero recruitment and builds
- BuildValidator: Testing and verification 
- TeamWindow (in ui/): User interface
"""
import Py4GW
from Py4GWCoreLib import Routines

from data.heroes import get_hero_display_name, get_all_hero_options
from data.timing import Timing
from .config import TeamConfigManager
from .composer import TeamComposer
from .validator import BuildValidator


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
        
        # UI reference (set later when UI is created)
        self._ui = None
        
        # State
        self.is_party_ready = False
        self.test_routine = None  # Active test coroutine
        self._initialized = False
        
        # Hero options for UI (cached)
        self._hero_options = []
    
    # ==================
    # PROPERTIES
    # ==================
    
    @property
    def is_new_config(self) -> bool:
        """Gets whether this is a new configuration."""
        return self.config.is_new_config
    
    @property
    def show_window(self) -> bool:
        """Gets the window visibility state."""
        if self._ui:
            return self._ui.show_window
        return False
    
    @show_window.setter
    def show_window(self, value: bool):
        """Sets the window visibility state."""
        if self._ui:
            self._ui.show_window = value
    
    @property
    def hero_options(self) -> list:
        """Gets the list of hero options for UI."""
        return self._hero_options
    
    # ==================
    # PUBLIC API
    # ==================
    
    def initialize(self) -> bool:
        """
        Initializes the team manager.
        Should be called once after character is loaded.
        
        Returns:
            True if successful
        """
        if self._initialized:
            return True
        
        success = self.config.initialize()
        if success:
            self._refresh_hero_list()
            self._initialized = True
            
            # Create UI now that we have hero options
            from ui.team_window import TeamWindow
            self._ui = TeamWindow(
                bot=self.bot,
                config_manager=self.config,
                on_save_callback=self.save_config,
                on_test_load_callback=self.start_test_load,
                hero_options=self._hero_options
            )
            
            Py4GW.Console.Log(
                "TeamManager", 
                "Initialized.", 
                Py4GW.Console.MessageType.Info
            )
        
        return success
    
    def update(self):
        """
        Updates test routines.
        Call this every frame.
        """
        if self.test_routine:
            try:
                next(self.test_routine)
            except StopIteration:
                self.test_routine = None
                Py4GW.Console.Log(
                    "TeamManager", 
                    "Test Sequence Complete.", 
                    Py4GW.Console.MessageType.Success
                )
            except Exception as e:
                self.test_routine = None
                import traceback
                Py4GW.Console.Log(
                    "TeamManager", 
                    f"Test Sequence Crash: {e}", 
                    Py4GW.Console.MessageType.Error
                )
                Py4GW.Console.Log(
                    "TeamManager", 
                    traceback.format_exc(), 
                    Py4GW.Console.MessageType.Error
                )
    
    def draw_window(self):
        """Draws the team setup UI. Call this every frame."""
        if self._ui:
            self._ui.draw()
    
    # ==================
    # CONFIGURATION
    # ==================
    
    def has_valid_config(self) -> bool:
        """Returns True if configuration has been set up."""
        return self.config.has_valid_config()
    
    def save_config(self):
        """Saves configuration and refreshes UI."""
        if self.config.save():
            self._refresh_hero_list()
    
    # ==================
    # TEAM LOADING
    # ==================
    
    def load_team(self, party_size: int, mode: str = "NM"):
        """
        Loads a standard team from profile.
        
        Args:
            party_size: 4, 6, or 8
            mode: "NM" or "HM"
        
        Yields for coroutine execution.
        """
        self.is_party_ready = False
        
        profile = self.config.get_profile(party_size, mode)
        Py4GW.Console.Log(
            "TeamManager", 
            f"Loading Profile: [{party_size}_{mode}]", 
            Py4GW.Console.MessageType.Info
        )
        
        # Disband existing party
        self.composer.disband_party()
        yield from Routines.Yield.wait(Timing.PARTY_DISBAND_WAIT)
        
        # Recruit team
        yield from self.composer.load_team(
            party_size=party_size,
            heroes=profile["heroes"],
            get_hero_name_fn=self._get_hero_display_name
        )
        
        self.is_party_ready = True
        Py4GW.Console.Log(
            "TeamManager", 
            "Party Assembled.", 
            Py4GW.Console.MessageType.Success
        )
    
    def load_team_with_mandatory_heroes(self, party_size: int, mode: str,
                                        mandatory_list: list, mission_name: str = ""):
        """
        Loads team with mandatory hero requirements.
        
        Args:
            party_size: 4, 6, or 8
            mode: "NM" or "HM"
            mandatory_list: List of HeroRequirements
            mission_name: Name of mission (for flexible hero assignments)
        
        Yields for coroutine execution.
        """
        self.is_party_ready = False
        
        profile = self.config.get_profile(party_size, mode)
        Py4GW.Console.Log(
            "TeamManager", 
            f"Loading Profile: [{party_size}_{mode}] with {len(mandatory_list)} mandatory heroes.", 
            Py4GW.Console.MessageType.Info
        )
        
        # Disband existing party
        self.composer.disband_party()
        yield from Routines.Yield.wait(Timing.PARTY_DISBAND_WAIT)
        
        # Recruit team with mandatory heroes
        yield from self.composer.load_team_with_mandatory_heroes(
            party_size=party_size,
            profile_heroes=profile["heroes"],
            mandatory_list=mandatory_list,
            mission_name=mission_name,
            get_assigned_hero_fn=self.config.get_assigned_hero,
            get_hero_name_fn=self._get_hero_display_name
        )
        
        self.is_party_ready = True
        Py4GW.Console.Log(
            "TeamManager", 
            "Party Assembled.", 
            Py4GW.Console.MessageType.Success
        )
    
    def is_party_ready(self) -> bool:
        """Returns True if party is assembled."""
        return self.is_party_ready
    
    def disband_party(self):
        """Disbands the current party."""
        self.composer.disband_party()
        self.is_party_ready = False
    
    def load_build_to_hero(self, hero_id: int, build_code: str):
        """Loads a build onto a hero that's already in party."""
        self.composer.load_build_to_hero(hero_id, build_code)
    
    # ==================
    # MISSION HERO ASSIGNMENTS
    # ==================
    
    def GetAssignedHero(self, mission_name: str, slot_index: int, default_hero_id: int = 0) -> int:
        """Gets the hero assigned to a mission's flexible slot."""
        return self.config.get_assigned_hero(mission_name, slot_index, default_hero_id)
    
    def SetAssignedHero(self, mission_name: str, slot_index: int, hero_id: int):
        """Assigns a hero to a mission's flexible slot."""
        if self.config.set_assigned_hero(mission_name, slot_index, hero_id):
            self.config.save()
    
    # ==================
    # TESTING
    # ==================
    
    def start_test_load(self, party_size: int, mode: str):
        """Starts a test load routine."""
        Py4GW.Console.Log(
            "TeamManager", 
            f"Test Load Initiated for [{party_size}_{mode}]", 
            Py4GW.Console.MessageType.Info
        )
        self.test_routine = self.load_team(party_size, mode)
    
    def TestPlayerLoadout(self, build_code: str, expected_skills: int = 8):
        """
        Returns a coroutine for testing player build.
        Use by setting: self.test_routine = manager.TestPlayerLoadout(...)
        """
        return self.validator.test_player_loadout(build_code, expected_skills)
    
    def TestMandatoryHeroes(self, hero_requirements: list, mission_name: str):
        """
        Returns a coroutine for testing mandatory heroes.
        Use by setting: self.test_routine = manager.TestMandatoryHeroes(...)
        """
        return self.validator.test_mandatory_heroes(
            hero_requirements=hero_requirements,
            mission_name=mission_name,
            get_assigned_hero_fn=self.config.get_assigned_hero,
            get_hero_name_fn=self._get_hero_display_name
        )
    
    # ==================
    # PRIVATE HELPERS
    # ==================
    
    def _refresh_hero_list(self):
        """
        Rebuilds the hero options list with custom names.
        """
        base_options = get_all_hero_options()
        
        # Apply custom names
        self._hero_options = []
        for hero_id, base_name in base_options:
            custom_name = self.config.get_custom_hero_name(hero_id)
            if custom_name:
                display_name = f"{custom_name} ({base_name})"
            else:
                display_name = base_name
            self._hero_options.append((hero_id, display_name))
        
        # Sort alphabetically
        self._hero_options.sort(key=lambda x: x[1])
    
    def _get_hero_display_name(self, hero_id: int) -> str:
        """Gets the display name for a hero ID."""
        if hero_id == 0:
            return "None"
        
        for id_val, name in self._hero_options:
            if id_val == hero_id:
                return name
        
        return get_hero_display_name(hero_id)
    
    # ==================
    # LEGACY ALIASES
    # ==================
    
    def Initialize(self) -> bool:
        """Legacy method name."""
        return self.initialize()
    
    def Update(self):
        """Legacy method name."""
        self.update()
    
    def DrawWindow(self):
        """Legacy method name."""
        self.draw_window()
    
    def HasValidConfig(self) -> bool:
        """Legacy method name."""
        return self.has_valid_config()
    
    def LoadTeam(self, party_size: int, mode: str = "NM"):
        """Legacy method name."""
        yield from self.load_team(party_size, mode)
    
    def LoadTeamWithMandatoryHeroes(self, party_size: int, mode: str,
                                    mandatory_list: list, mission_name: str = ""):
        """Legacy method name."""
        yield from self.load_team_with_mandatory_heroes(party_size, mode, mandatory_list, mission_name)
    
    def DisbandParty(self):
        """Legacy method name."""
        self.disband_party()
    
    def LoadBuildToHero(self, hero_id: int, build_code: str):
        """Legacy method name."""
        self.load_build_to_hero(hero_id, build_code)
