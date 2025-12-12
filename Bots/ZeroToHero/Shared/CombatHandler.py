import sys
import os
from Py4GWCoreLib import *
from Py4GWCoreLib import SkillManager

class CombatHandler:
    def __init__(self, log_module_name="CombatHandler"):
        self.log_module = log_module_name
        # Initialize the robust AutoCombat handler from the library
        self.auto_combat = SkillManager.Autocombat()
        
        # FIX #2: Timer to throttle attack commands
        self._attack_timer = Timer()
        self._attack_timer.Start()
        
        # Track current target to detect target changes
        self._current_target = 0

    def Execute(self, target_agent_id=None):
        """
        Main combat loop called by the mission runner.
        Args:
            target_agent_id (int, optional): The agent ID to attack.
        """
        # 1. Handle Targeting
        if target_agent_id and Agent.IsValid(target_agent_id):
            current_target = Player.GetTargetID()
            if current_target != target_agent_id:
                Player.ChangeTarget(target_agent_id)
                self._current_target = target_agent_id
                self._attack_timer.Reset()  # Reset timer on new target
        
        # 2. Safety Checks (Mirrors AutoCombat.py)
        if not (Routines.Checks.Map.MapValid() and 
                Routines.Checks.Player.CanAct() and 
                Map.IsExplorable()):
            return

        # 3. Execute Combat Logic
        try:
            # Update weapon timing data
            self.auto_combat.SetWeaponAttackAftercast()
            
            # Delegate the decision making to the library's Autocombat class
            self.auto_combat.HandleCombat()
            
            # FIX #2: If we have a valid target and autocombat isn't attacking,
            # force an attack by interacting with the target
            if target_agent_id and Agent.IsValid(target_agent_id):
                if Agent.IsAlive(target_agent_id):
                    # Check if player is idle (not already attacking/casting)
                    player_id = Player.GetAgentID()
                    
                    # Only send attack command every 500ms to avoid spam
                    if self._attack_timer.HasElapsed(500):
                        # Check if we're not already attacking this target
                        if not Agent.IsAttacking(player_id) and not Agent.IsCasting(player_id):
                            # Interact with enemy to initiate attack
                            Player.Interact(target_agent_id, call_target=False)
                        self._attack_timer.Reset()
            
        except Exception as e:
            # Catch errors to prevent the bot from crashing entirely
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
        self._attack_timer.Reset()
        self._current_target = 0
