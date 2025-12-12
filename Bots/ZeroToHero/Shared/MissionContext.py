from Py4GWCoreLib import *
from .CombatHandler import CombatHandler
from .Navigation import MissionNavigation

class MissionContext:
    """
    Interface definition for Mission Modules.
    All missions must implement these methods.
    """
    def GetInfo(self):
        """Returns a dict with Name, Description, etc."""
        raise NotImplementedError

    def Execution_Routine(self, bot, logger):
        """
        Main update loop.
        Args:
            bot: The BotState object.
            logger: The LogConsole object for logging to UI.
        """
        raise NotImplementedError

    def Reset(self):
        """
        Called when the bot is started to reset the mission state.
        """
        pass

class BaseMission:
    """
    A helper class that provides standardized methods for common mission tasks
    like Movement, Interaction, and Dialogs. 
    
    NOTE: This class does NOT inherit from MissionContext to prevent the 
    MissionLoader from trying to load it as a standalone mission.
    Actual missions should inherit from (BaseMission, MissionContext).
    """
    def __init__(self):
        self.combat_handler = CombatHandler()
        self.nav = MissionNavigation(self.combat_handler)
        self.step = 1
        self.sub_state = 0
        self.timer = Timer()
        self.timer.Start()
        self.waiting = False

    def Reset(self):
        """Resets the standard variables."""
        self.step = 1
        self.sub_state = 0
        self.timer.Reset()
        self.nav.Reset()
        self.waiting = False

    def ExecuteMove(self, path_handler, next_step_id, logger, log_msg=None):
        """
        Executes a move operation using the MissionNavigation handler.
        Automatically advances the step when the path is finished.
        """
        if log_msg and not self.waiting:
             logger.Add(log_msg, prefix="[Move]")
             self.waiting = True # Prevent spamming log

        # self.nav.Execute returns True when destination reached and combat clear
        if self.nav.Execute(path_handler, logger):
            self.step = next_step_id
            self.waiting = False
            self.sub_state = 0 # Ensure sub_state is clean for next step
            path_handler.reset() # Reset path for future use if needed
            return True
        return False

    def ExecuteInteract(self, gadget_id, wait_after_ms, next_step_id, logger, log_msg="Interacting"):
        """
        Handles the full interaction loop:
        1. Checks validity.
        2. Interacts.
        3. Waits for X ms.
        4. Advances Step.
        """
        if self.sub_state == 0:
            if Agent.IsValid(gadget_id):
                logger.Add(f"{log_msg}...", prefix="[Interact]")
                Player.Interact(gadget_id)
                self.timer.Reset()
                self.sub_state = 1
            else:
                # If gadget not found yet, we just wait/retry next frame.
                pass 
            
        elif self.sub_state == 1:
            # Wait for the interaction ping or simple delay
            if self.timer.HasElapsed(wait_after_ms):
                self.sub_state = 0
                self.step = next_step_id
                return True
        return False

    def ExecuteDialog(self, npc_id, dialog_id, wait_after_ms, next_step_id, logger):
        """
        Handles the full dialog loop:
        1. Targets NPC.
        2. Approaches if too far (>250 range).
        3. Sends Dialog ID.
        4. Waits for X ms.
        5. Advances Step.
        """
        if self.sub_state == 0:
            if not Agent.IsValid(npc_id):
                return False

            Player.ChangeTarget(npc_id)
            
            # Simple approach if too far to talk
            p_pos = Player.GetXY()
            npc_pos = Agent.GetXY(npc_id)
            if Utils.Distance(p_pos, npc_pos) > 250:
                # FIX: Unpack tuple (x, y) for Player.Move(x, y)
                Player.Move(npc_pos[0], npc_pos[1])
            else:
                self.sub_state = 1
                
        elif self.sub_state == 1:
            Player.SendDialog(dialog_id)
            self.timer.Reset()
            self.sub_state = 2
            
        elif self.sub_state == 2:
            if self.timer.HasElapsed(wait_after_ms):
                self.sub_state = 0
                self.step = next_step_id
                return True
        return False