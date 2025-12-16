"""
UI Theme configuration for Zero To Hero bot.
Centralized styling to maintain consistent look.

Note: PyImGui in Py4GW has limited style support.
This module provides safe no-op wrappers that can be extended
once the available PyImGui API is determined.
"""


class Theme:
    """
    Centralized theme management for the bot UI.
    
    Currently provides no-op methods since PyImGui.ImGuiStyleVar
    is not available in the Py4GW wrapper. These can be filled in
    once the correct API is discovered.
    """
    
    @classmethod
    def push_styles(cls):
        """Push common style modifications. Currently a no-op."""
        # PyImGui.ImGuiStyleVar not available in Py4GW
        # Add styling here once correct API is known
        pass
    
    @classmethod
    def pop_styles(cls):
        """Pop style modifications. Currently a no-op."""
        pass
    
    @classmethod
    def push_button_success(cls):
        """Push green button style. Currently a no-op."""
        pass
    
    @classmethod
    def push_button_danger(cls):
        """Push red button style. Currently a no-op."""
        pass
    
    @classmethod
    def push_button_warning(cls):
        """Push yellow/orange button style. Currently a no-op."""
        pass
    
    @classmethod
    def pop_button_style(cls):
        """Pop button color modifications. Currently a no-op."""
        pass