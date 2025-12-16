from Py4GWCoreLib import *

class Movement:
    def __init__(self):
        # We use a single shared handler for following coordinates
        self.follow_handler = Routines.Movement.FollowXY(tolerance=100)
        self.path_handler = None

    def MoveTo(self, x, y, tolerance=100):
        """
        Moves to a specific coordinate.
        """
        # 1. Setup
        self.follow_handler.tolerance = tolerance
        self.follow_handler.move_to_waypoint(x, y)
        
        # 2. Execution Loop
        # We must keep updating until we arrive
        while not self.follow_handler.has_arrived():
            self.follow_handler.update()
            yield # Pass control back to the bot for one frame

    def FollowPath(self, path_coords):
        """
        Follows a list of coordinates [(x,y), (x,y), ...].
        """
        # 1. Setup
        self.path_handler = Routines.Movement.PathHandler(path_coords)
        self.follow_handler.reset()
        
        # 2. Execution Loop
        # Check if BOTH the path traversal is done AND we reached the final point
        while not Routines.Movement.IsFollowPathFinished(self.path_handler, self.follow_handler):
            # This function performs one "tick" of movement logic
            Routines.Movement.FollowPath(self.path_handler, self.follow_handler)
            yield # Pass control back to the bot for one frame

    def Stop(self):
        """
        Forces the bot to stop moving.
        """
        Player.CancelMove()
        self.follow_handler.reset()
        if self.path_handler:
            self.path_handler.reset()