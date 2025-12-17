"""
Unified requirement access for Zero To Hero bot.

Provides normalized access to task requirements, eliminating the need
for isinstance(dict) checks throughout the codebase.
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from data.enums import GameMode


@dataclass
class PlayerRequirements:
    """Normalized player build requirements."""
    builds: Dict[str, str]          # profession -> build code
    expected_skills: int
    equipment: str
    weapons: Dict[str, str]         # slot -> description
    
    @classmethod
    def from_loadout(cls, player_build) -> Optional['PlayerRequirements']:
        """
        Create from PlayerBuildRequirement dataclass.
        
        Args:
            player_build: PlayerBuildRequirement or None
            
        Returns:
            PlayerRequirements or None
        """
        if player_build is None:
            return None
        
        return cls(
            builds=player_build.builds or {},
            expected_skills=player_build.expected_skills,
            equipment=player_build.equipment or "",
            weapons=player_build.weapons or {}
        )
    
    def get_build_for_profession(self, profession: str) -> Optional[str]:
        """Get build code for a profession, falling back to 'Any'."""
        if profession in self.builds:
            return self.builds[profession]
        return self.builds.get("Any")
    
    def has_requirements(self) -> bool:
        """Check if any requirements are defined."""
        return bool(self.builds or self.equipment or self.weapons)


@dataclass
class HeroRequirements:
    """Normalized single hero requirement."""
    hero_id: int
    role: str
    build: str
    expected_skills: int
    equipment: str
    weapons: str
    
    @classmethod
    def from_hero_requirement(cls, req) -> 'HeroRequirements':
        """
        Create from HeroRequirement dataclass.
        
        Args:
            req: HeroRequirement dataclass
            
        Returns:
            HeroRequirements instance
        """
        return cls(
            hero_id=req.hero_id,
            role=req.role or "",
            build=req.build or "",
            expected_skills=req.expected_skills,
            equipment=req.equipment or "",
            weapons=req.weapons or ""
        )
    
    @property
    def is_flexible(self) -> bool:
        """True if this is a flexible slot (user picks hero)."""
        return self.hero_id == 0
    
    @property
    def has_build(self) -> bool:
        """True if a specific build is required."""
        return bool(self.build) and self.build != "Any"


@dataclass
class LoadoutRequirements:
    """Normalized complete loadout requirements for a mode."""
    player: Optional[PlayerRequirements]
    heroes: List[HeroRequirements]
    notes: str
    
    @classmethod
    def from_mandatory_loadout(cls, loadout) -> Optional['LoadoutRequirements']:
        """
        Create from MandatoryLoadout dataclass.
        
        Args:
            loadout: MandatoryLoadout or None
            
        Returns:
            LoadoutRequirements or None
        """
        if loadout is None:
            return None
        
        player = PlayerRequirements.from_loadout(loadout.player_build)
        
        heroes = [
            HeroRequirements.from_hero_requirement(h)
            for h in (loadout.required_heroes or [])
        ]
        
        return cls(
            player=player,
            heroes=heroes,
            notes=loadout.notes or ""
        )
    
    def has_requirements(self) -> bool:
        """Check if any requirements exist."""
        player_has = self.player and self.player.has_requirements()
        return bool(player_has or self.heroes or self.notes)
    
    @property
    def hero_count(self) -> int:
        """Number of required heroes."""
        return len(self.heroes)


class TaskRequirementsAccessor:
    """
    Provides unified access to task requirements.
    
    This is the single point of access for task loadout requirements,
    eliminating scattered isinstance() checks.
    
    Usage:
        accessor = TaskRequirementsAccessor(task_info)
        reqs = accessor.get_for_mode(GameMode.HARD)
        if reqs and reqs.has_requirements():
            # process requirements
    """
    
    def __init__(self, task_info):
        """
        Args:
            task_info: TaskInfo dataclass
        """
        self.task_info = task_info
    
    def get_for_mode(self, mode: GameMode) -> Optional[LoadoutRequirements]:
        """
        Get normalized requirements for a game mode.
        
        Args:
            mode: GameMode.NORMAL or GameMode.HARD
            
        Returns:
            LoadoutRequirements or None
        """
        if not self.task_info.loadout:
            return None
        
        loadout = self.task_info.loadout.get_for_mode(mode)
        return LoadoutRequirements.from_mandatory_loadout(loadout)
    
    def get_for_mode_string(self, mode_str: str) -> Optional[LoadoutRequirements]:
        """
        Get normalized requirements using mode string.
        
        Args:
            mode_str: "NM" or "HM"
            
        Returns:
            LoadoutRequirements or None
        """
        mode = GameMode.HARD if mode_str == "HM" else GameMode.NORMAL
        return self.get_for_mode(mode)
    
    def has_any_requirements(self) -> bool:
        """Check if task has any loadout requirements."""
        if not self.task_info.loadout:
            return False
        return self.task_info.loadout.has_any_requirements()
    
    def get_hero_requirements_for_mode(self, mode: GameMode) -> List[HeroRequirements]:
        """
        Get just the hero requirements for a mode.
        
        Convenience method for team loading.
        
        Args:
            mode: GameMode.NORMAL or GameMode.HARD
            
        Returns:
            List of HeroRequirements (empty if none)
        """
        reqs = self.get_for_mode(mode)
        if reqs:
            return reqs.heroes
        return []
