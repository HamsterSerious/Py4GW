"""
Team Composer - Handles actual game actions for assembling teams.

Responsibilities:
- Recruiting heroes
- Applying skill templates
- Disbanding party
- Finding hero slots
"""
import Py4GW
from Py4GWCoreLib import Routines
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from data.timing import Timing


class TeamComposer:
    """
    Handles the actual game actions for assembling teams.
    """
    
    def __init__(self):
        pass
    
    def disband_party(self):
        """Kicks all heroes from the party."""
        if GLOBAL_CACHE.Party.GetHeroCount() > 0:
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            Py4GW.Console.Log(
                "TeamComposer", 
                "Party disbanded.", 
                Py4GW.Console.MessageType.Info
            )
    
    def load_team(self, party_size: int, heroes: list, get_hero_name_fn=None):
        """
        Recruits heroes and applies builds.
        
        Args:
            party_size: Total party size (4, 6, or 8)
            heroes: List of {"hero_id": int, "build": str} dicts
            get_hero_name_fn: Optional function(hero_id) -> name for logging
        
        Yields for coroutine execution.
        """
        slots_needed = party_size - 1  # Exclude player
        party_slot_index = 1  # First hero slot
        
        for i in range(min(slots_needed, len(heroes))):
            hero = heroes[i]
            hero_id = hero.get("hero_id", 0)
            build_code = hero.get("build", "")
            
            if hero_id > 0:
                hero_name = get_hero_name_fn(hero_id) if get_hero_name_fn else f"Hero {hero_id}"
                
                Py4GW.Console.Log(
                    "TeamComposer", 
                    f"Slot {i + 1}: Adding {hero_name}", 
                    Py4GW.Console.MessageType.Info
                )
                
                # Recruit hero
                GLOBAL_CACHE.Party.Heroes.AddHero(hero_id)
                yield from Routines.Yield.wait(Timing.HERO_ADD_DELAY)
                
                # Apply build if specified
                if build_code and build_code != "Any":
                    yield from self._apply_build(party_slot_index, build_code, hero_name)
                
                party_slot_index += 1
    
    def load_team_with_mandatory_heroes(self, party_size: int, profile_heroes: list, 
                                        mandatory_list: list, mission_name: str,
                                        get_assigned_hero_fn, get_hero_name_fn=None):
        """
        Loads team with mandatory hero requirements overlaying the profile.
        
        Args:
            party_size: Total party size
            profile_heroes: List of hero dicts from profile
            mandatory_list: List of HeroRequirements from mission
            mission_name: Name of mission (for flexible hero lookup)
            get_assigned_hero_fn: Function(mission_name, slot_index) -> hero_id
            get_hero_name_fn: Optional function for hero names
        
        Yields for coroutine execution.
        """
        # Merge mandatory requirements into profile
        final_heroes = self._merge_mandatory_heroes(
            profile_heroes,
            mandatory_list,
            mission_name,
            get_assigned_hero_fn
        )
        
        # Log mandatory slots
        for i, req in enumerate(mandatory_list):
            hero_id = final_heroes[i]["hero_id"] if i < len(final_heroes) else 0
            hero_name = get_hero_name_fn(hero_id) if (get_hero_name_fn and hero_id > 0) else f"Hero {hero_id}"
            Py4GW.Console.Log(
                "TeamComposer", 
                f"Mandatory Slot {i+1}: {hero_name}", 
                Py4GW.Console.MessageType.Info
            )
        
        # Recruit the team
        yield from self.load_team(party_size, final_heroes, get_hero_name_fn)
    
    def load_build_to_hero(self, hero_id: int, build_code: str):
        """
        Loads a build onto a hero that's already in the party.
        Non-coroutine version for immediate use.
        """
        if not build_code or build_code == "Any":
            return
        
        party_slot = self.find_hero_slot(hero_id)
        if party_slot == -1:
            return
        
        try:
            GLOBAL_CACHE.SkillBar.LoadHeroSkillTemplate(party_slot, build_code)
        except Exception as e:
            Py4GW.Console.Log(
                "TeamComposer", 
                f"Failed to load build: {e}", 
                Py4GW.Console.MessageType.Warning
            )
    
    def find_hero_slot(self, hero_id: int) -> int:
        """
        Finds which party slot a hero occupies.
        
        Args:
            hero_id: The HeroType ID to find
        
        Returns:
            Party slot index (1-7) or -1 if not found
        """
        try:
            heroes = GLOBAL_CACHE.Party.GetHeroes()
            for i, hero in enumerate(heroes):
                if hero.hero_id.GetID() == hero_id:
                    return i + 1  # Party slots are 1-indexed
        except Exception:
            pass
        return -1
    
    # ==================
    # PRIVATE HELPERS
    # ==================
    
    def _apply_build(self, party_slot: int, build_code: str, hero_name: str = "Hero"):
        """Applies a build template to a hero slot."""
        if not build_code or build_code == "Any":
            return
        
        try:
            GLOBAL_CACHE.SkillBar.LoadHeroSkillTemplate(party_slot, build_code)
            yield from Routines.Yield.wait(Timing.BUILD_APPLY_DELAY)
            Py4GW.Console.Log(
                "TeamComposer", 
                f"Applied build to {hero_name}.", 
                Py4GW.Console.MessageType.Info
            )
        except Exception as e:
            Py4GW.Console.Log(
                "TeamComposer", 
                f"Failed to apply build to {hero_name}: {e}", 
                Py4GW.Console.MessageType.Warning
            )
    
    def _merge_mandatory_heroes(self, profile_heroes: list, mandatory_list: list,
                                mission_name: str, get_assigned_hero_fn) -> list:
        """
        Merges mandatory requirements into profile heroes.
        
        Args:
            profile_heroes: List of hero dicts from profile
            mandatory_list: List of HeroRequirements
            mission_name: Name of mission
            get_assigned_hero_fn: Function to get assigned hero for flexible slots
        
        Returns:
            List of hero dicts with mandatory heroes merged
        """
        if not mandatory_list:
            return profile_heroes
        
        # Start with copy of profile
        result = [dict(h) for h in profile_heroes]
        
        # Overwrite first N slots with mandatory requirements
        for i, req in enumerate(mandatory_list):
            if i >= len(result):
                break
            
            # Handle HeroRequirements dataclass
            hero_id = req.hero_id
            build_code = req.build
            
            # Resolve flexible heroes (hero_id = 0)
            if hero_id == 0:
                hero_id = get_assigned_hero_fn(mission_name, i)
                if hero_id == 0:
                    Py4GW.Console.Log(
                        "TeamComposer", 
                        f"Warning: No hero assigned for mandatory slot {i+1}!", 
                        Py4GW.Console.MessageType.Warning
                    )
            
            # Update slot
            result[i] = {
                "hero_id": hero_id,
                "build": "" if build_code == "Any" else build_code
            }
        
        return result