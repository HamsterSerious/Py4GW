"""
Mission_BlacktideDen.py - Blacktide Den Mission Bot

Infiltrate the corsair base, recover the stolen goods, and eliminate the corsair threat.
Includes bonus objective: Kill 5 Rinkhal Monitors.
"""

from Py4GWCoreLib import *
from Bots.ZeroToHero.Shared.MissionContext import BaseMission, MissionContext
from Bots.ZeroToHero.Shared.PartyUtils import PartyRequirements
from Bots.ZeroToHero.Shared.OutpostHandler import OutpostHandler
from Bots.ZeroToHero.Shared.InteractionUtils import (
    BundleHandler, 
    EnemyFinder,
    ItemPickupState,
    WaitForHostileState,
    MultiKillTracker,
    ScanWhileMoving,
    ScanWhileMovingMulti
)


class BlacktideDen(BaseMission, MissionContext):
    """
    Blacktide Den Mission Bot
    
    Main objective: Kill General Kahyet
    Bonus objective: Kill 5 Rinkhal Monitors
    """
    
    # --- MAP IDs ---
    Outpost_Map_ID = 492
    Mission_Map_ID = 492
    
    # --- NPC CONFIGURATION ---
    NPC_Position = (2299, 792)
    NPC_Name = "Mission Giver"
    Dialog_Sequence = [0x18]  # Start mission
    
    # --- ENEMY NAMES ---
    Enemy_Ironfist_Envoy = "Ironfist"  # Partial match for "Ironfist's Envoy"
    Enemy_Rinkhal_Monitor = "Rinkhal"  # Partial match for "Rinkhal Monitor"
    Enemy_General_Kahyet = "General Kahyet"
    Enemy_Grasp_Of_Chaos = "Grasp of Chaos"
    
    # --- ITEM NAME ---
    Item_Corsair_Grab = "Corsair"  # Partial match for dropped item
    
    # --- PATH DATA ---
    # Phase 1: To Ironfist's Envoy (scan for Ironfist during this movement)
    Path_ToIronfist = [(3589, 15743), (410, 13195), (-2092, 13452)]
    
    # Phase 2: After cutscene, continue through mission (scan for Rinkhals)
    Path_Phase2 = [
        (-2796, 10592),  # First Rinkhal area
        (116, 9145),
        (4623, 5450),
        (5913, 3206),
        (7486, 2096),
        (8491, 6248),
        (12347, 9578),   # Second Rinkhal area
        (14760, 11141),  # Third Rinkhal area
        (11308, 8435),
        (8112, 5835),
        (7361, 127),
        (8609, -4374),
        (9588, -9794),
        (6858, -10126),
        (2295, -11729),
        (-842, -9353),
        (-3479, -4488),
        (-8620, 2435),   # Fourth Rinkhal area
        (-14281, 8476),  # Fifth Rinkhal area
        (-13124, 3900),
        (-6367, -438),
        (-1934, -6082),
        (1162, -12530),
        (-1926, -15995),
        (-4093, -15091),
    ]
    
    # Phase 3: Boss arena
    Path_ToBoss = [(-9241, -12077)]
    
    def GetInfo(self):
        return {
            "Name": "Blacktide Den",
            "Description": (
                "Infiltrate the corsair hideout, recover the stolen goods from Ironfist's Envoy, "
                "and eliminate General Kahyet to end the corsair threat."
            ),
            "Recommended_Builds": ["Any", "Tahlkora Required"],
            "HM_Tips": (
                "The Rinkhal Monitors hit hard - keep your party healed. "
                "General Kahyet and her Grasp of Chaos companions can spike quickly, "
                "so be ready with defensive skills when they turn hostile."
            )
        }

    def __init__(self):
        super().__init__()
        
        # Outpost handler with party requirements
        self.outpost_handler = OutpostHandler(
            requirements=PartyRequirements(
                min_size=2,
                required_heroes=["Tahlkora"]
            ),
            npc_position=self.NPC_Position,
            npc_name=self.NPC_Name,
            dialog_sequence=self.Dialog_Sequence,
            outpost_map_id=self.Outpost_Map_ID
        )
        
        # Path handlers - created on demand
        self._path_to_ironfist = None
        self._path_phase2 = None
        self._path_to_boss = None
        
        # Scanning movement handlers
        self._ironfist_scanner = None
        self._rinkhal_scanner = None
        
        # Item pickup handler
        self._item_pickup = None
        
        # Boss phase handlers
        self._boss_wait = None
        
        # Bonus tracker
        self.rinkhal_tracker = MultiKillTracker(self.Enemy_Rinkhal_Monitor, required_kills=5)
        
        # State flags
        self._ironfist_killed = False
        self._item_picked_up = False
        self._cutscene_wait_done = False
        self._boss_phase_logged = False

    def Reset(self):
        """Reset mission state."""
        super().Reset()
        
        # Reset handlers
        self.outpost_handler.Reset()
        
        self._path_to_ironfist = None
        self._path_phase2 = None
        self._path_to_boss = None
        self._ironfist_scanner = None
        self._rinkhal_scanner = None
        self._item_pickup = None
        self._boss_wait = None
        
        # Reset trackers
        self.rinkhal_tracker.Reset()
        self._ironfist_killed = False
        self._item_picked_up = False
        self._cutscene_wait_done = False
        self._boss_phase_logged = False

    def Execution_Routine(self, bot, logger):
        """Main execution routine."""
        # Skip if map loading
        if Map.IsMapLoading():
            return
        
        # Skip cinematics
        if Map.IsInCinematic():
            Map.SkipCinematic()
            return
        
        current_map = Map.GetMapID()
        if current_map == 0:
            return

        # --- CHECK FOR MISSION COMPLETION FIRST ---
        if self.mission_tracker.IsMissionStarted():
            if self.mission_tracker.Update(logger):
                bot.is_running = False
                return
            
            # If we're in an outpost after mission started = mission completed
            if self.IsInOutpost():
                logger.Add("Mission Complete!", (0, 1, 0, 1), prefix="[Victory]")
                bot.is_running = False
                return

        # --- OUTPOST PHASE ---
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
            logger.Add("Go to Blacktide Den to start.", (1, 0.5, 0, 1))
        bot.is_running = False

    def ExecuteMissionLogic(self, bot, logger):
        """Mission instance logic."""
        
        # ===== PHASE 1: Move to Ironfist while scanning for him =====
        if self.step == 3:
            if self._ironfist_scanner is None:
                logger.Add("Infiltrating corsair base... Hunting Ironfist's Envoy!", (0, 1, 1, 1), prefix="[Mission]")
                self._path_to_ironfist = Routines.Movement.PathHandler(self.Path_ToIronfist)
                self._ironfist_scanner = ScanWhileMoving(
                    path_handler=self._path_to_ironfist,
                    target_enemy_name=self.Enemy_Ironfist_Envoy,
                    combat_handler=self.combat_handler,
                    navigation=self.nav,
                    scan_distance=2000,
                    kill_once=True
                )
            
            result = self._ironfist_scanner.Execute(logger)
            
            if result == "enemy_killed":
                self._ironfist_killed = True
                # Continue moving to complete path
            
            if result == "path_complete":
                if self._ironfist_killed:
                    logger.Add("Ironfist's Envoy eliminated!", (0, 1, 0, 1))
                    self.step = 4
                    self.sub_state = 0
                else:
                    # Didn't find Ironfist on the way, he might already be dead
                    logger.Add("Reached destination. Ironfist may already be dead.", (1, 1, 0, 1), prefix="[Warn]")
                    self.step = 4
                    self.sub_state = 0
        
        # ===== PHASE 2: Pick up Corsair Grab =====
        elif self.step == 4:
            if self._item_pickup is None:
                logger.Add("Looking for dropped loot...", (0, 1, 1, 1))
                self._item_pickup = ItemPickupState(
                    self.Item_Corsair_Grab,
                    max_distance=2000,
                    timeout_ms=8000
                )
            
            result = self._item_pickup.Execute(logger)
            
            if result == "success":
                self._item_picked_up = True
                self._item_pickup = None
                self.step = 5
                self.sub_state = 0
            elif result == "failed":
                # Continue anyway
                logger.Add("Continuing without item pickup...", (1, 1, 0, 1), prefix="[Warn]")
                self._item_pickup = None
                self.step = 5
                self.sub_state = 0
        
        # ===== PHASE 3: Brief wait for cutscene =====
        elif self.step == 5:
            if not self._cutscene_wait_done:
                if self.timer.HasElapsed(2000):
                    self._cutscene_wait_done = True
                    logger.Add("Continuing mission... Hunting Rinkhal Monitors for bonus!", (0, 1, 1, 1), prefix="[Mission]")
                    self.step = 6
                    self.sub_state = 0
        
        # ===== PHASE 4: Main mission path with Rinkhal scanning =====
        elif self.step == 6:
            if self._rinkhal_scanner is None:
                self._path_phase2 = Routines.Movement.PathHandler(self.Path_Phase2)
                self._rinkhal_scanner = ScanWhileMovingMulti(
                    path_handler=self._path_phase2,
                    target_enemy_name=self.Enemy_Rinkhal_Monitor,
                    combat_handler=self.combat_handler,
                    navigation=self.nav,
                    kill_tracker=self.rinkhal_tracker,
                    scan_distance=2000
                )
            
            result = self._rinkhal_scanner.Execute(logger)
            
            if result == "path_complete":
                # Log bonus status
                if self.rinkhal_tracker.IsComplete():
                    logger.Add("BONUS COMPLETE: All Rinkhal Monitors killed!", (0, 1, 0, 1), prefix="[Bonus]")
                else:
                    progress = self.rinkhal_tracker.GetProgress()
                    logger.Add(f"Bonus progress: {progress} Rinkhal Monitors", (1, 1, 0, 1), prefix="[Bonus]")
                
                self.step = 7
                self.sub_state = 0
        
        # ===== PHASE 5: Move to boss arena =====
        elif self.step == 7:
            if self._path_to_boss is None:
                logger.Add("Approaching General Kahyet...", (1, 0.5, 0, 1), prefix="[Boss]")
                self._path_to_boss = Routines.Movement.PathHandler(self.Path_ToBoss)
            
            if self.nav.Execute(self._path_to_boss, logger):
                self.step = 8
                self.sub_state = 0
        
        # ===== PHASE 6: Wait for General Kahyet to turn hostile =====
        elif self.step == 8:
            if not self._boss_phase_logged:
                logger.Add("Waiting for General Kahyet to reveal herself...", (1, 0.5, 0, 1))
                self._boss_phase_logged = True
                self._boss_wait = WaitForHostileState(
                    self.Enemy_General_Kahyet,
                    max_distance=3000,
                    timeout_ms=120000
                )
            
            result = self._boss_wait.Execute(logger)
            
            if result == "hostile":
                self.step = 9
                self.sub_state = 0
            elif result == "timeout":
                # Check if boss is already hostile
                boss_id = EnemyFinder.FindEnemyByName(self.Enemy_General_Kahyet, 5000)
                if boss_id != 0:
                    self.step = 9
                    self.sub_state = 0
                else:
                    logger.Add("Boss not appearing. Check your position.", (1, 0, 0, 1), prefix="[Error]")
        
        # ===== PHASE 7: Kill General Kahyet and Grasp of Chaos =====
        elif self.step == 9:
            self._ExecuteBossFight(bot, logger)

    def _ExecuteBossFight(self, bot, logger):
        """Execute the boss fight against Kahyet and Grasp of Chaos."""
        if self.sub_state == 0:
            logger.Add("Engaging General Kahyet and her minions!", (1, 0, 0, 1), prefix="[BOSS]")
            self.sub_state = 1
        
        # Find priority targets
        # Priority: General Kahyet > Grasp of Chaos > other enemies
        boss_id = EnemyFinder.FindEnemyByName(self.Enemy_General_Kahyet, 3000, alive_only=True)
        grasp_id = EnemyFinder.FindEnemyByName(self.Enemy_Grasp_Of_Chaos, 3000, alive_only=True)
        
        if boss_id != 0:
            # Focus on boss
            self.combat_handler.Execute(target_agent_id=boss_id)
        elif grasp_id != 0:
            # Kill remaining Grasp of Chaos
            self.combat_handler.Execute(target_agent_id=grasp_id)
        else:
            # All main targets dead
            enemies = self.nav.GetNearbyEnemies()
            if enemies:
                # Clean up remaining enemies
                self.combat_handler.Execute(target_agent_id=enemies[0])
            else:
                # No enemies left - mission should end soon
                if self.sub_state != 2:
                    logger.Add("All enemies defeated! Awaiting mission completion...", (0, 1, 0, 1))
                    self.sub_state = 2
