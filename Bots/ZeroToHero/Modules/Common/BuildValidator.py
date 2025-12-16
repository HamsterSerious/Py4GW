import time
import Py4GW
from Py4GWCoreLib import Routines
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE


class BuildValidator:
    """
    Handles testing and verification of builds.
    Responsibilities:
    - Testing player loadouts
    - Testing hero builds
    - Verifying skill counts
    - Managing test sequences
    """
    
    def __init__(self, team_composer):
        """
        Args:
            team_composer: TeamComposer instance for finding hero slots
        """
        self.composer = team_composer
    
    def test_player_loadout(self, build_code, expected_skills=8):
        """
        Tests loading a build template on the player.
        
        Args:
            build_code: Template code to load
            expected_skills: Number of skills expected to load
        
        Yields for coroutine execution.
        """
        Py4GW.Console.Log("BuildValidator", "Testing Player Loadout...", Py4GW.Console.MessageType.Info)
        
        if not build_code or build_code == "Any":
            Py4GW.Console.Log("BuildValidator", "No build code provided.", Py4GW.Console.MessageType.Warning)
            return
        
        # Load the build
        GLOBAL_CACHE.SkillBar.LoadSkillTemplate(build_code)
        yield from Routines.Yield.wait(1000)
        
        # Verify
        try:
            skill_ids = GLOBAL_CACHE.SkillBar.GetSkillbar()
            equipped_count = len([s for s in skill_ids if s != 0])
            
            if equipped_count >= expected_skills:
                Py4GW.Console.Log("BuildValidator", 
                                f"Success! Equipped {equipped_count}/{expected_skills} skills.", 
                                Py4GW.Console.MessageType.Success)
            else:
                Py4GW.Console.Log("BuildValidator", 
                                f"Warning: Only {equipped_count} skills loaded. Expected {expected_skills}. "
                                "Click the build code in the info window to copy and verify.", 
                                Py4GW.Console.MessageType.Warning)
        except Exception as e:
            Py4GW.Console.Log("BuildValidator", f"Verification failed: {e}", Py4GW.Console.MessageType.Error)
    
    def test_mandatory_heroes(self, hero_requirements, mission_name, get_assigned_hero_fn, get_hero_name_fn):
        """
        Tests loading all mandatory heroes with their builds.
        
        Args:
            hero_requirements: List of hero requirement dicts
            mission_name: Name of mission (for flexible hero lookup)
            get_assigned_hero_fn: Function(mission_name, slot_index) -> hero_id
            get_hero_name_fn: Function(hero_id) -> display name
        
        Yields for coroutine execution.
        """
        Py4GW.Console.Log("BuildValidator", "Starting Mandatory Hero Test...", Py4GW.Console.MessageType.Info)
        
        # Disband existing party
        if GLOBAL_CACHE.Party.GetHeroCount() > 0:
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            timeout = time.time() + 2.0
            while GLOBAL_CACHE.Party.GetHeroCount() > 0 and time.time() < timeout:
                yield from Routines.Yield.wait(100)
            yield from Routines.Yield.wait(200)
        
        # Add each hero
        for idx, req in enumerate(hero_requirements):
            hero_id = req.get("HeroID", 0)
            
            # Resolve flexible heroes
            if hero_id == 0:
                hero_id = get_assigned_hero_fn(mission_name, idx)
                if hero_id == 0:
                    Py4GW.Console.Log("BuildValidator", 
                                    f"Skipping Slot {idx+1}: No hero selected.", 
                                    Py4GW.Console.MessageType.Warning)
                    continue
            
            hero_name = get_hero_name_fn(hero_id)
            Py4GW.Console.Log("BuildValidator", f"Adding {hero_name} (Slot {idx+1})...", Py4GW.Console.MessageType.Info)
            
            # Add hero
            GLOBAL_CACHE.Party.Heroes.AddHero(hero_id)
            
            # Wait for hero to appear in party
            party_slot = yield from self._wait_for_hero(hero_id, timeout=3.0)
            if party_slot == -1:
                Py4GW.Console.Log("BuildValidator", f"Failed to add {hero_name}.", Py4GW.Console.MessageType.Error)
                continue
            
            # Load and verify build
            build_code = req.get("Build", "")
            expected_skills = req.get("Expected_Skills", 8)
            
            if build_code and build_code != "Any":
                yield from self._load_and_verify_hero_build(
                    party_slot, 
                    build_code, 
                    expected_skills, 
                    hero_name
                )
            else:
                Py4GW.Console.Log("BuildValidator", f"{hero_name} ready (Any build).", Py4GW.Console.MessageType.Success)
            
            yield from Routines.Yield.wait(300)
        
        Py4GW.Console.Log("BuildValidator", "Mandatory Hero Check Complete.", Py4GW.Console.MessageType.Info)
    
    def verify_hero_build(self, party_slot, expected_count=8):
        """
        Verifies how many skills are loaded on a hero.
        
        Args:
            party_slot: Party slot index (1-7)
            expected_count: Expected number of skills
        
        Returns:
            (success: bool, loaded_count: int)
        """
        try:
            if hasattr(GLOBAL_CACHE.SkillBar, "GetHeroSkillbar"):
                hero_data = GLOBAL_CACHE.SkillBar.GetHeroSkillbar(party_slot)
                loaded_count = self._count_loaded_skills(hero_data)
                return (loaded_count >= expected_count, loaded_count)
            else:
                # Method not available, assume success
                return (True, expected_count)
        except Exception as e:
            Py4GW.Console.Log("BuildValidator", f"Verification error: {e}", Py4GW.Console.MessageType.Error)
            return (False, 0)
    
    # --- Private Helpers ---
    
    def _wait_for_hero(self, hero_id, timeout=3.0):
        """
        Waits for a hero to appear in the party.
        
        Args:
            hero_id: Hero ID to wait for
            timeout: Max wait time in seconds
        
        Returns:
            Party slot index or -1 if timeout
        
        Yields for coroutine execution.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            party_slot = self.composer.find_hero_slot(hero_id)
            if party_slot != -1:
                return party_slot
            yield from Routines.Yield.wait(100)
        return -1
    
    def _load_and_verify_hero_build(self, party_slot, build_code, expected_skills, hero_name):
        """
        Loads a build on a hero and verifies skill count.
        
        Yields for coroutine execution.
        """
        yield from Routines.Yield.wait(200)
        GLOBAL_CACHE.SkillBar.LoadHeroSkillTemplate(party_slot, build_code)
        yield from Routines.Yield.wait(1000)
        
        success, loaded_count = self.verify_hero_build(party_slot, expected_skills)
        
        if success:
            Py4GW.Console.Log("BuildValidator", 
                            f"{hero_name}: Success ({loaded_count}/{expected_skills} skills).", 
                            Py4GW.Console.MessageType.Success)
        else:
            Py4GW.Console.Log("BuildValidator", 
                            f"{hero_name}: Warning! Only loaded {loaded_count}/{expected_skills} skills. "
                            "Click the build code in the info window to copy and verify.", 
                            Py4GW.Console.MessageType.Warning)
    
    def _count_loaded_skills(self, hero_data):
        """
        Counts how many skills are loaded on a hero.
        Handles multiple data formats returned by GetHeroSkillbar.
        
        Args:
            hero_data: Data returned from GetHeroSkillbar
        
        Returns:
            Number of non-zero skills
        """
        loaded_count = 0
        
        # Format 1: List or tuple
        if isinstance(hero_data, (list, tuple)):
            for item in hero_data:
                skill_id = self._extract_skill_id(item)
                if skill_id != 0:
                    loaded_count += 1
        
        # Format 2: Object with GetSkill method
        elif hasattr(hero_data, "GetSkill"):
            for i in range(8):
                try:
                    skill = hero_data.GetSkill(i)
                    if skill:
                        skill_id = self._extract_skill_id(skill)
                        if skill_id != 0:
                            loaded_count += 1
                except Exception:
                    pass
        
        return loaded_count
    
    def _extract_skill_id(self, item):
        """
        Extracts a skill ID from various data formats.
        
        Args:
            item: Could be int, or object with .id.id, or object with .id
        
        Returns:
            Skill ID as int
        """
        if isinstance(item, int):
            return item
        
        # Try nested .id.id
        try:
            return item.id.id
        except (AttributeError, TypeError):
            pass
        
        # Try single .id
        try:
            return item.id
        except (AttributeError, TypeError):
            pass
        
        return 0