"""
Movement System - Handles pathfinding and movement control.
"""
import time
import Py4GW
from Py4GWCoreLib import Routines, Player, Utils
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE

from core.constants import BOT_NAME
from data.timing import Timing, Range


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
    # GATE/BARRIER HANDLING
    # ==================

    def move_with_gate_check(
        self,
        x: float,
        y: float,
        stuck_timeout_sec: float = 3.0,
        retry_delay_sec: float = 5.0,
        arrival_tolerance: int = 150,
        max_retries: int = 60,
        status_callback=None
    ):
        """
        Moves to coordinates while handling gates/barriers that may block progress.
        
        Detects when the player stops making progress toward the target
        (e.g., blocked by a closed gate) and waits before retrying.
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
            stuck_timeout_sec: Seconds of no progress before considering blocked (default: 3.0)
            retry_delay_sec: Seconds to wait before retrying after being blocked (default: 5.0)
            arrival_tolerance: Distance to target considered "arrived" (default: 150)
            max_retries: Maximum retry attempts before giving up (default: 60 = ~5 minutes)
            status_callback: Optional function(str) to report status updates
            
        Yields for coroutine execution.
        Returns True if arrived, False if max_retries exceeded.
        
        Example:
            # Wait at gate position until gate opens, then proceed
            yield from bot.movement.move_with_gate_check(
                -1505.30, 14471.92,  # Waypoint AFTER the gate
                status_callback=lambda msg: self.update_status(msg)
            )
        """
        target = (x, y)
        retries = 0
        
        def log(msg):
            Py4GW.Console.Log(BOT_NAME, f"[GateCheck] {msg}", Py4GW.Console.MessageType.Info)
            if status_callback:
                status_callback(msg)
        
        while retries < max_retries:
            # Get current position and distance to target
            my_pos = Player.GetXY()
            current_distance = Utils.Distance(my_pos, target)
            
            # Check if we've arrived
            if current_distance < arrival_tolerance:
                log(f"Arrived at destination!")
                return True
            
            # Start moving toward target
            Player.Move(x, y)
            
            # Track progress
            last_progress_time = time.time()
            best_distance = current_distance
            
            # Movement loop - monitor progress
            while True:
                # Safety: abort if map is loading
                if GLOBAL_CACHE.Map.IsMapLoading():
                    log("Map loading detected, aborting movement")
                    return False
                
                my_pos = Player.GetXY()
                current_distance = Utils.Distance(my_pos, target)
                
                # Check arrival
                if current_distance < arrival_tolerance:
                    log(f"Arrived at destination!")
                    return True
                
                # Check if we made progress (got closer to target)
                if current_distance < best_distance - 10:  # 10 unit buffer to avoid micro-fluctuations
                    best_distance = current_distance
                    last_progress_time = time.time()
                
                # Check if we're stuck (no progress for stuck_timeout_sec)
                time_since_progress = time.time() - last_progress_time
                if time_since_progress >= stuck_timeout_sec:
                    # We're blocked (probably by a gate)
                    retries += 1
                    remaining_dist = int(current_distance)
                    log(f"Blocked! Distance to target: {remaining_dist}. Waiting {retry_delay_sec}s... (attempt {retries}/{max_retries})")
                    
                    # Stop movement while waiting
                    Player.CancelMove()
                    
                    # Wait before retrying
                    yield from Routines.Yield.wait(int(retry_delay_sec * 1000))
                    
                    # Break inner loop to retry outer loop
                    break
                
                yield from Routines.Yield.wait(100)  # Check every 100ms
        
        # Max retries exceeded
        log(f"Max retries ({max_retries}) exceeded. Giving up.")
        return False

    def move_to_waypoint_with_gate(
        self,
        gate_position: tuple,
        target_position: tuple,
        stuck_timeout_sec: float = 3.0,
        retry_delay_sec: float = 5.0,
        status_callback=None
    ):
        """
        Convenience method: Move to gate position first, then wait for gate to open.
        
        This is useful when you need to:
        1. First walk TO the gate
        2. Then wait for the gate to open
        3. Then continue to the next waypoint
        
        Args:
            gate_position: (x, y) tuple - position in front of the gate
            target_position: (x, y) tuple - position after the gate (used for progress check)
            stuck_timeout_sec: How long without progress before assuming blocked
            retry_delay_sec: How long to wait before retrying
            status_callback: Optional status update function
            
        Yields for coroutine execution.
        Returns True if successfully passed through gate area.
        
        Example:
            yield from bot.movement.move_to_waypoint_with_gate(
                gate_position=(-155.00, 14430.16),
                target_position=(-1505.30, 14471.92),
                status_callback=lambda msg: self.update_status(msg)
            )
        """
        def log(msg):
            Py4GW.Console.Log(BOT_NAME, f"[GateWait] {msg}", Py4GW.Console.MessageType.Info)
            if status_callback:
                status_callback(msg)
        
        # Step 1: Move to the gate position (standard movement)
        log(f"Moving to gate area...")
        yield from self.move_to(gate_position[0], gate_position[1], tolerance=200)
        
        # Step 2: Now try to move through/past the gate
        log(f"Waiting for gate to open...")
        success = yield from self.move_with_gate_check(
            target_position[0],
            target_position[1],
            stuck_timeout_sec=stuck_timeout_sec,
            retry_delay_sec=retry_delay_sec,
            status_callback=status_callback
        )
        
        return success

    # ==================
    # ESCORT HANDLING
    # ==================

    def escort_npc(
        self,
        npc_model_id: int,
        path: list,
        max_distance: int = 500,
        status_callback=None
    ):
        """
        Follow a path while ensuring an NPC stays within range.
        
        If the player would move too far from the NPC, we wait for them
        to catch up before continuing. The NPC is found by ModelID.
        
        Args:
            npc_model_id: ModelID of the NPC to escort
            path: List of (x, y) waypoints to follow
            max_distance: Maximum allowed distance from NPC (default 500)
            status_callback: Optional function(str) for status updates
            
        Yields for coroutine execution.
        Returns True if escort completed, False if NPC lost/died.
        """
        def log(msg):
            Py4GW.Console.Log(BOT_NAME, f"[Escort] {msg}", Py4GW.Console.MessageType.Info)
            if status_callback:
                status_callback(msg)
        
        def find_npc() -> int:
            """Find the escort NPC by ModelID."""
            try:
                # Check ally array for the NPC
                allies = GLOBAL_CACHE.AgentArray.GetAllyArray()
                for agent_id in allies:
                    if GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id) == npc_model_id:
                        return agent_id
                
                # Also check NPC array
                npcs = GLOBAL_CACHE.AgentArray.GetNPCArray()
                for agent_id in npcs:
                    if GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id) == npc_model_id:
                        return agent_id
            except:
                pass
            return 0
        
        def get_npc_distance(npc_id: int) -> float:
            """Get distance to the NPC."""
            try:
                my_pos = Player.GetXY()
                npc_pos = GLOBAL_CACHE.Agent.GetXY(npc_id)
                return Utils.Distance(my_pos, npc_pos)
            except:
                return 9999
        
        log("Starting escort...")
        
        for waypoint_idx, (target_x, target_y) in enumerate(path):
            target = (target_x, target_y)
            log(f"Moving to waypoint {waypoint_idx + 1}/{len(path)}")
            
            while True:
                # Safety: Abort if map loading
                if GLOBAL_CACHE.Map.IsMapLoading():
                    return False
                
                # Find the NPC
                npc_id = find_npc()
                if npc_id == 0:
                    log("Warning: Lost escort NPC!")
                    # Try to wait a moment - they might be spawning
                    yield from Routines.Yield.wait(1000)
                    npc_id = find_npc()
                    if npc_id == 0:
                        log("ERROR: Escort NPC not found!")
                        return False
                
                # Check NPC health (if they can die)
                try:
                    if GLOBAL_CACHE.Agent.IsDead(npc_id):
                        log("ERROR: Escort NPC died!")
                        return False
                except:
                    pass
                
                # Get positions
                my_pos = Player.GetXY()
                npc_distance = get_npc_distance(npc_id)
                distance_to_target = Utils.Distance(my_pos, target)
                
                # Check if we've arrived at this waypoint
                if distance_to_target < Range.WAYPOINT_ARRIVAL:
                    break  # Move to next waypoint
                
                # Check if we're too far from NPC
                if npc_distance > max_distance:
                    # Stop and wait for NPC to catch up
                    Player.CancelMove()
                    log(f"Waiting for NPC (distance: {npc_distance:.0f})...")
                    
                    # Wait until NPC is closer
                    wait_timeout = 0
                    while npc_distance > (max_distance * 0.7):  # Wait until 70% of max
                        yield from Routines.Yield.wait(200)
                        npc_distance = get_npc_distance(npc_id)
                        wait_timeout += 200
                        
                        # Safety timeout - if waiting too long, something is wrong
                        if wait_timeout > 10000:
                            log("Warning: NPC taking too long to catch up")
                            break
                        
                        # Check if NPC died while waiting
                        npc_id = find_npc()
                        if npc_id == 0:
                            log("ERROR: Lost NPC while waiting!")
                            return False
                    
                    log("NPC caught up, continuing...")
                
                # Move toward target
                Player.Move(target_x, target_y)
                
                yield from Routines.Yield.wait(Timing.MOVEMENT_POLL)
        
        log("Escort path complete!")
        return True

    # ==================
    # LEGACY ALIASES
    # ==================
    
    def MoveTo(self, x: float, y: float, tolerance: int = 100):
        yield from self.move_to(x, y, tolerance)
    
    def FollowPath(self, path_coords: list):
        yield from self.follow_path(path_coords)
    
    def Stop(self):
        self.stop()