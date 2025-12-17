"""
Timer utilities for Zero To Hero bot.

Provides simple elapsed-time tracking without scattered time.time() calls.
"""
import time


class Timer:
    """
    Simple elapsed-time timer.
    
    Usage:
        timer = Timer()
        # ... do stuff ...
        if timer.has_elapsed(5000):  # 5 seconds
            print("Time's up!")
    """
    
    def __init__(self, auto_start: bool = True):
        """
        Args:
            auto_start: If True, timer starts immediately. If False, call start().
        """
        self.start_time = time.time() if auto_start else None
    
    def start(self):
        """Start or restart the timer."""
        self.start_time = time.time()
    
    def reset(self):
        """Alias for start() - restarts the timer."""
        self.start()
    
    def stop(self):
        """Stop the timer (elapsed time will freeze)."""
        self.start_time = None
    
    @property
    def is_running(self) -> bool:
        """Check if timer is currently running."""
        return self.start_time is not None
    
    def elapsed_ms(self) -> float:
        """Returns elapsed time in milliseconds."""
        if self.start_time is None:
            return 0
        return (time.time() - self.start_time) * 1000
    
    def elapsed_sec(self) -> float:
        """Returns elapsed time in seconds."""
        if self.start_time is None:
            return 0
        return time.time() - self.start_time
    
    def has_elapsed(self, milliseconds: float) -> bool:
        """
        Check if the specified time has passed.
        
        Args:
            milliseconds: Time to check against
            
        Returns:
            True if elapsed time >= milliseconds
        """
        return self.elapsed_ms() >= milliseconds
    
    def has_elapsed_sec(self, seconds: float) -> bool:
        """
        Check if the specified time in seconds has passed.
        
        Args:
            seconds: Time to check against
            
        Returns:
            True if elapsed time >= seconds
        """
        return self.elapsed_sec() >= seconds


class Timeout:
    """
    Timeout checker for loops and waiting operations.
    
    Cleaner alternative to manual timer checks in while loops.
    
    Usage:
        timeout = Timeout(5000)  # 5 second timeout
        while not timeout.expired:
            # do stuff
            if condition_met:
                break
            yield
        
        if timeout.expired:
            print("Operation timed out!")
    """
    
    def __init__(self, milliseconds: float):
        """
        Args:
            milliseconds: Timeout duration in milliseconds
        """
        self.limit_ms = milliseconds
        self.timer = Timer()
    
    @property
    def expired(self) -> bool:
        """Check if the timeout has been reached."""
        return self.timer.has_elapsed(self.limit_ms)
    
    @property
    def remaining_ms(self) -> float:
        """Get remaining time in milliseconds (0 if expired)."""
        return max(0, self.limit_ms - self.timer.elapsed_ms())
    
    @property
    def remaining_sec(self) -> float:
        """Get remaining time in seconds (0 if expired)."""
        return self.remaining_ms / 1000
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.timer.elapsed_ms()
    
    @property
    def elapsed_sec(self) -> float:
        """Get elapsed time in seconds."""
        return self.timer.elapsed_sec()
    
    def reset(self):
        """Reset the timeout timer."""
        self.timer.reset()
    
    def extend(self, additional_ms: float):
        """Extend the timeout by additional milliseconds."""
        self.limit_ms += additional_ms