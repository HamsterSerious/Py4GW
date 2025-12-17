"""
Base window class for Zero To Hero bot UI.

Provides common window management functionality to reduce boilerplate.
"""
import PyImGui
from abc import ABC, abstractmethod
from typing import Tuple


class BaseWindow(ABC):
    """
    Abstract base class for all UI windows.
    
    Handles common patterns:
    - Initial window sizing
    - Visibility toggling
    - Standard draw loop structure
    
    Subclasses must:
    1. Set TITLE and SIZE class attributes
    2. Implement is_visible property
    3. Implement draw_content() method
    
    Example:
        class MyWindow(BaseWindow):
            TITLE = "My Window"
            SIZE = (400, 300)
            
            @property
            def is_visible(self) -> bool:
                return self.bot.show_my_window
            
            def draw_content(self):
                PyImGui.text("Hello!")
    """
    
    # Override in subclasses
    TITLE: str = "Window"
    SIZE: Tuple[int, int] = (400, 300)
    FLAGS: int = 0  # PyImGui window flags
    
    def __init__(self, bot):
        """
        Args:
            bot: Reference to ZeroToHeroBot instance
        """
        self.bot = bot
        self._first_run = True
    
    @property
    @abstractmethod
    def is_visible(self) -> bool:
        """
        Return True if window should be drawn.
        Override to control visibility.
        """
        return True
    
    @abstractmethod
    def draw_content(self):
        """
        Draw the window content.
        Override to implement window-specific content.
        Called inside PyImGui.begin()/end() block.
        """
        pass
    
    def draw(self):
        """
        Main draw function - call every frame.
        Handles visibility, sizing, and begin/end.
        """
        if not self.is_visible:
            self._first_run = True
            return
        
        # Set initial window size on first open
        if self._first_run:
            PyImGui.set_next_window_size(*self.SIZE)
            self._first_run = False
        
        # Draw window
        if PyImGui.begin(self.TITLE, self.FLAGS):
            self.draw_content()
        
        PyImGui.end()
    
    def reset(self):
        """Reset the window state (e.g., when closing)."""
        self._first_run = True


class ClosableWindow(BaseWindow):
    """
    Base class for windows with a close button.
    
    Adds a standard footer with a Close button.
    
    Subclasses should:
    1. Implement draw_content() for main content
    2. Implement set_visible(False) to close
    """
    
    def draw_content(self):
        """Draws content + close button."""
        self.draw_body()
        self._draw_close_button()
    
    @abstractmethod
    def draw_body(self):
        """
        Draw the main window body.
        Override for window-specific content.
        """
        pass
    
    @abstractmethod
    def set_visible(self, visible: bool):
        """
        Set window visibility.
        Override to update the appropriate flag.
        """
        pass
    
    def _draw_close_button(self):
        """Draw standard close button at bottom."""
        PyImGui.separator()
        if PyImGui.button("Close", -1, 0):
            self.set_visible(False)
