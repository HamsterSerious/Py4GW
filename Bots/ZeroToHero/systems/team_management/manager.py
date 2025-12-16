import Py4GW
from Py4GWCoreLib import Routines
from .config import TeamConfigManager
from .composer import TeamComposer
from .validator import BuildValidator
from .ui import TeamManagerUI


class TeamManager:
    """
    Coordinator for team management operations.
    Delegates responsibilities to specialized classes:
    - TeamConfigManager: Configuration persistence
    - TeamComposer: Hero recruitment and builds
    - BuildValidator: Testing and verification 
    - TeamManagerUI: User interface
    """
    
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize components
        self.config = TeamConfigManager()
        self.composer = TeamComposer()
        self.validator = BuildValidator(self.composer)
        self.ui = TeamManagerUI(
            config_manager=self.config,
            on_save_callback=self.save_config,
            on_test_load_callback=self.start_test_load
        )
        
        # State
        self.is_party_ready = False
        self.test_routine = None  # Active test coroutine
        self.initialized = False
    
    # --- Public API ---
    
    def Initialize(self):
        """
        Initializes the team manager.
        Should be called once after character is loaded.
        Returns True if successful.
        """
        if self.initialized:
            return True
        
        success = self.config.initialize()
        if success:
            self.ui.refresh_hero_list()
            self.initialized = True
            Py4GW.Console.Log("TeamManager", "Initialized.", Py4GW.Console.MessageType.Info)
        
        return success
    
    def Update(self):
        """
        Updates test routines.
        Call this every frame.
        """
        if self.test_routine:
            try:
                next(self.test_routine)
            except StopIteration:
                self.test_routine = None
                Py4GW.Console.Log("TeamManager", "Test Sequence Complete.", Py4GW.Console.MessageType.Success)
            except Exception as e:
                self.test_routine = None
                import traceback
                Py4GW.Console.Log("TeamManager", f"Test Sequence Crash: {e}", Py4GW.Console.MessageType.Error)
                Py4GW.Console.Log("TeamManager", traceback.format_exc(), Py4GW.Console.MessageType.Error)
    
    def DrawWindow(self):
        """Draws the team setup UI. Call this every frame."""
        self.ui.draw()
    
    # --- Configuration ---
    
    def HasValidConfig(self):
        """Returns True if configuration has been set up."""
        return self.config.has_valid_config()
    
    @property
    def is_new_config(self):
        """Gets whether this is a new configuration."""
        return self.config.is_new_config
    
    def save_config(self):
        """Saves configuration and refreshes UI."""
        if self.config.save():
            self.ui.refresh_hero_list()
    
    # --- Team Loading ---
    
    def LoadTeam(self, party_size, mode="NM"):
        """
        Loads a standard team from profile.
        
        Args:
            party_size: 4, 6, or 8
            mode: "NM" or "HM"
        
        Yields for coroutine execution.
        """
        self.is_party_ready = False
        
        profile = self.config.get_profile(party_size, mode)
        Py4GW.Console.Log("TeamManager", f"Loading Profile: [{party_size}_{mode}]", Py4GW.Console.MessageType.Info)
        
        # Disband existing party
        self.composer.disband_party()
        yield from Routines.Yield.wait(500)
        
        # Recruit team
        yield from self.composer.load_team(
            party_size=party_size,
            heroes=profile["heroes"],
            get_hero_name_fn=self.ui.get_hero_display_name
        )
        
        self.is_party_ready = True
        Py4GW.Console.Log("TeamManager", "Party Assembled.", Py4GW.Console.MessageType.Success)
    
    def LoadTeamWithMandatoryHeroes(self, party_size, mode, mandatory_list, mission_name=""):
        """
        Loads team with mandatory hero requirements.
        
        Args:
            party_size: 4, 6, or 8
            mode: "NM" or "HM"
            mandatory_list: List of hero requirement dicts
            mission_name: Name of mission (for flexible hero assignments)
        
        Yields for coroutine execution.
        """
        self.is_party_ready = False
        
        profile = self.config.get_profile(party_size, mode)
        Py4GW.Console.Log("TeamManager", 
                         f"Loading Profile: [{party_size}_{mode}] with {len(mandatory_list)} mandatory heroes.", 
                         Py4GW.Console.MessageType.Info)
        
        # Disband existing party
        self.composer.disband_party()
        yield from Routines.Yield.wait(500)
        
        # Recruit team with mandatory heroes
        yield from self.composer.load_team_with_mandatory_heroes(
            party_size=party_size,
            profile_heroes=profile["heroes"],
            mandatory_list=mandatory_list,
            mission_name=mission_name,
            get_assigned_hero_fn=self.config.get_assigned_hero,
            get_hero_name_fn=self.ui.get_hero_display_name
        )
        
        self.is_party_ready = True
        Py4GW.Console.Log("TeamManager", "Party Assembled.", Py4GW.Console.MessageType.Success)
    
    def IsPartyReady(self):
        """Returns True if party is assembled."""
        return self.is_party_ready
    
    def DisbandParty(self):
        """Disbands the current party."""
        self.composer.disband_party()
        self.is_party_ready = False
    
    def LoadBuildToHero(self, hero_id, build_code):
        """Loads a build onto a hero that's already in party."""
        self.composer.load_build_to_hero(hero_id, build_code)
    
    # --- Mission Hero Assignments ---
    
    def GetAssignedHero(self, mission_name, slot_index, default_hero_id=0):
        """Gets the hero assigned to a mission's flexible slot."""
        return self.config.get_assigned_hero(mission_name, slot_index, default_hero_id)
    
    def SetAssignedHero(self, mission_name, slot_index, hero_id):
        """Assigns a hero to a mission's flexible slot."""
        if self.config.set_assigned_hero(mission_name, slot_index, hero_id):
            self.config.save()
    
    # --- Testing ---
    
    def start_test_load(self, party_size, mode):
        """Starts a test load routine."""
        Py4GW.Console.Log("TeamManager", f"Test Load Initiated for [{party_size}_{mode}]", Py4GW.Console.MessageType.Info)
        self.test_routine = self.LoadTeam(party_size, mode)
    
    def TestPlayerLoadout(self, build_code, expected_skills=8):
        """
        Returns a coroutine for testing player build.
        Use by setting: self.test_routine = manager.TestPlayerLoadout(...)
        """
        return self.validator.test_player_loadout(build_code, expected_skills)
    
    def TestMandatoryHeroes(self, hero_requirements, mission_name):
        """
        Returns a coroutine for testing mandatory heroes.
        Use by setting: self.test_routine = manager.TestMandatoryHeroes(...)
        """
        return self.validator.test_mandatory_heroes(
            hero_requirements=hero_requirements,
            mission_name=mission_name,
            get_assigned_hero_fn=self.config.get_assigned_hero,
            get_hero_name_fn=self.ui.get_hero_display_name
        )
    
    # --- UI Control ---
    
    @property
    def show_window(self):
        """Gets the window visibility state."""
        return self.ui.show_window
    
    @show_window.setter
    def show_window(self, value):
        """Sets the window visibility state."""
        self.ui.show_window = value
    
    @property
    def hero_options(self):
        """Gets the list of hero options for UI."""
        return self.ui.hero_options