from dataclasses import dataclass

@dataclass
class TaskObjective:
    """
    Represents a single goal within a mission.
    """
    name: str                  # e.g., "Kill the Corsair Commander"
    current_count: int = 0     # Current progress (e.g., 0)
    total_count: int = 1       # Target (e.g., 1)
    is_completed: bool = False # Checkmark status
    is_active: bool = False    # Highlights the current step

    @property
    def percentage(self) -> float:
        if self.total_count == 0:
            return 1.0 if self.is_completed else 0.0
        return min(max(self.current_count / self.total_count, 0.0), 1.0)

    @property
    def status_text(self) -> str:
        """Returns string like '0/1' or 'Done'"""
        if self.is_completed:
            return "Done"
        return f"{self.current_count}/{self.total_count}"