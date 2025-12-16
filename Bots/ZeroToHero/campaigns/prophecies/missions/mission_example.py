"""
Example Mission - Template for creating new missions.

Copy this file and modify for your own missions.
"""
from Py4GWCoreLib.enums_src.Hero_enums import HeroType

from core.base_task import BaseTask
from data.enums import TaskType, GameMode
from models.task import TaskInfo
from models.loadout import (
    LoadoutConfig,
    MandatoryLoadout,
    PlayerBuildRequirement,
    HeroRequirement
)


class Mission_Example(BaseTask):
    """
    Example mission demonstrating the new TaskInfo pattern.
    
    This serves as a template for creating new missions.
    """
    
    # Task metadata - define at class level
    INFO = TaskInfo(
        name="Example Mission (Ascalon)",
        description="This is an example mission template showing how to define "
                    "task metadata using the new dataclass pattern.",
        task_type=TaskType.MISSION,
        start_map_id=148,  # Example: Ascalon City
        
        # Optional: recommended builds for general use
        recommended_builds=["Warrior", "Elementalist", "Any caster"],
        
        # Optional: hard mode tips
        hm_tips="In Hard Mode, enemies hit harder and have more health. "
                "Consider bringing additional healing.",
        
        # Optional: mandatory loadout requirements
        loadout=LoadoutConfig(
            # Normal mode requirements (or None if no special requirements)
            normal_mode=None,
            
            # Hard mode requirements
            hard_mode=MandatoryLoadout(
                # Player build requirements
                player_build=PlayerBuildRequirement(
                    # Build codes by profession (use "Any" key for universal builds)
                    builds={
                        "Warrior": "OQcAQ8hTIxsDAAAAAAAAAA",  # Example build code
                        "Any": "OAhAAAAAAAAAAAAAAAAAAA"       # Fallback for other professions
                    },
                    expected_skills=8,
                    equipment="Sentinel's Insignia recommended",
                    weapons={
                        "Set 1": "Sword/Shield with +armor",
                        "Set 2": "Longbow for pulling"
                    }
                ),
                
                # Required heroes
                required_heroes=[
                    # Fixed hero requirement (specific hero required)
                    HeroRequirement(
                        hero_id=HeroType.Koss.value,
                        build="OQcAQ8hTIxsDAAAAAAAAAA",
                        expected_skills=8,
                        equipment="Survivor Insignia",
                        weapons="Hammer"
                    ),
                    
                    # Flexible hero requirement (user picks hero matching role)
                    HeroRequirement(
                        hero_id=0,  # 0 = flexible, user selects
                        role="Healer",
                        build="OAhAAAAAAAAAAAAAAAAAAA",
                        expected_skills=8
                    ),
                    
                    # Another flexible slot
                    HeroRequirement(
                        hero_id=0,
                        role="Protection Monk",
                        build="OAhAAAAAAAAAAAAAAAAAAA"
                    )
                ],
                
                # General notes for the player
                notes="Do NOT bring Minion Masters - corpses are needed for quest objectives."
            )
        )
    )
    
    # Mission-specific data
    WAYPOINTS = [
        (1000, 2000),
        (1500, 2500),
        (2000, 3000)
    ]
    
    MISSION_NPC_ID = 12345  # Example NPC ID
    
    def PreRunCheck(self, bot) -> tuple:
        """
        Verify preconditions before starting the mission.
        """
        # Example: Check if player has required quest
        # if not has_quest(self.INFO.requires_quest_id):
        #     return (False, "Required quest not active")
        
        return (True, "")
    
    def execute(self, bot):
        """
        Main mission execution logic.
        
        Args:
            bot: The bot instance with access to all systems
        """
        # 1. Travel to mission outpost
        yield from bot.transition.TravelTo(self.INFO.start_map_id)
        
        # 2. Setup team and enter mission
        yield from bot.transition.SetupMission(bot, self.use_hard_mode)
        
        # 3. Talk to NPC to enter mission (if applicable)
        # yield from bot.transition.MoveToAndInteract(bot, self.MISSION_NPC_ID)
        # yield from bot.transition.EnterMission(bot)
        
        # 4. Execute mission waypoints
        for x, y in self.WAYPOINTS:
            yield from bot.movement.MoveTo(x, y)
            
            # Optional: Combat handling
            # if bot.combat.InCombat():
            #     yield from bot.combat.Fight()
        
        # 5. Mark as complete
        self.finished = True


# ==================
# MINIMAL EXAMPLE
# ==================

class Mission_Minimal(BaseTask):
    """
    Minimal mission example - just the essentials.
    """
    
    INFO = TaskInfo(
        name="Minimal Example",
        description="A bare-bones mission template.",
        task_type=TaskType.MISSION,
        start_map_id=148
    )
    
    def execute(self, bot):
        yield from bot.transition.TravelTo(self.INFO.start_map_id)
        yield from bot.transition.SetupMission(bot, self.use_hard_mode)
        # ... mission logic here
        self.finished = True


# ==================
# QUEST EXAMPLE
# ==================

class Quest_Example(BaseTask):
    """
    Example quest - quests don't have HM/NM modes.
    """
    
    INFO = TaskInfo(
        name="Example Quest",
        description="Template for creating quests.",
        task_type=TaskType.QUEST,
        start_map_id=148,
        requires_quest_id=100  # Quest ID that must be active
    )
    
    QUEST_GIVER_ID = 54321
    
    def execute(self, bot):
        yield from bot.transition.TravelTo(self.INFO.start_map_id)
        yield from bot.movement.MoveTo(1000, 2000)
        # ... quest logic
        self.finished = True