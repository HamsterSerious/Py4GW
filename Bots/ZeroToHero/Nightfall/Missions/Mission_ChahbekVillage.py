"""
Mission_ChahbekVillage.py - Chahbek Village Mission Bot (Refactored)

Save the village by defeating the corsairs and sinking their ships.
Uses shared utilities for cleaner, more maintainable code.
"""

from Py4GWCoreLib import *
from Bots.ZeroToHero.Shared.MissionContext import BaseMission, MissionContext
from Bots.ZeroToHero.Shared.PartyUtils import PartyRequirements
from Bots.ZeroToHero.Shared.OutpostHandler import OutpostHandler
from Bots.ZeroToHero.Shared.InteractionUtils import BundlePickupState, GadgetInteractionState


class ChahbekVillage(BaseMission, MissionContext):
    """
    Chahbek Village Mission Bot
    """
    
    # --- MAP IDs ---
    Outpost_Map_ID = 544
    Mission_Map_ID = 544  # Same as outpost for Chahbek
    
    # --- NPC CONFIGURATION ---
    NPC_Position = (3482, -5167)
    NPC_Name = "First Spear Jahdugar"
    Dialog_Sequence = [0x84]  # Start mission directly
    
    # --- GADGET POSITIONS ---
    Gadget_Oil_Position = (-4781, -1776)
    Gadget_Catapult_1_Position = (-1691, -2515)
    Gadget_Catapult_2_Position = (-1733, -4172)
    
    # --- PATH DATA ---
    Path_Data = {
        "Step1": [(1672, -3500)],
        "Step2": [(51, -5261)],
        "Step3": [(-2201, -6408)],
        "Step4": [(-3847, -6360)],
        "Step5": [(-4500, -2856)],
        "ToOil": [(-4799, -1827)],
        "ToCata1": [(-2998, -2775), (-1720, -2520)],
        "ToCata2": [(-2998, -2775), (-1731, -4138)],
        "ToBeach": [(-531, -3264)],
        "ToCommander": [(-2196, -3)],
        "KillCommander": [(-1648, 1073)]
    }
    
    def GetInfo(self):
        return {
            "Name": "Chahbek Village",
            "Description": "Save the village by defeating the corsairs and sinking their ships.",
            "Recommended_Builds": ["Any", "Koss Required"],
            "HM_Tips": "Make sure to have strong Healers, as the Sunspear Recruits tend to die easily."
        }

    def __init__(self):
        super().__init__()
        
        # Initialize Path Handlers
        self.paths = {
            key: Routines.Movement.PathHandler(coords) 
            for key, coords in self.Path_Data.items()
        }
        
        # Outpost handler with party requirements
        self.outpost_handler = OutpostHandler(
            requirements=PartyRequirements(
                min_size=2,
                required_heroes=["Koss"]
            ),
            npc_position=self.NPC_Position,
            npc_name=self.NPC_Name,
            dialog_sequence=self.Dialog_Sequence,
            outpost_map_id=self.Outpost_Map_ID
        )
        
        # Bundle/Gadget interaction handlers (created on demand)
        self._oil_pickup = None
        self._catapult_interact = None
        
        # Track final phase
        self._final_phase_logged = False

    def Reset(self):
        """Reset mission state."""
        super().Reset()
        
        # Reset all paths
        for path in self.paths.values():
            path.reset()
        
        # Reset handlers
        self.outpost_handler.Reset()
        self._oil_pickup = None
        self._catapult_interact = None
        self._final_phase_logged = False

    def Execution_Routine(self, bot, logger):
        """Main execution routine."""
        # Skip if map loading
        if Map.IsMapLoading():
            return
        
        current_map = Map.GetMapID()
        if current_map == 0:
            return

        # --- CHECK FOR MISSION COMPLETION FIRST ---
        # If mission was started, check if it ended (map change, defeat, etc.)
        if self.mission_tracker.IsMissionStarted():
            if self.mission_tracker.Update(logger):
                # Mission ended (complete or failed)
                bot.is_running = False
                return
            
            # If we're in an outpost after mission started = mission completed
            if self.IsInOutpost():
                map_name = Map.GetMapName(current_map)
                logger.Add(f"Mission Complete!", (0, 1, 0, 1), prefix="[Victory]")
                bot.is_running = False
                return

        # --- OUTPOST PHASE (only if mission not started yet) ---
        if self.IsInOutpost() and not self.mission_tracker.IsMissionStarted():
            if self.outpost_handler.Execute(bot, logger):
                # Outpost complete, transition to mission
                self.step = 3
                self.sub_state = 0
                self.mission_tracker.MarkMissionStarted()
            elif self.outpost_handler.IsFailed():
                bot.is_running = False
            return

        # --- MISSION PHASE ---
        if self.IsInMission():
            # Mark mission started if not already
            if not self.mission_tracker.IsMissionStarted():
                self.mission_tracker.MarkMissionStarted()
                self.step = 3
                self.sub_state = 0
                logger.Add("Mission started!", (0, 1, 0, 1))
            
            self.ExecuteMissionLogic(bot, logger)
            return
        
        # --- WRONG MAP ---
        if self.mission_tracker.IsMissionStarted():
            logger.Add("Mission completed!", (0, 1, 0, 1), prefix="[Complete]")
        else:
            logger.Add(f"Go to Chahbek Village to start.", (1, 0.5, 0, 1))
        bot.is_running = False

    def ExecuteMissionLogic(self, bot, logger):
        """Mission instance logic - clear enemies, fire catapults, kill boss."""
        
        # --- PHASE 1: Clear path to docks ---
        if self.step == 3:
            self.ExecuteMove(self.paths["Step1"], 4, logger, "Clearing path to village...")
            
        elif self.step == 4:
            self.ExecuteMove(self.paths["Step2"], 5, logger)
            
        elif self.step == 5:
            self.ExecuteMove(self.paths["Step3"], 6, logger)
            
        elif self.step == 6:
            self.ExecuteMove(self.paths["Step4"], 7, logger)
            
        elif self.step == 7:
            self.ExecuteMove(self.paths["Step5"], 8, logger)

        # --- PHASE 2: First Catapult ---
        elif self.step == 8:
            self.ExecuteMove(self.paths["ToOil"], 9, logger, "Getting oil for catapult...")

        elif self.step == 9:
            self._ExecuteOilPickup(10, logger)

        elif self.step == 10:
            self.ExecuteMove(self.paths["ToCata1"], 11, logger)

        elif self.step == 11:
            self._ExecuteCatapultLoad(self.Gadget_Catapult_1_Position, 12, logger, "Loading Catapult 1")

        elif self.step == 12:
            self._ExecuteCatapultFire(self.Gadget_Catapult_1_Position, 13, logger, "Firing Catapult 1!")

        # --- PHASE 3: Second Catapult ---
        elif self.step == 13:
            self.ExecuteMove(self.paths["ToOil"], 14, logger, "Getting more oil...")

        elif self.step == 14:
            self._ExecuteOilPickup(15, logger)

        elif self.step == 15:
            self.ExecuteMove(self.paths["ToCata2"], 16, logger)

        elif self.step == 16:
            self._ExecuteCatapultLoad(self.Gadget_Catapult_2_Position, 17, logger, "Loading Catapult 2")

        elif self.step == 17:
            self._ExecuteCatapultFire(self.Gadget_Catapult_2_Position, 18, logger, "Firing Catapult 2!")

        # --- PHASE 4: Kill Boss ---
        elif self.step == 18:
            self.ExecuteMove(self.paths["ToBeach"], 19, logger, "Ships sunk! Engaging Corsair Commander...")

        elif self.step == 19:
            self.ExecuteMove(self.paths["ToCommander"], 20, logger)

        elif self.step == 20:
            self.ExecuteMove(self.paths["KillCommander"], 21, logger)

        elif self.step == 21:
            # Final phase - wait for mission completion trigger
            if not getattr(self, '_final_phase_logged', False):
                logger.Add("Finishing off remaining enemies...", (0, 1, 1, 1))
                self._final_phase_logged = True
            
            # Keep fighting while waiting for mission completion
            enemies = self.nav.GetNearbyEnemies()
            if enemies:
                self.combat_handler.Execute(target_agent_id=enemies[0])

    # --- Helper Methods for Catapult Mechanics ---

    def _ExecuteOilPickup(self, next_step, logger):
        """Handle oil pickup using BundlePickupState."""
        # Create handler if needed
        if self._oil_pickup is None:
            self._oil_pickup = BundlePickupState(
                self.Gadget_Oil_Position[0],
                self.Gadget_Oil_Position[1]
            )
        
        result = self._oil_pickup.Execute(logger)
        
        if result == "success":
            self._oil_pickup = None  # Reset for next use
            self.step = next_step
            self.sub_state = 0
        elif result == "failed":
            # Retry by recreating handler
            self._oil_pickup = None

    def _ExecuteCatapultLoad(self, position, next_step, logger, log_msg):
        """Handle loading oil into catapult."""
        if self._catapult_interact is None:
            self._catapult_interact = GadgetInteractionState(
                position[0], position[1],
                wait_ms=3000  # Longer wait for loading animation
            )
        
        result = self._catapult_interact.Execute(logger, log_msg)
        
        if result == "complete":
            self._catapult_interact = None
            self.step = next_step
            self.sub_state = 0

    def _ExecuteCatapultFire(self, position, next_step, logger, log_msg):
        """Handle firing the catapult."""
        if self._catapult_interact is None:
            self._catapult_interact = GadgetInteractionState(
                position[0], position[1],
                wait_ms=1500  # Shorter wait for firing
            )
        
        result = self._catapult_interact.Execute(logger, log_msg)
        
        if result == "complete":
            self._catapult_interact = None
            self.step = next_step
            self.sub_state = 0
