"""
Mission: Chahbek Village
Campaign: Nightfall

Save the village by defeating the corsairs and sinking their ships.
This is the first mission in the Nightfall campaign.

DECLARATIVE PATTERN:
This mission uses the BottingClass declarative FSM pattern.
- build_routine() adds states to the FSM
- No manual yield/yield from in build_routine
- Complex logic uses AddCustomState() with generators
"""
from core.base_task import BaseTask
from models.task import TaskInfo
from models.loadout import LoadoutConfig, MandatoryLoadout, HeroRequirement
from data.enums import TaskType
from Py4GWCoreLib.enums_src.Hero_enums import HeroType


class MissionChahbek(BaseTask):
    """Chahbek Village - First Nightfall mission."""
    
    INFO = TaskInfo(
        name="Chahbek Village",
        description="Save the village by defeating the corsairs and sinking their ships.",
        task_type=TaskType.MISSION,
        loadout=LoadoutConfig(
            normal_mode=MandatoryLoadout(
                required_heroes=[
                    HeroRequirement(hero_id=HeroType.Koss.value, role="Mandatory", build="Any")
                ],
                notes="Koss is mandatory for this mission."
            ),
            hard_mode=MandatoryLoadout(
                required_heroes=[
                    HeroRequirement(hero_id=HeroType.Koss.value, role="Mandatory", build="Any")
                ],
                notes="Koss is mandatory for this mission."
            )
        )
    )
    
    # ==================
    # MISSION CONSTANTS
    # ==================
    
    # Map IDs
    MAP_ID = 544                    # Chahbek Village (outpost/mission)
    MAP_ID_COMPLETION = 456         # Churrhir Fields (after completion)
    
    # NPCs
    NPC_DEHVAD_MODEL = 4751
    NPC_DEHVAD_POS = (3482.00, -5167.00)
    DIALOG_ENTER_MISSION = 0x84     # Dialog to enter mission
    
    # Gadgets
    GADGET_OIL = 6373
    GADGET_CATAPULT_1 = 6388
    GADGET_CATAPULT_2 = 6389
    
    # Positions
    OIL_POSITION = (-4781.00, -1776.00)
    CATAPULT_1_POSITION = (-1691.00, -2515.00)
    CATAPULT_2_POSITION = (-1733.00, -4172.00)
    
    # Path waypoints
    PATH_TO_BENNIS = [
        (1628.69, -3524.50),
        (-238.17, -5863.46),
        (-1997.69, -6181.05),
        (-4212.00, -6730.00),
    ]
    
    PATH_CLEANUP = [
        (-865.51, -2144.52),
        (-1733.83, -264.36),
        (-1628.37, 710.30),
    ]

    # ==================
    # BUILD ROUTINE (Declarative)
    # ==================

    def build_routine(self, bot) -> None:
        """
        Build the mission routine declaratively.
        
        This method is called ONCE when the task is queued.
        It adds states to the FSM - no yielding here.
        """
        
        # === SETUP PHASE ===
        bot.States.AddHeader("Setup - Travel & Team")
        
        # Travel to mission outpost
        bot.Map.Travel(target_map_id=self.MAP_ID)
        bot.Wait.ForMapLoad(target_map_id=self.MAP_ID)
        
        # Setup team and hard mode (complex logic -> custom state)
        bot.States.AddCustomState(
            lambda: self._setup_team_and_mode(bot),
            "Configure Team & Mode"
        )
        
        # === ENTER MISSION ===
        bot.States.AddHeader("Enter Mission")
        
        # Talk to Dehvad to enter mission
        bot.Move.XY(self.NPC_DEHVAD_POS[0], self.NPC_DEHVAD_POS[1])
        bot.Dialogs.AtXY(self.NPC_DEHVAD_POS[0], self.NPC_DEHVAD_POS[1], self.DIALOG_ENTER_MISSION)
        bot.Wait.UntilOnExplorable()
        bot.Wait.ForTime(2000)  # Wait for mission to fully load
        
        # Enable aggressive combat mode
        bot.Templates.Aggressive()
        
        # === OBJECTIVE 1: Kill Midshipman Bennis ===
        bot.States.AddHeader("Hunt Midshipman Bennis")
        
        # Follow path to boss area - auto_combat handles enemies
        for x, y in self.PATH_TO_BENNIS:
            bot.Move.XY(x, y)
        
        # Wait for combat to clear
        bot.Wait.UntilOutOfCombat()
        
        # === OBJECTIVE 2: Destroy Ship 1 ===
        bot.States.AddHeader("Destroy Corsair Ship 1")
        
        # Get oil
        bot.Move.XY(self.OIL_POSITION[0], self.OIL_POSITION[1])
        bot.Interact.WithGadgetID(self.GADGET_OIL)
        bot.Wait.ForTime(500)
        
        # Load catapult
        bot.Move.XY(self.CATAPULT_1_POSITION[0], self.CATAPULT_1_POSITION[1])
        bot.Interact.WithGadgetID(self.GADGET_CATAPULT_1)
        bot.Wait.ForTime(1500)
        
        # Fire catapult
        bot.Interact.WithGadgetID(self.GADGET_CATAPULT_1)
        bot.Wait.ForTime(2000)  # Wait for ship destruction animation
        
        # === OBJECTIVE 3: Destroy Ship 2 ===
        bot.States.AddHeader("Destroy Corsair Ship 2")
        
        # Get oil again
        bot.Move.XY(self.OIL_POSITION[0], self.OIL_POSITION[1])
        bot.Interact.WithGadgetID(self.GADGET_OIL)
        bot.Wait.ForTime(500)
        
        # Load catapult 2
        bot.Move.XY(self.CATAPULT_2_POSITION[0], self.CATAPULT_2_POSITION[1])
        bot.Interact.WithGadgetID(self.GADGET_CATAPULT_2)
        bot.Wait.ForTime(1500)
        
        # Fire catapult 2
        bot.Interact.WithGadgetID(self.GADGET_CATAPULT_2)
        bot.Wait.ForTime(2000)
        
        # === CLEANUP: Clear Remaining Enemies ===
        bot.States.AddHeader("Clear Remaining Corsairs")
        
        for x, y in self.PATH_CLEANUP:
            bot.Move.XY(x, y)
        
        bot.Wait.UntilOutOfCombat()
        
        # === MISSION COMPLETE ===
        bot.States.AddHeader("Mission Complete")
        bot.Wait.ForMapToChange(target_map_id=self.MAP_ID_COMPLETION)

    # ==================
    # CUSTOM STATE GENERATORS
    # ==================
    
    def _setup_team_and_mode(self, bot):
        """
        Generator for team setup and hard mode configuration.
        
        This is complex logic that needs conditionals and yields,
        so we use AddCustomState() to wrap it.
        """
        from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
        from Py4GWCoreLib import Routines
        
        # Handle hard mode toggle
        current_hm = GLOBAL_CACHE.Party.IsHardMode()
        
        if self.use_hard_mode and not current_hm:
            GLOBAL_CACHE.Party.SetHardMode()
            yield from Routines.Yield.wait(1500)
        elif not self.use_hard_mode and current_hm:
            GLOBAL_CACHE.Party.SetNormalMode()
            yield from Routines.Yield.wait(1500)
        
        # Get party size for this map
        party_size = GLOBAL_CACHE.Map.GetMaxPartySize()
        mode_str = "HM" if self.use_hard_mode else "NM"
        
        # Load team using TeamManager
        yield from bot.team_manager.load_team(party_size, mode_str)
        
        # Final yield to complete the state
        yield