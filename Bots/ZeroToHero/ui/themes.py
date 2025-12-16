"""
UI theme management and styling helpers.
"""
import PyImGui
from core.constants import Colors


class Theme:
    """Manages ImGui styling and theme application."""
    
    @staticmethod
    def push_styles():
        """Apply the bot's color scheme to ImGui."""
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, Colors.BODY_TEXT)
        PyImGui.push_style_color(PyImGui.ImGuiCol.Separator, Colors.SEPARATOR)
        PyImGui.push_style_color(PyImGui.ImGuiCol.Button, Colors.BUTTON)
        PyImGui.push_style_color(PyImGui.ImGuiCol.ButtonHovered, Colors.BUTTON_HOVER)
        PyImGui.push_style_color(PyImGui.ImGuiCol.ButtonActive, Colors.BUTTON_ACTIVE)
        PyImGui.push_style_color(PyImGui.ImGuiCol.FrameBg, Colors.FRAME_BG)
        PyImGui.push_style_color(PyImGui.ImGuiCol.FrameBgHovered, Colors.FRAME_HOVER)
        PyImGui.push_style_color(PyImGui.ImGuiCol.FrameBgActive, Colors.FRAME_ACTIVE)
        PyImGui.push_style_color(PyImGui.ImGuiCol.Header, Colors.BUTTON)
        PyImGui.push_style_color(PyImGui.ImGuiCol.HeaderHovered, Colors.BUTTON_HOVER)
        PyImGui.push_style_color(PyImGui.ImGuiCol.HeaderActive, Colors.BUTTON_ACTIVE)
    
    @staticmethod
    def pop_styles():
        """Remove applied styles."""
        PyImGui.pop_style_color(11)