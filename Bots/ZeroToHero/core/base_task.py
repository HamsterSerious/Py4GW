"""
Base Task - Abstract base class for all missions, quests, and tasks.

Provides:
- Task metadata via INFO class attribute
- Execution lifecycle (started, finished, failed)
- Pre-run checks
- Backward compatibility with legacy GetInfo() method
"""
from data.enums import TaskType, GameMode
from models.task import TaskInfo


class BaseTask:
    """
    Base class for all executable tasks (missions, quests, etc).
    
    Subclasses should:
    1. Override INFO with a TaskInfo instance
    2. Implement execute(bot) generator method
    3. Optionally override PreRunCheck(bot)
    
    Example:
        class MyMission(BaseTask):
            INFO = TaskInfo(
                name="My Mission",
                description="Does something cool",
                task_type=TaskType.MISSION,
                start_map_id=123
            )
            
            def execute(self, bot):
                yield from bot.transition.TravelTo(123)
                # ... mission logic
                self.finished = True
    """
    
    # Class-level task info - override in subclasses
    INFO: TaskInfo = TaskInfo(
        name="Unnamed Task",
        description="No description provided.",
        task_type=TaskType.TASK
    )
    
    def __init__(self):
        # Execution state
        self.started = False
        self.finished = False
        self.failed = False
        
        # Mode configuration (set by QueuedTask.create_instance)
        self.use_hard_mode = False
    
    # ==================
    # PROPERTIES
    # ==================
    
    @property
    def name(self) -> str:
        """Task display name."""
        return self.INFO.name
    
    @property
    def task_type(self) -> TaskType:
        """Task type enum."""
        return self.INFO.task_type
    
    @property
    def game_mode(self) -> GameMode:
        """Current game mode based on use_hard_mode flag."""
        return GameMode.from_bool(self.use_hard_mode)
    
    @property
    def mode_string(self) -> str:
        """Mode as string ('NM' or 'HM')."""
        return self.game_mode.value
    
    # ==================
    # CLASS METHODS
    # ==================
    
    @classmethod
    def get_info(cls) -> TaskInfo:
        """
        Returns the TaskInfo for this task class.
        Preferred method for accessing task metadata.
        """
        return cls.INFO
    
    # ==================
    # INSTANCE METHODS
    # ==================
    
    def PreRunCheck(self, bot) -> tuple:
        """
        Called before task execution starts.
        Override to add custom pre-run validation.
        
        Args:
            bot: The bot instance
            
        Returns:
            (ready: bool, reason: str) - If not ready, reason explains why
        """
        return (True, "")
    
    def execute(self, bot):
        """
        Main execution generator. Override in subclasses.
        
        Args:
            bot: The bot instance with access to all systems
            
        Yields:
            Control back to the bot loop
            
        Example:
            def execute(self, bot):
                yield from bot.transition.TravelTo(self.INFO.start_map_id)
                yield from bot.movement.MoveTo(1000, 2000)
                self.finished = True
        """
        # Default implementation - override in subclasses
        self.finished = True
        yield
    
    def Execution_Routine(self, bot):
        """
        Legacy method name - calls execute() for backward compatibility.
        New code should use execute() instead.
        """
        yield from self.execute(bot)
    
    # ==================
    # LEGACY COMPATIBILITY
    # ==================
    
    def GetInfo(self) -> dict:
        """
        Legacy method - returns task info as dictionary.
        
        New code should use get_info() classmethod instead.
        This method exists for backward compatibility with existing
        code that expects the dictionary format.
        
        Returns:
            Dict with task metadata in legacy format
        """
        info = self.INFO
        
        result = {
            "Name": info.name,
            "Description": info.description,
            "Type": info.task_type.value if isinstance(info.task_type, TaskType) else str(info.task_type),
            "Recommended_Builds": info.recommended_builds or ["Any"],
            "HM_Tips": info.hm_tips or ""
        }
        
        # Convert loadout to legacy format if present
        if info.loadout:
            result["Mandatory_Loadout"] = self._loadout_to_dict(info.loadout)
        
        return result
    
    def _loadout_to_dict(self, loadout) -> dict:
        """Convert LoadoutConfig to legacy dict format."""
        result = {}
        
        if loadout.normal_mode:
            result["NM"] = self._mandatory_loadout_to_dict(loadout.normal_mode)
        
        if loadout.hard_mode:
            result["HM"] = self._mandatory_loadout_to_dict(loadout.hard_mode)
        
        return result
    
    def _mandatory_loadout_to_dict(self, ml) -> dict:
        """Convert MandatoryLoadout to legacy dict format."""
        result = {}
        
        if ml.player_build:
            pb = ml.player_build
            if pb.builds:
                result["Player_Build"] = pb.builds
            if pb.expected_skills != 8:
                result["Expected_Skills"] = pb.expected_skills
            if pb.equipment:
                result["Equipment"] = pb.equipment
            if pb.weapons:
                result["Weapons"] = pb.weapons
        
        if ml.required_heroes:
            result["Required_Heroes"] = [
                {
                    "HeroID": h.hero_id,
                    "Role": h.role,
                    "Build": h.build,
                    "Expected_Skills": h.expected_skills,
                    "Equipment": h.equipment,
                    "Weapons": h.weapons
                }
                for h in ml.required_heroes
            ]
        
        if ml.notes:
            result["Notes"] = ml.notes
        
        return result