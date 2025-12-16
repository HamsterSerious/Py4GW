"""
Loadout-related data structures.
Defines hero requirements, player builds, and mandatory loadout configurations.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from data.enums import GameMode


@dataclass
class HeroRequirement:
    """
    A single hero requirement for a mission slot.
    
    Attributes:
        hero_id: HeroType ID. 0 = flexible slot (user picks hero matching role)
        role: Role description for flexible slots (e.g., "Healer", "Necro")
        build: Template code. Empty or "Any" = no specific build required
        expected_skills: Number of skills expected to load (for validation)
        equipment: Description of required runes/insignias
        weapons: Description of required weapons
    """
    hero_id: int = 0
    role: str = ""
    build: str = ""
    expected_skills: int = 8
    equipment: str = ""
    weapons: str = ""
    
    def is_flexible(self) -> bool:
        """Returns True if this is a flexible slot (user picks hero)."""
        return self.hero_id == 0
    
    def has_build_requirement(self) -> bool:
        """Returns True if a specific build is required."""
        return bool(self.build) and self.build != "Any"


@dataclass
class PlayerBuildRequirement:
    """
    Player build requirements, with per-profession builds.
    
    Attributes:
        builds: Dict mapping profession name to template code
                e.g., {"Warrior": "OQ...", "Mesmer": "OQ...", "Any": "OA..."}
        expected_skills: Number of skills expected to load
        equipment: Description of required runes/insignias  
        weapons: Dict mapping set name to description
                 e.g., {"Set 1": "40/40 Fire Staff", "Set 2": "Shield Set"}
    """
    builds: Dict[str, str] = field(default_factory=dict)
    expected_skills: int = 8
    equipment: str = ""
    weapons: Dict[str, str] = field(default_factory=dict)
    
    def get_build_for_profession(self, profession: str) -> Optional[str]:
        """
        Get the build code for a specific profession.
        Falls back to "Any" if profession-specific build not found.
        
        Args:
            profession: Profession name (e.g., "Warrior", "Mesmer")
            
        Returns:
            Build template code or None if no matching build
        """
        if profession in self.builds:
            return self.builds[profession]
        return self.builds.get("Any")
    
    def has_requirements(self) -> bool:
        """Returns True if any build requirements are defined."""
        return bool(self.builds) or bool(self.equipment) or bool(self.weapons)


@dataclass
class MandatoryLoadout:
    """
    Complete mandatory loadout for a specific game mode (NM or HM).
    
    Attributes:
        player_build: Player build requirements (optional)
        required_heroes: List of hero requirements for party slots
        notes: General notes/warnings for this loadout
    """
    player_build: Optional[PlayerBuildRequirement] = None
    required_heroes: List[HeroRequirement] = field(default_factory=list)
    notes: str = ""
    
    def has_requirements(self) -> bool:
        """Returns True if this loadout has any actual requirements."""
        return bool(
            (self.player_build and self.player_build.has_requirements()) or
            self.required_heroes or
            self.notes
        )
    
    def get_hero_count(self) -> int:
        """Returns the number of required hero slots."""
        return len(self.required_heroes)


@dataclass
class LoadoutConfig:
    """
    Container for Normal Mode and Hard Mode loadout requirements.
    
    Attributes:
        normal_mode: Loadout requirements for Normal Mode (optional)
        hard_mode: Loadout requirements for Hard Mode (optional)
    """
    normal_mode: Optional[MandatoryLoadout] = None
    hard_mode: Optional[MandatoryLoadout] = None
    
    def get_for_mode(self, mode: GameMode) -> Optional[MandatoryLoadout]:
        """
        Get loadout requirements for the specified game mode.
        
        Args:
            mode: GameMode.NORMAL or GameMode.HARD
            
        Returns:
            MandatoryLoadout for that mode, or None if not defined
        """
        if mode == GameMode.HARD:
            return self.hard_mode
        return self.normal_mode
    
    def get_for_mode_string(self, mode_str: str) -> Optional[MandatoryLoadout]:
        """
        Get loadout requirements using mode string ("NM" or "HM").
        
        Args:
            mode_str: "NM" or "HM"
            
        Returns:
            MandatoryLoadout for that mode, or None if not defined
        """
        if mode_str == "HM":
            return self.hard_mode
        return self.normal_mode
    
    def has_any_requirements(self) -> bool:
        """Returns True if either mode has requirements."""
        nm_has = self.normal_mode and self.normal_mode.has_requirements()
        hm_has = self.hard_mode and self.hard_mode.has_requirements()
        return nm_has or hm_has