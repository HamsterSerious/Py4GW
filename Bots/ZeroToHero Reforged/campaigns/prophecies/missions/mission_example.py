"""
Example Mission - Demo to test the declarative pattern.

This is a simple example showing the declarative FSM pattern.
"""
from core.base_task import BaseTask
from models.task import TaskInfo
from data.enums import TaskType


class MissionExample(BaseTask):
    """Example mission demonstrating the declarative pattern."""
    
    INFO = TaskInfo(
        name="Mission Example",
        description="A demo mission to test the declarative FSM pattern.",
        task_type=TaskType.MISSION
    )

    def build_routine(self, bot) -> None:
        """
        Build the example routine declaratively.
        
        This shows the basic pattern:
        1. Use bot.States.AddHeader() for visual sections
        2. Use bot.Move.XY(), bot.Wait.ForTime() etc for simple actions
        3. Use bot.States.AddCustomState() for complex logic
        """
        
        # === SETUP ===
        bot.States.AddHeader("Example Mission - Setup")
        
        # Initialize objectives (for UI display)
        bot.States.AddCustomState(
            lambda: self._init_objectives(),
            "Initialize Objectives"
        )
        
        # === STEP 1: Movement ===
        bot.States.AddHeader("Step 1: Travel to Statue")
        
        bot.States.AddCustomState(
            self.create_objective_activator("Travel to Statue"),
            "Activate Objective"
        )
        
        # Simple movement
        bot.Move.XY(1000, 2000)
        bot.Wait.ForTime(500)
        
        bot.States.AddCustomState(
            self.create_objective_completer("Travel to Statue"),
            "Complete Objective"
        )
        
        # === STEP 2: Simulated Combat ===
        bot.States.AddHeader("Step 2: Clear Area")
        
        bot.States.AddCustomState(
            self.create_objective_activator("Clear Area"),
            "Activate Objective"
        )
        
        # Simulate clearing enemies with custom state
        bot.States.AddCustomState(
            lambda: self._simulate_combat(),
            "Fight Enemies"
        )
        
        bot.States.AddCustomState(
            self.create_objective_completer("Clear Area"),
            "Complete Objective"
        )
        
        # === STEP 3: Boss Fight ===
        bot.States.AddHeader("Step 3: Defeat Boss")
        
        bot.States.AddCustomState(
            self.create_objective_activator("Defeat Boss"),
            "Activate Objective"
        )
        
        # Wait for "combat" (in real mission this would be actual combat)
        bot.Wait.ForTime(2000)
        
        bot.States.AddCustomState(
            self.create_objective_completer("Defeat Boss"),
            "Complete Objective"
        )
        
        # === COMPLETE ===
        bot.States.AddHeader("Mission Complete!")
        
        bot.States.AddCustomState(
            self.create_status_updater("Mission Complete!"),
            "Final Status"
        )
    
    # ==================
    # CUSTOM STATE GENERATORS
    # ==================
    
    def _init_objectives(self):
        """Initialize objectives for UI display."""
        self.add_objective("Travel to Statue", total=1)
        self.add_objective("Clear Area", total=3)
        self.add_objective("Defeat Boss", total=1)
        self.update_status("Mission initialized!")
        yield
    
    def _simulate_combat(self):
        """Simulate fighting enemies."""
        from Py4GWCoreLib import Routines
        
        obj = self.get_objective("Clear Area")
        
        for i in range(3):
            self.update_status(f"Fighting enemy {i + 1}/3...")
            yield from Routines.Yield.wait(1000)
            
            if obj:
                obj.current_count = i + 1
        
        self.update_status("Area cleared!")
        yield