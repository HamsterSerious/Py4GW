"""
PartyUtils.py - Party validation utilities for ZeroToHero missions.

Provides:
- Hero presence checks
- Party size validation
- Hard mode status checks
"""

from Py4GWCoreLib import *

# Try importing GLOBAL_CACHE safely
try:
    from Py4GWCoreLib import GLOBAL_CACHE
except ImportError:
    try:
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
    except ImportError:
        GLOBAL_CACHE = None


class PartyValidator:
    """
    Validates party composition before starting a mission.
    """
    
    @staticmethod
    def CheckHeroInParty(hero_name):
        """
        Check if a specific hero is in the party.
        
        Args:
            hero_name (str): The name of the hero to check for (e.g., "Koss", "Melonni")
            
        Returns:
            bool: True if hero is in party, False otherwise
        """
        try:
            heroes = Party.GetHeroes()
            if not heroes:
                return False
            
            for hero in heroes:
                if hasattr(hero, 'hero_id'):
                    name = hero.hero_id.GetName()
                    if name.lower() == hero_name.lower():
                        return True
            return False
        except Exception:
            return False
    
    @staticmethod
    def CheckMultipleHeroes(hero_names):
        """
        Check if multiple heroes are in the party.
        
        Args:
            hero_names (list): List of hero names to check for
            
        Returns:
            tuple: (bool all_present, list missing_heroes)
        """
        missing = []
        for hero_name in hero_names:
            if not PartyValidator.CheckHeroInParty(hero_name):
                missing.append(hero_name)
        
        return (len(missing) == 0, missing)
    
    @staticmethod
    def GetPartySize():
        """
        Get the current party size.
        
        Returns:
            int: Number of party members (including player)
        """
        try:
            return Party.GetPartySize()
        except Exception:
            return 0
    
    @staticmethod
    def ValidatePartySize(min_size, max_size=8):
        """
        Check if party size is within acceptable range.
        
        Args:
            min_size (int): Minimum required party members
            max_size (int): Maximum allowed party members (default 8)
            
        Returns:
            tuple: (bool is_valid, int current_size, str error_message or None)
        """
        current_size = PartyValidator.GetPartySize()
        
        if current_size < min_size:
            return (False, current_size, f"Party too small! Need at least {min_size}, have {current_size}.")
        
        if current_size > max_size:
            return (False, current_size, f"Party too large! Max is {max_size}, have {current_size}.")
        
        return (True, current_size, None)
    
    @staticmethod
    def IsHardModeUnlocked():
        """
        Check if Hard Mode is unlocked for the current character/campaign.
        
        Returns:
            bool: True if HM is unlocked
        """
        if not GLOBAL_CACHE:
            return False
        
        try:
            return GLOBAL_CACHE.Party.IsHardModeUnlocked()
        except Exception:
            return False
    
    @staticmethod
    def IsInHardMode():
        """
        Check if currently in Hard Mode.
        
        Returns:
            bool: True if in HM
        """
        if not GLOBAL_CACHE:
            return False
        
        try:
            return GLOBAL_CACHE.Party.IsHardMode()
        except Exception:
            return False
    
    @staticmethod
    def SetHardMode(enabled, logger=None):
        """
        Attempt to set Hard Mode on or off.
        
        Args:
            enabled (bool): True to enable HM, False for Normal Mode
            logger: Optional logger for status messages
            
        Returns:
            bool: True if successful
        """
        if not GLOBAL_CACHE:
            if logger:
                logger.Add("GLOBAL_CACHE not available.", (1, 0, 0, 1), prefix="[Error]")
            return False
        
        if not Map.IsOutpost():
            if logger:
                logger.Add("Can only change mode in outpost.", (1, 0.5, 0, 1), prefix="[Warn]")
            return False
        
        try:
            if enabled:
                if not PartyValidator.IsHardModeUnlocked():
                    if logger:
                        logger.Add("Hard Mode not unlocked!", (1, 0, 0, 1), prefix="[Error]")
                    return False
                GLOBAL_CACHE.Party.SetHardMode()
                if logger:
                    logger.Add("Hard Mode enabled.", (0, 1, 0, 1), prefix="[System]")
            else:
                GLOBAL_CACHE.Party.SetNormalMode()
                if logger:
                    logger.Add("Normal Mode enabled.", (0, 1, 0, 1), prefix="[System]")
            return True
        except Exception as e:
            if logger:
                logger.Add(f"Mode change failed: {e}", (1, 0, 0, 1), prefix="[Error]")
            return False
    
    @staticmethod
    def GetHeroList():
        """
        Get list of all heroes currently in party.
        
        Returns:
            list: List of hero names
        """
        hero_names = []
        try:
            heroes = Party.GetHeroes()
            if heroes:
                for hero in heroes:
                    if hasattr(hero, 'hero_id'):
                        hero_names.append(hero.hero_id.GetName())
        except Exception:
            pass
        return hero_names


class PartyRequirements:
    """
    Data class to define party requirements for a mission.
    """
    def __init__(self, min_size=2, max_size=8, required_heroes=None):
        """
        Args:
            min_size (int): Minimum party members required
            max_size (int): Maximum party members allowed
            required_heroes (list): List of hero names that must be present
        """
        self.min_size = min_size
        self.max_size = max_size
        self.required_heroes = required_heroes or []
    
    def Validate(self, logger=None):
        """
        Validate all party requirements.
        
        Args:
            logger: Optional logger for error messages
            
        Returns:
            tuple: (bool is_valid, str error_message or None)
        """
        # Check party size
        size_valid, current_size, size_error = PartyValidator.ValidatePartySize(
            self.min_size, self.max_size
        )
        if not size_valid:
            if logger:
                logger.Add(size_error, (1, 0, 0, 1), prefix="[Error]")
            return (False, size_error)
        
        # Check required heroes
        if self.required_heroes:
            all_present, missing = PartyValidator.CheckMultipleHeroes(self.required_heroes)
            if not all_present:
                error_msg = f"Missing required hero(es): {', '.join(missing)}"
                if logger:
                    logger.Add(error_msg, (1, 0, 0, 1), prefix="[Error]")
                return (False, error_msg)
        
        return (True, None)
