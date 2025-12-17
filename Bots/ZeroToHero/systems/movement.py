"""
Movement System - Handles pathfinding and movement control.
"""
from Py4GWCoreLib import Routines, Player, Utils
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from data.timing import Timing


class Movement:
    """
    Handles character movement and pathfinding.
    """
    
    def __init__(self):
        self.follow_handler = Routines.Movement.FollowXY(tolerance=100)
        self.path_handler = None
    
    def move_to(self, x: float, y: float, tolerance: int = 100):
        """Moves to a specific coordinate."""
        self.follow_handler.tolerance = tolerance
        self.follow_handler.move_to_waypoint(x, y)
        
        while not self.follow_handler.has_arrived():
            self.follow_handler.update()
            yield
    
    def move_to_target(self, agent_id: int, range: int = 200):
        """
        Moves until within specific range of an agent.
        Does not interact, just approaches.
        """
        if not GLOBAL_CACHE.Agent.IsValid(agent_id):
            return

        Player.ChangeTarget(agent_id)
        
        # Initial Move
        target_x, target_y = GLOBAL_CACHE.Agent.GetXY(agent_id)
        Player.Move(target_x, target_y)
        
        while True:
            if not GLOBAL_CACHE.Agent.IsValid(agent_id):
                break
            
            # Use Utils.Distance instead of Player.GetDistanceFromAgent (which likely doesn't exist)
            my_x, my_y = Player.GetXY()
            target_x, target_y = GLOBAL_CACHE.Agent.GetXY(agent_id)
            dist = Utils.Distance((my_x, my_y), (target_x, target_y))
            
            if dist < range:
                break
            
            # Re-issue move command if stopped but not there yet
            # Or if target has moved significantly? For now, we rely on stopping.
            if not Player.IsMoving():
                 Player.Move(target_x, target_y)
                 
            yield

    def follow_path(self, path_coords: list):
        """Follows a list of coordinates."""
        self.path_handler = Routines.Movement.PathHandler(path_coords)
        self.follow_handler.reset()
        
        while not Routines.Movement.IsFollowPathFinished(self.path_handler, self.follow_handler):
            Routines.Movement.FollowPath(self.path_handler, self.follow_handler)
            yield
    
    def stop(self):
        """Forces the bot to stop moving."""
        Player.CancelMove()
        self.follow_handler.reset()
        if self.path_handler:
            self.path_handler.reset()
    
    # ==================
    # LEGACY ALIASES
    # ==================
    
    def MoveTo(self, x: float, y: float, tolerance: int = 100):
        yield from self.move_to(x, y, tolerance)
    
    def FollowPath(self, path_coords: list):
        yield from self.follow_path(path_coords)
    
    def Stop(self):
        self.stop()