from core.base_task import BaseTask
from models.task import TaskInfo
from data.enums import TaskType

class MissionExample(BaseTask):
    INFO = TaskInfo(
        name="Mission Example",
        description="A demo mission to test the Progress Window UI.",
        task_type=TaskType.MISSION
    )

    def execute(self, bot):
        # 1. Setup Objectives for the UI
        self.update_status("Initializing Mission Example...")
        obj_move = self.add_objective("Travel to Statue", total=1)
        obj_enemies = self.add_objective("Clear Area", total=3)
        obj_boss = self.add_objective("Defeat Boss", total=1)

        # 2. Step 1: Movement
        self.set_active_objective("Travel to Statue")
        self.update_status("Moving to waypoint...")
        
        # Fixed: Passed x, y as separate args, not a tuple
        yield from bot.movement.move_to(1000, 2000) 
        
        # Mark Step 1 Complete
        self.complete_objective("Travel to Statue")

        # 3. Step 2: Combat Simulation
        self.set_active_objective("Clear Area")
        self.update_status("Fighting enemies...")
        
        for i in range(3):
            bot.sleep(1000) # Simulate fighting time
            obj_enemies.current_count += 1
            yield

        self.complete_objective("Clear Area")

        # 4. Step 3: Boss
        self.set_active_objective("Defeat Boss")
        self.update_status("Boss fight in progress!")
        
        yield from bot.combat.kill_target(target_id=123) # Fake ID for demo
        
        self.complete_objective("Defeat Boss")
        self.update_status("Mission Complete!")
        self.finished = True