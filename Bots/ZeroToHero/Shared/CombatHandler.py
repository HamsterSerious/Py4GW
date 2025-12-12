"""
CombatHandler.py - Combat execution handler for ZeroToHero missions.

Wraps the Py4GW Autocombat system with mission-specific enhancements.
"""

import sys
import os
from Py4GWCoreLib import *
from Py4GWCoreLib import SkillManager
from .InteractionUtils import BundleHandler


class CombatHandler:
    def __init__(self, log_module_name="CombatHandler"):
        self.log_module = log_module_name
        # Initialize the robust AutoCombat handler from the library
        self.auto_combat = SkillManager.Autocombat()
        
        # Timer to throttle attack commands
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
        # Skip combat entirely if holding a bundle (oil, torch, etc.)
        if BundleHandler.IsHoldingBundle():
            return
        
        # 1. Handle Targeting
        if target_agent_id and Agent.IsValid(target_agent_id):
            current_target = Player.GetTargetID()
            if current_target != target_agent_id:
                Player.ChangeTarget(target_agent_id)
                self._current_target = target_agent_id
                self._attack_timer.Reset()  # Reset timer on new target
        
        # 2. Safety Checks
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
            
            # If we have a valid target and autocombat isn't attacking,
            # force an attack by interacting with the target
            if target_agent_id and Agent.IsValid(target_agent_id):
                if Agent.IsAlive(target_agent_id):
                    player_id = Player.GetAgentID()
                    
                    # Only send attack command every 500ms to avoid spam
                    if self._attack_timer.HasElapsed(500):
                        if not Agent.IsAttacking(player_id) and not Agent.IsCasting(player_id):
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
        self.auto_combat = SkillManager.Autocombat()
        self._attack_timer.Reset()
        self._current_target = 0
