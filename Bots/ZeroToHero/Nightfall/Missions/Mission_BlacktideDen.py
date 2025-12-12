"""
Mission_BlacktideDen.py - Blacktide Den Mission Bot

Infiltrate the corsair base, recover the stolen goods, and eliminate the corsair threat.
Includes bonus objective: Kill 5 Rinkhal Monitors.
"""

from Py4GWCoreLib import *
from Bots.ZeroToHero.Shared.MissionContext import BaseMission, MissionContext
from Bots.ZeroToHero.Shared.PartyUtils import PartyRequirements
from Bots.ZeroToHero.Shared.OutpostHandler import OutpostHandler
from Bots.ZeroToHero.Shared.AgentUtils import AgentFinder
from Bots.ZeroToHero.Shared.InteractionUtils import (
    BundleHandler, 
    EnemyFinder,
    ItemFinder,
    ItemPickupState,
    WaitForHostileState,
    MultiKillTracker,
    ScanWhileMoving,
    ScanWhileMovingMulti,
    EscortNavigation
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
    Dialog_Sequence = [0x84]  # Start mission dialog
    
    # --- CAPTAIN BESUZ ---
    Captain_Besuz_Position = (4623, 5450)
    Captain_Besuz_Name = "Captain Besuz"
    
    # --- ENEMY NAMES ---
    Enemy_Ironfist_Envoy = "Ironfist"  # Partial match for "Ironfist's Envoy"
    Enemy_Rinkhal_Monitor = "Rinkhal"  # Partial match for "Rinkhal Monitor"
    Enemy_General_Kahyet = "General Kahyet"
    Enemy_Grasp_Of_Chaos = "Grasp of Chaos"
    
    # --- ITEM NAME ---
    Item_Corsair_Garb = "Corsair Garb"  # Dropped item name
    
    # --- PATH DATA ---
    # Phase 1: To Ironfist's Envoy (scan for Ironfist during this movement)
    Path_ToIronfist = [(3589, 15743), (410, 13195), (-2092, 13452)]
    
    # Position where Ironfist dies (approximately) - used for item search
    Ironfist_Death_Position = (-2092, 13452)
    
    # Phase 2a: After cutscene, to Captain Besuz (scan for Rinkhals)
    Path_ToCaptainBesuz = [
        (-2796, 10592),  # First Rinkhal area
        (116, 9145),
        (4623, 5450),    # Captain Besuz location
    ]
    
    # Phase 2b: After Captain Besuz, continue through mission (with escort)
    Path_AfterCaptainBesuz = [
        (4589, 5204),    # Avoid getting stuck after Besuz
        (4780, 4848),    # Avoid getting stuck after Besuz
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
            outpost_map_id=self.Outpost_Map_ID,
            dialog_wait_ms=2000,
            dialog_open_wait_ms=1500
        )
        
        # Path handlers - created on demand
        self._path_to_ironfist = None
        self._path_to_besuz = None
        self._path_after_besuz = None
        self._path_to_boss = None
        
        # Scanning movement handlers
        self._ironfist_scanner = None
        self._rinkhal_scanner_1 = None  # Before Besuz
        self._escort_nav = None          # After Besuz (with escort)
        
        # Item pickup handler
        self._item_pickup = None
        self._last_ironfist_pos = None
        
        # NPC interaction state
        self._besuz_npc_id = 0
        
        # Boss phase handlers
        self._boss_wait = None
        
        # Bonus tracker
        self.rinkhal_tracker = MultiKillTracker(self.Enemy_Rinkhal_Monitor, required_kills=5)
        
        # Track killed Rinkhals during escort phase
        self._escort_killed_rinkhals = set()
        
        # State flags
        self._ironfist_killed = False
        self._item_picked_up = False
        self._cutscene_wait_done = False
        self._besuz_talked = False
        self._boss_phase_logged = False

    def Reset(self):
        """Reset mission state."""
        super().Reset()
        
        # Reset handlers
        self.outpost_handler.Reset()
        
        self._path_to_ironfist = None
        self._path_to_besuz = None
        self._path_after_besuz = None
        self._path_to_boss = None
        self._ironfist_scanner = None
        self._rinkhal_scanner_1 = None
        self._escort_nav = None
        self._item_pickup = None
        self._boss_wait = None
        self._last_ironfist_pos = None
        
        # Reset NPC state
        self._besuz_npc_id = 0
        
        # Reset trackers
        self.rinkhal_tracker.Reset()
        self._escort_killed_rinkhals.clear()
        self._ironfist_killed = False
        self._item_picked_up = False
        self._cutscene_wait_done = False
        self._besuz_talked = False
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
                    scan_distance=2500,
                    kill_once=True
                )
            
            # Track Ironfist's position when found (for item pickup later)
            if self._ironfist_scanner._target_id != 0 and self._last_ironfist_pos is None:
                try:
                    if Agent.IsValid(self._ironfist_scanner._target_id):
                        self._last_ironfist_pos = Agent.GetXY(self._ironfist_scanner._target_id)
                except:
                    pass
            
            result = self._ironfist_scanner.Execute(logger)
            
            if result == "enemy_killed":
                self._ironfist_killed = True
                if self._last_ironfist_pos is None:
                    self._last_ironfist_pos = self.Ironfist_Death_Position
                logger.Add("Ironfist's Envoy eliminated!", (0, 1, 0, 1))
                self.step = 4
                self.sub_state = 0
                self.timer.Reset()
            
            if result == "path_complete":
                if self._ironfist_killed:
                    self.step = 4
                    self.sub_state = 0
                    self.timer.Reset()
                else:
                    logger.Add("Reached destination. Looking for dropped items...", (1, 1, 0, 1), prefix="[Warn]")
                    self._last_ironfist_pos = self.Ironfist_Death_Position
                    self.step = 4
                    self.sub_state = 0
                    self.timer.Reset()
        
        # ===== PHASE 2: Wait a moment then pick up Corsair Garb =====
        elif self.step == 4:
            if not self.timer.HasElapsed(2000):
                return
            
            if self._item_pickup is None:
                logger.Add("Searching for Corsair Garb...", (0, 1, 1, 1))
                search_pos = self._last_ironfist_pos or self.Ironfist_Death_Position
                self._item_pickup = ItemPickupState(
                    item_name=self.Item_Corsair_Garb,
                    near_position=search_pos,
                    max_distance=1500,
                    pickup_distance=200,
                    timeout_ms=20000
                )
            
            result = self._item_pickup.Execute(logger)
            
            if result == "success":
                self._item_picked_up = True
                self._item_pickup = None
                logger.Add("Got the Corsair Garb! Triggering cutscene...", (0, 1, 0, 1))
                self.step = 5
                self.sub_state = 0
                self.timer.Reset()
            elif result == "failed":
                logger.Add("Looking for any nearby item...", (1, 0.5, 0, 1), prefix="[Warn]")
                nearest_item = ItemFinder.FindNearestItem(max_distance=1500)
                if nearest_item != 0:
                    logger.Add("Found an item! Attempting pickup...", (1, 1, 0, 1))
                    self._item_pickup = ItemPickupState(
                        near_position=Agent.GetXY(nearest_item),
                        max_distance=500,
                        timeout_ms=10000
                    )
                else:
                    logger.Add("No items found. Continuing anyway...", (1, 0.5, 0, 1), prefix="[Warn]")
                    self._item_pickup = None
                    self.step = 5
                    self.sub_state = 0
                    self.timer.Reset()
        
        # ===== PHASE 3: Wait for cutscene to trigger =====
        elif self.step == 5:
            if not self._cutscene_wait_done:
                if self.timer.HasElapsed(3000):
                    self._cutscene_wait_done = True
                    logger.Add("Hunting Rinkhal Monitors on the way to Captain Besuz!", (0, 1, 1, 1), prefix="[Mission]")
                    self.step = 6
                    self.sub_state = 0
        
        # ===== PHASE 4: Path to Captain Besuz (scan for Rinkhals) =====
        elif self.step == 6:
            if self._rinkhal_scanner_1 is None:
                self._path_to_besuz = Routines.Movement.PathHandler(self.Path_ToCaptainBesuz)
                self._rinkhal_scanner_1 = ScanWhileMovingMulti(
                    path_handler=self._path_to_besuz,
                    target_enemy_name=self.Enemy_Rinkhal_Monitor,
                    combat_handler=self.combat_handler,
                    navigation=self.nav,
                    kill_tracker=self.rinkhal_tracker,
                    scan_distance=2500
                )
            
            result = self._rinkhal_scanner_1.Execute(logger)
            
            if result == "path_complete":
                logger.Add("Reached Captain Besuz's location.", (0, 1, 1, 1))
                self.step = 7
                self.sub_state = 0
                self.timer.Reset()
        
        # ===== PHASE 5: Talk to Captain Besuz =====
        elif self.step == 7:
            self._ExecuteCaptainBesuzInteraction(bot, logger)
        
        # ===== PHASE 6: Continue mission after Besuz WITH ESCORT =====
        elif self.step == 8:
            if self._escort_nav is None:
                logger.Add("Following Captain Besuz... Hunting Rinkhal Monitors!", (0, 1, 1, 1), prefix="[Mission]")
                self._path_after_besuz = Routines.Movement.PathHandler(self.Path_AfterCaptainBesuz)
                self._escort_nav = EscortNavigation(
                    path_handler=self._path_after_besuz,
                    escort_name=self.Captain_Besuz_Name,
                    combat_handler=self.combat_handler,
                    navigation=self.nav,
                    max_escort_distance=1500,
                    escort_search_distance=5000
                )
            
            # Also scan for Rinkhals while escorting
            rinkhal_id = EnemyFinder.FindEnemyByName(self.Enemy_Rinkhal_Monitor, 2500, alive_only=True)
            if rinkhal_id != 0 and rinkhal_id not in self._escort_killed_rinkhals:
                # Found a Rinkhal - kill it
                self.combat_handler.Execute(target_agent_id=rinkhal_id)
                if EnemyFinder.IsEnemyDead(rinkhal_id):
                    self._escort_killed_rinkhals.add(rinkhal_id)
                    self.rinkhal_tracker.RegisterKill()
                    logger.Add(f"Rinkhal Monitor killed! ({self.rinkhal_tracker.GetProgress()})", (0, 1, 0, 1), prefix="[Kill]")
                return
            
            result = self._escort_nav.Execute(logger)
            
            if result == "path_complete":
                # Log bonus status
                if self.rinkhal_tracker.IsComplete():
                    logger.Add("BONUS COMPLETE: All Rinkhal Monitors killed!", (0, 1, 0, 1), prefix="[Bonus]")
                else:
                    progress = self.rinkhal_tracker.GetProgress()
                    logger.Add(f"Bonus progress: {progress} Rinkhal Monitors", (1, 1, 0, 1), prefix="[Bonus]")
                
                self.step = 9
                self.sub_state = 0
        
        # ===== PHASE 7: Move to boss arena =====
        elif self.step == 9:
            if self._path_to_boss is None:
                logger.Add("Approaching General Kahyet...", (1, 0.5, 0, 1), prefix="[Boss]")
                self._path_to_boss = Routines.Movement.PathHandler(self.Path_ToBoss)
            
            if self.nav.Execute(self._path_to_boss, logger):
                self.step = 10
                self.sub_state = 0
        
        # ===== PHASE 8: Wait for General Kahyet to turn hostile =====
        elif self.step == 10:
            if not self._boss_phase_logged:
                logger.Add("Waiting for General Kahyet to reveal herself...", (1, 0.5, 0, 1))
                self._boss_phase_logged = True
                self._boss_wait = WaitForHostileState(
                    self.Enemy_General_Kahyet,
                    max_distance=3500,
                    timeout_ms=120000
                )
            
            result = self._boss_wait.Execute(logger)
            
            if result == "hostile":
                self.step = 11
                self.sub_state = 0
            elif result == "timeout":
                boss_id = EnemyFinder.FindEnemyByName(self.Enemy_General_Kahyet, 5000)
                if boss_id != 0:
                    self.step = 11
                    self.sub_state = 0
                else:
                    logger.Add("Boss not appearing. Check your position.", (1, 0, 0, 1), prefix="[Error]")
        
        # ===== PHASE 9: Kill General Kahyet and Grasp of Chaos =====
        elif self.step == 11:
            self._ExecuteBossFight(bot, logger)

    def _ExecuteCaptainBesuzInteraction(self, bot, logger):
        """Handle talking to Captain Besuz to continue the mission."""
        
        # Sub-state 0: Find Captain Besuz
        if self.sub_state == 0:
            self._besuz_npc_id = AgentFinder.FindNearestNPC(
                self.Captain_Besuz_Position[0],
                self.Captain_Besuz_Position[1],
                max_distance=800,
                name_filter=self.Captain_Besuz_Name
            )
            
            if self._besuz_npc_id == 0:
                # Try without name filter
                self._besuz_npc_id = AgentFinder.FindNearestNPC(
                    self.Captain_Besuz_Position[0],
                    self.Captain_Besuz_Position[1],
                    max_distance=800
                )
            
            if self._besuz_npc_id != 0:
                logger.Add(f"Found {self.Captain_Besuz_Name}!", (0, 1, 1, 1))
                self.sub_state = 1
                self.timer.Reset()
            else:
                # Keep searching
                if self.timer.HasElapsed(5000):
                    logger.Add(f"Searching for {self.Captain_Besuz_Name}...", (1, 1, 0, 1))
                    self.timer.Reset()
        
        # Sub-state 1: Move to Captain Besuz
        elif self.sub_state == 1:
            if not Agent.IsValid(self._besuz_npc_id):
                self.sub_state = 0
                return
            
            player_pos = Player.GetXY()
            npc_pos = Agent.GetXY(self._besuz_npc_id)
            distance = Utils.Distance(player_pos, npc_pos)
            
            if distance > 250:
                if self.timer.HasElapsed(500):
                    Player.Move(npc_pos[0], npc_pos[1])
                    self.timer.Reset()
            else:
                # Close enough - stop and target
                Player.Move(player_pos[0], player_pos[1])  # Stop moving
                self.sub_state = 2
                self.timer.Reset()
        
        # Sub-state 2: Target NPC
        elif self.sub_state == 2:
            if self.timer.HasElapsed(300):
                Player.ChangeTarget(self._besuz_npc_id)
                self.sub_state = 3
                self.timer.Reset()
        
        # Sub-state 3: Wait for target, then interact
        elif self.sub_state == 3:
            if self.timer.HasElapsed(500):
                logger.Add(f"Talking to {self.Captain_Besuz_Name}...", (0, 1, 1, 1))
                Player.Interact(self._besuz_npc_id)
                self.sub_state = 4
                self.timer.Reset()
        
        # Sub-state 4: Wait after interaction, then done (no dialog needed)
        elif self.sub_state == 4:
            if self.timer.HasElapsed(1500):
                logger.Add(f"Finished talking to {self.Captain_Besuz_Name}. Continuing mission!", (0, 1, 0, 1))
                self._besuz_talked = True
                self.step = 8
                self.sub_state = 0

    def _ExecuteBossFight(self, bot, logger):
        """Execute the boss fight against Kahyet and Grasp of Chaos."""
        if self.sub_state == 0:
            logger.Add("Engaging General Kahyet and her minions!", (1, 0, 0, 1), prefix="[BOSS]")
            self.sub_state = 1
        
        # Find priority targets
        boss_id = EnemyFinder.FindEnemyByName(self.Enemy_General_Kahyet, 3000, alive_only=True)
        grasp_id = EnemyFinder.FindEnemyByName(self.Enemy_Grasp_Of_Chaos, 3000, alive_only=True)
        
        if boss_id != 0:
            self.combat_handler.Execute(target_agent_id=boss_id)
        elif grasp_id != 0:
            self.combat_handler.Execute(target_agent_id=grasp_id)
        else:
            enemies = self.nav.GetNearbyEnemies()
            if enemies:
                self.combat_handler.Execute(target_agent_id=enemies[0])
            else:
                if self.sub_state != 2:
                    logger.Add("All enemies defeated! Awaiting mission completion...", (0, 1, 0, 1))
                    self.sub_state = 2
