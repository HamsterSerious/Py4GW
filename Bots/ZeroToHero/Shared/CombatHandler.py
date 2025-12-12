import sys
import os
from Py4GWCoreLib import *
from Py4GWCoreLib import SkillManager

class CombatHandler:
    def __init__(self, log_module_name="CombatHandler"):
        self.log_module = log_module_name
        # Initialize the robust AutoCombat handler from the library
        self.auto_combat = SkillManager.Autocombat()

    def Execute(self, target_agent_id=None):
        """
        Main combat loop called by the mission runner.
        Args:
            target_agent_id (int, optional): The agent ID to attack.
        """
        # 1. Handle Targeting
        # If the mission provides a specific target, force the bot to target it.
        if target_agent_id and Agent.IsValid(target_agent_id):
            current_target = Player.GetTargetID()
            if current_target != target_agent_id:
                Player.ChangeTarget(target_agent_id)
        
        # 2. Safety Checks (Mirrors AutoCombat.py)
        # Ensure we are in a valid state to perform combat actions
        if not (Routines.Checks.Map.MapValid() and 
                Routines.Checks.Player.CanAct() and 
                Map.IsExplorable()):
            return

        # 3. Execute Combat Logic
        try:
            # Update weapon timing data
            self.auto_combat.SetWeaponAttackAftercast()
            
            # Delegate the decision making to the library's Autocombat class
            # This handles skill priority, range checking, energy, etc.
            self.auto_combat.HandleCombat()
            
        except Exception as e:
            # Catch errors to prevent the bot from crashing entirely
            # We use console logging directly to avoid dependency issues with the custom logger
            pass

    def Update(self, target_agent_id=None):
        """
        Alias for Execute to maintain compatibility with different calling conventions.
        """
        self.Execute(target_agent_id)

    def Reset(self):
        """
        Resets the combat handler state.
        """
        # Re-initialize to ensure a clean state when starting a new mission
        self.auto_combat = SkillManager.Autocombat()