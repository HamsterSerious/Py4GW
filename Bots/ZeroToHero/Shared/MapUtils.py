"""
MapUtils.py - Map validation and mission state utilities for ZeroToHero missions.

Provides:
- Map validation (correct outpost/mission)
- Mission completion detection
- Loading state handling
- Cinematic detection
"""

from Py4GWCoreLib import *


class MapValidator:
    """
    Validates map state and detects mission completion.
    """
    
    @staticmethod
    def GetCurrentMapID():
        """Get the current map ID."""
        try:
            return Map.GetMapID()
        except Exception:
            return 0
    
    @staticmethod
    def GetCurrentMapName():
        """Get the current map name."""
        try:
            map_id = Map.GetMapID()
            return Map.GetMapName(map_id)
        except Exception:
            return "Unknown"
    
    @staticmethod
    def IsOnMap(expected_map_id):
        """
        Check if player is on a specific map.
        
        Args:
            expected_map_id (int): The map ID to check for
            
        Returns:
            bool: True if on the expected map
        """
        return MapValidator.GetCurrentMapID() == expected_map_id
    
    @staticmethod
    def IsInOutpost():
        """Check if player is in an outpost."""
        try:
            return Map.IsOutpost()
        except Exception:
            return False
    
    @staticmethod
    def IsInExplorable():
        """Check if player is in an explorable/mission area."""
        try:
            return Map.IsExplorable()
        except Exception:
            return False
    
    @staticmethod
    def IsMapLoading():
        """Check if map is currently loading."""
        try:
            return Map.IsMapLoading()
        except Exception:
            return True  # Assume loading if we can't check
    
    @staticmethod
    def IsInCinematic():
        """Check if a cinematic is playing."""
        try:
            return Map.IsInCinematic()
        except Exception:
            return False
    
    @staticmethod
    def IsPartyDefeated():
        """Check if the party has been defeated."""
        try:
            return Party.IsPartyDefeated()
        except Exception:
            return False


class MissionStateTracker:
    """
    Tracks mission state and detects completion/failure.
    
    Usage:
        tracker = MissionStateTracker(mission_map_id=123)
        tracker.Update()  # Call each frame
        if tracker.IsMissionComplete():
            # Handle completion
    """
    
    def __init__(self, mission_map_id, outpost_map_id=None):
        """
        Args:
            mission_map_id (int): The map ID of the mission instance
            outpost_map_id (int, optional): The map ID of the starting outpost
        """
        self.mission_map_id = mission_map_id
        self.outpost_map_id = outpost_map_id
        
        # State tracking
        self._mission_started = False
        self._mission_complete = False
        self._mission_failed = False
        self._last_map_id = 0
        self._cinematic_detected = False
        self._completion_reason = None
    
    def Reset(self):
        """Reset all tracking state."""
        self._mission_started = False
        self._mission_complete = False
        self._mission_failed = False
        self._last_map_id = 0
        self._cinematic_detected = False
        self._completion_reason = None
    
    def MarkMissionStarted(self):
        """Mark that the mission instance has been entered."""
        self._mission_started = True
        self._last_map_id = self.mission_map_id
    
    def IsMissionStarted(self):
        """Check if we've entered the mission."""
        return self._mission_started
    
    def IsMissionComplete(self):
        """Check if mission completed successfully."""
        return self._mission_complete
    
    def IsMissionFailed(self):
        """Check if mission failed (party wipe)."""
        return self._mission_failed
    
    def GetCompletionReason(self):
        """Get the reason for completion/failure."""
        return self._completion_reason
    
    def Update(self, logger=None):
        """
        Update mission state. Call this each frame.
        
        Args:
            logger: Optional logger for status messages
            
        Returns:
            bool: True if mission ended (complete or failed)
        """
        # Skip if already ended
        if self._mission_complete or self._mission_failed:
            return True
        
        # Skip if mission hasn't started yet
        if not self._mission_started:
            return False
        
        current_map = MapValidator.GetCurrentMapID()
        
        # Check for party defeat
        if MapValidator.IsPartyDefeated():
            self._mission_failed = True
            self._completion_reason = "Party Defeated"
            if logger:
                logger.Add("Party defeated!", (1, 0, 0, 1), prefix="[Defeat]")
            return True
        
        # Check for cinematic (often precedes mission end)
        if MapValidator.IsInCinematic():
            self._cinematic_detected = True
            # Don't return True yet - wait for map transition
            return False
        
        # Check if we left the mission map
        if current_map != self.mission_map_id and current_map != 0:
            map_name = MapValidator.GetCurrentMapName()
            
            if MapValidator.IsInOutpost():
                self._mission_complete = True
                self._completion_reason = f"Arrived at {map_name}"
            else:
                self._mission_complete = True
                self._completion_reason = f"Transitioned to {map_name}"
            return True
        
        # Update last known map
        self._last_map_id = current_map
        return False
    
    def VerifyCorrectMap(self, is_mission_phase, logger=None):
        """
        Verify the player is on the correct map for the current phase.
        
        Args:
            is_mission_phase (bool): True if we should be in mission, False if outpost
            logger: Optional logger for error messages
            
        Returns:
            bool: True if on correct map
        """
        current_map = MapValidator.GetCurrentMapID()
        
        if is_mission_phase:
            # Should be in mission
            if MapValidator.IsInExplorable():
                if current_map != self.mission_map_id:
                    if logger:
                        map_name = MapValidator.GetCurrentMapName()
                        logger.Add(f"Wrong mission map: {map_name} (ID: {current_map})", (1, 0.5, 0, 1), prefix="[Error]")
                    return False
            return True
        else:
            # Should be in outpost
            if self.outpost_map_id and MapValidator.IsInOutpost():
                if current_map != self.outpost_map_id:
                    if logger:
                        logger.Add(f"Wrong outpost (ID: {current_map}). Expected: {self.outpost_map_id}", (1, 0, 0, 1), prefix="[Error]")
                    return False
            return True


class MapWaiter:
    """
    Utility for waiting for map state changes.
    """
    
    def __init__(self):
        self._timer = Timer()
        self._timer.Start()
        self._waiting = False
    
    def Reset(self):
        """Reset the waiter state."""
        self._timer.Reset()
        self._waiting = False
    
    def WaitForMapLoad(self, timeout_ms=30000):
        """
        Wait for map to finish loading.
        
        Args:
            timeout_ms (int): Maximum wait time in milliseconds
            
        Returns:
            str: "loading", "ready", or "timeout"
        """
        if MapValidator.IsMapLoading():
            if not self._waiting:
                self._waiting = True
                self._timer.Reset()
            
            if self._timer.HasElapsed(timeout_ms):
                return "timeout"
            return "loading"
        
        self._waiting = False
        return "ready"
    
    def WaitForCinematicEnd(self, timeout_ms=60000):
        """
        Wait for cinematic to end.
        
        Args:
            timeout_ms (int): Maximum wait time
            
        Returns:
            str: "playing", "ended", or "timeout"
        """
        if MapValidator.IsInCinematic():
            if not self._waiting:
                self._waiting = True
                self._timer.Reset()
            
            if self._timer.HasElapsed(timeout_ms):
                return "timeout"
            return "playing"
        
        self._waiting = False
        return "ended"
