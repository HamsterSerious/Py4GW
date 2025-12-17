"""
Movement System - Handles pathfinding and movement control.
"""
from Py4GWCoreLib import Routines, Player

from data.timing import Timing


class Movement:
    """
    Handles character movement and pathfinding.
    
    Uses Py4GWCoreLib's FollowXY and PathHandler for movement.
    """
    
    def __init__(self):
        self.follow_handler = Routines.Movement.FollowXY(tolerance=100)
        self.path_handler = None
    
    def move_to(self, x: float, y: float, tolerance: int = 100):
        """
        Moves to a specific coordinate.
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
            tolerance: Distance threshold to consider "arrived"
            
        Yields for coroutine execution.
        """
        self.follow_handler.tolerance = tolerance
        self.follow_handler.move_to_waypoint(x, y)
        
        while not self.follow_handler.has_arrived():
            self.follow_handler.update()
            yield
    
    def follow_path(self, path_coords: list):
        """
        Follows a list of coordinates.
        
        Args:
            path_coords: List of (x, y) tuples
            
        Yields for coroutine execution.
        """
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
        """Legacy method name - use move_to() instead."""
        yield from self.move_to(x, y, tolerance)
    
    def FollowPath(self, path_coords: list):
        """Legacy method name - use follow_path() instead."""
        yield from self.follow_path(path_coords)
    
    def Stop(self):
        """Legacy method name - use stop() instead."""
        self.stop()
