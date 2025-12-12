"""
InteractionUtils.py - Interaction utilities for ZeroToHero missions.

Provides:
- Bundle (environmental item) handling
- Gadget interaction state machines
- NPC interaction helpers
- Enemy hunting/killing state machines
- Dropped item pickup
"""

from Py4GWCoreLib import *
from .AgentUtils import AgentFinder


class BundleHandler:
    """
    Handles picking up and using environmental items (bundles) like oil, torches, etc.
    """
    
    # Weapon types that indicate player is holding a bundle
    BUNDLE_TYPE_NAMES = ["Bundle", "Item", "Environmental", "Unknown", ""]
    
    @staticmethod
    def IsHoldingBundle():
        """
        Check if the player is currently holding a bundle item.
        
        Returns:
            bool: True if holding a bundle
        """
        try:
            agent_id = Player.GetAgentID()
            weapon_type_id, weapon_type_name = Agent.GetWeaponType(agent_id)
            
            # Bundle detection
            if weapon_type_name in BundleHandler.BUNDLE_TYPE_NAMES:
                return True
            if weapon_type_id == 0:
                return True
            
            return False
        except Exception:
            return False
    
    @staticmethod
    def DropBundle():
        """
        Drop the currently held bundle.
        
        Returns:
            bool: True if drop command was sent
        """
        try:
            if BundleHandler.IsHoldingBundle():
                Player.DropBundle()
                return True
            return False
        except Exception:
            return False


class BundlePickupState:
    """
    State machine for picking up a bundle item.
    
    Usage:
        pickup = BundlePickupState(gadget_x, gadget_y)
        
        # In your execution loop:
        result = pickup.Execute(logger)
        if result == "success":
            # Got the item!
        elif result == "failed":
            # Couldn't get it
        # else: still working ("searching", "interacting", "waiting")
    """
    
    STATE_SEARCH = 0
    STATE_INTERACT = 1
    STATE_WAIT = 2
    STATE_VERIFY = 3
    
    def __init__(self, gadget_x, gadget_y, max_distance=300, max_retries=3):
        """
        Args:
            gadget_x (float): X coordinate of the bundle
            gadget_y (float): Y coordinate of the bundle
            max_distance (float): Search radius
            max_retries (int): Number of pickup attempts before failing
        """
        self.gadget_pos = (gadget_x, gadget_y)
        self.max_distance = max_distance
        self.max_retries = max_retries
        
        self._state = self.STATE_SEARCH
        self._timer = Timer()
        self._timer.Start()
        self._retries = 0
        self._gadget_id = 0
    
    def Reset(self):
        """Reset the pickup state."""
        self._state = self.STATE_SEARCH
        self._timer.Reset()
        self._retries = 0
        self._gadget_id = 0
    
    def Execute(self, logger=None):
        """
        Execute one tick of the pickup state machine.
        
        Returns:
            str: "searching", "interacting", "waiting", "success", or "failed"
        """
        if self._state == self.STATE_SEARCH:
            # Find the gadget
            gadget_id = AgentFinder.FindNearestGadget(
                self.gadget_pos[0], 
                self.gadget_pos[1], 
                self.max_distance
            )
            
            if gadget_id == 0:
                # Silent search - only log after long delay
                if self._timer.HasElapsed(5000):
                    if logger:
                        logger.Add("Searching for item...", (1, 1, 0, 0.7))
                    self._timer.Reset()
                return "searching"
            
            self._gadget_id = gadget_id
            self._state = self.STATE_INTERACT
            self._timer.Reset()
            return "interacting"
        
        elif self._state == self.STATE_INTERACT:
            # Interact with the gadget (no log - action speaks for itself)
            Player.Interact(self._gadget_id)
            self._state = self.STATE_WAIT
            self._timer.Reset()
            return "interacting"
        
        elif self._state == self.STATE_WAIT:
            # Wait for pickup animation
            if self._timer.HasElapsed(1500):
                self._state = self.STATE_VERIFY
                self._timer.Reset()
            return "waiting"
        
        elif self._state == self.STATE_VERIFY:
            # Check if we're holding the bundle
            if BundleHandler.IsHoldingBundle():
                return "success"
            
            # Retry if not holding
            self._retries += 1
            if self._retries >= self.max_retries:
                if logger:
                    logger.Add("Failed to pick up item.", (1, 0, 0, 1), prefix="[Error]")
                return "failed"
            
            self._state = self.STATE_SEARCH
            self._timer.Reset()
            return "searching"
        
        return "searching"


class GadgetInteractionState:
    """
    State machine for interacting with a gadget (lever, catapult, etc.)
    
    Usage:
        interact = GadgetInteractionState(catapult_x, catapult_y, wait_ms=2000)
        
        # In your execution loop:
        result = interact.Execute(logger)
        if result == "complete":
            # Interaction done!
    """
    
    STATE_SEARCH = 0
    STATE_INTERACT = 1
    STATE_WAIT = 2
    
    def __init__(self, gadget_x, gadget_y, wait_ms=1500, max_distance=300):
        """
        Args:
            gadget_x (float): X coordinate of the gadget
            gadget_y (float): Y coordinate of the gadget
            wait_ms (int): Time to wait after interaction (ms)
            max_distance (float): Search radius
        """
        self.gadget_pos = (gadget_x, gadget_y)
        self.wait_ms = wait_ms
        self.max_distance = max_distance
        
        self._state = self.STATE_SEARCH
        self._timer = Timer()
        self._timer.Start()
        self._log_timer = Timer()
        self._log_timer.Start()
        self._gadget_id = 0
    
    def Reset(self):
        """Reset the interaction state."""
        self._state = self.STATE_SEARCH
        self._timer.Reset()
        self._log_timer.Reset()
        self._gadget_id = 0
    
    def Execute(self, logger=None, log_msg="Interacting"):
        """
        Execute one tick of the interaction state machine.
        
        Returns:
            str: "searching", "interacting", "waiting", or "complete"
        """
        if self._state == self.STATE_SEARCH:
            gadget_id = AgentFinder.FindNearestGadget(
                self.gadget_pos[0],
                self.gadget_pos[1],
                self.max_distance
            )
            
            if gadget_id == 0:
                # Silent search - only log after long delay
                if self._log_timer.HasElapsed(5000):
                    if logger:
                        logger.Add("Searching for gadget...", (1, 1, 0, 0.7))
                    self._log_timer.Reset()
                return "searching"
            
            self._gadget_id = gadget_id
            self._state = self.STATE_INTERACT
            return "interacting"
        
        elif self._state == self.STATE_INTERACT:
            # Log the action message once
            if logger and log_msg:
                logger.Add(f"{log_msg}...", (0, 1, 1, 1))
            Player.Interact(self._gadget_id)
            self._timer.Reset()
            self._state = self.STATE_WAIT
            return "interacting"
        
        elif self._state == self.STATE_WAIT:
            if self._timer.HasElapsed(self.wait_ms):
                return "complete"
            return "waiting"
        
        return "searching"


class NPCInteractionHelper:
    """
    Helper for NPC interactions (move to, target, interact).
    """
    
    @staticmethod
    def MoveToAgent(agent_id, min_distance=250, logger=None):
        """
        Move toward an agent until within min_distance.
        
        Args:
            agent_id (int): Agent to move toward
            min_distance (float): Stop distance
            logger: Optional logger
            
        Returns:
            bool: True if within range
        """
        if not Agent.IsValid(agent_id):
            return False
        
        player_pos = Player.GetXY()
        agent_pos = Agent.GetXY(agent_id)
        distance = Utils.Distance(player_pos, agent_pos)
        
        if distance <= min_distance:
            return True
        
        Player.Move(agent_pos[0], agent_pos[1])
        return False
    
    @staticmethod
    def TargetAndInteract(agent_id):
        """
        Target an agent and interact with it.
        
        Args:
            agent_id (int): Agent to interact with
            
        Returns:
            bool: True if interaction initiated
        """
        if not Agent.IsValid(agent_id):
            return False
        
        Player.ChangeTarget(agent_id)
        Player.Interact(agent_id)
        return True
    
    @staticmethod
    def SendDialog(dialog_id):
        """
        Send a dialog response.
        
        Args:
            dialog_id (int): Dialog ID to send
        """
        Player.SendDialog(dialog_id)


class EnemyFinder:
    """
    Utility class for finding enemies by name or other criteria.
    """
    
    @staticmethod
    def FindEnemyByName(name, max_distance=5000, alive_only=True):
        """
        Find an enemy by name within range.
        
        Args:
            name (str): Name (or partial name) to search for
            max_distance (float): Maximum search radius
            alive_only (bool): Only return alive enemies
            
        Returns:
            int: Agent ID if found, 0 otherwise
        """
        try:
            player_pos = Player.GetXY()
            enemies = AgentArray.GetEnemyArray()
            enemies = AgentArray.Filter.ByDistance(enemies, player_pos, max_distance)
            
            if alive_only:
                enemies = AgentArray.Filter.ByCondition(enemies, lambda id: Agent.IsAlive(id))
            
            for agent_id in enemies:
                try:
                    if not Agent.IsValid(agent_id):
                        continue
                    agent_name = Agent.GetName(agent_id)
                    if name.lower() in agent_name.lower():
                        return agent_id
                except Exception:
                    continue
            
            return 0
        except Exception:
            return 0
    
    @staticmethod
    def FindAllEnemiesByName(name, max_distance=5000, alive_only=True):
        """
        Find all enemies matching a name within range.
        
        Args:
            name (str): Name (or partial name) to search for
            max_distance (float): Maximum search radius
            alive_only (bool): Only return alive enemies
            
        Returns:
            list: List of matching agent IDs
        """
        result = []
        try:
            player_pos = Player.GetXY()
            enemies = AgentArray.GetEnemyArray()
            enemies = AgentArray.Filter.ByDistance(enemies, player_pos, max_distance)
            
            if alive_only:
                enemies = AgentArray.Filter.ByCondition(enemies, lambda id: Agent.IsAlive(id))
            
            for agent_id in enemies:
                try:
                    if not Agent.IsValid(agent_id):
                        continue
                    agent_name = Agent.GetName(agent_id)
                    if name.lower() in agent_name.lower():
                        result.append(agent_id)
                except Exception:
                    continue
            
            return result
        except Exception:
            return []
    
    @staticmethod
    def IsEnemyDead(agent_id):
        """
        Check if a specific enemy is dead.
        
        Args:
            agent_id (int): Agent ID to check
            
        Returns:
            bool: True if dead or invalid
        """
        if not Agent.IsValid(agent_id):
            return True
        return Agent.IsDead(agent_id)
    
    @staticmethod
    def CountAliveEnemiesByName(name, max_distance=5000):
        """
        Count how many alive enemies match a name.
        
        Args:
            name (str): Name to search for
            max_distance (float): Search radius
            
        Returns:
            int: Count of matching alive enemies
        """
        enemies = EnemyFinder.FindAllEnemiesByName(name, max_distance, alive_only=True)
        return len(enemies)


class TargetedKillState:
    """
    State machine for finding and killing a specific enemy by name.
    
    Usage:
        kill_state = TargetedKillState("Ironfist's Envoy")
        
        # In your execution loop:
        result = kill_state.Execute(combat_handler, logger)
        if result == "complete":
            # Enemy killed!
        elif result == "failed":
            # Could not find/kill enemy
    """
    
    STATE_SEARCH = 0
    STATE_ENGAGE = 1
    STATE_FIGHTING = 2
    STATE_VERIFY = 3
    
    def __init__(self, enemy_name, max_search_distance=2500, search_timeout_ms=30000):
        """
        Args:
            enemy_name (str): Name of the enemy to kill
            max_search_distance (float): Search radius for the enemy
            search_timeout_ms (int): How long to search before failing
        """
        self.enemy_name = enemy_name
        self.max_search_distance = max_search_distance
        self.search_timeout_ms = search_timeout_ms
        
        self._state = self.STATE_SEARCH
        self._target_id = 0
        self._timer = Timer()
        self._timer.Start()
        self._search_timer = Timer()
        self._search_timer.Start()
        self._logged_search = False
        self._logged_engage = False
    
    def Reset(self):
        """Reset the kill state."""
        self._state = self.STATE_SEARCH
        self._target_id = 0
        self._timer.Reset()
        self._search_timer.Reset()
        self._logged_search = False
        self._logged_engage = False
    
    def Execute(self, combat_handler, logger=None):
        """
        Execute one tick of the kill state machine.
        
        Args:
            combat_handler: CombatHandler instance for combat
            logger: Optional logger for status messages
            
        Returns:
            str: "searching", "engaging", "fighting", "complete", or "failed"
        """
        if self._state == self.STATE_SEARCH:
            # Search for the enemy
            enemy_id = EnemyFinder.FindEnemyByName(
                self.enemy_name,
                self.max_search_distance,
                alive_only=True
            )
            
            if enemy_id == 0:
                # Check timeout
                if self._search_timer.HasElapsed(self.search_timeout_ms):
                    if logger:
                        logger.Add(f"Could not find {self.enemy_name}", (1, 0.5, 0, 1), prefix="[Warn]")
                    return "failed"
                
                # Log search periodically
                if not self._logged_search and self._timer.HasElapsed(3000):
                    if logger:
                        logger.Add(f"Searching for {self.enemy_name}...", (1, 1, 0, 1))
                    self._logged_search = True
                
                return "searching"
            
            self._target_id = enemy_id
            self._state = self.STATE_ENGAGE
            self._timer.Reset()
            return "engaging"
        
        elif self._state == self.STATE_ENGAGE:
            # Target and engage the enemy
            if not self._logged_engage:
                if logger:
                    logger.Add(f"Engaging {self.enemy_name}!", (1, 0.5, 0, 1), prefix="[Combat]")
                self._logged_engage = True
            
            Player.ChangeTarget(self._target_id)
            self._state = self.STATE_FIGHTING
            self._timer.Reset()
            return "engaging"
        
        elif self._state == self.STATE_FIGHTING:
            # Check if target is dead
            if EnemyFinder.IsEnemyDead(self._target_id):
                self._state = self.STATE_VERIFY
                self._timer.Reset()
                return "fighting"
            
            # Keep fighting
            if combat_handler:
                combat_handler.Execute(target_agent_id=self._target_id)
            
            return "fighting"
        
        elif self._state == self.STATE_VERIFY:
            # Brief delay to ensure kill registered
            if self._timer.HasElapsed(500):
                if logger:
                    logger.Add(f"{self.enemy_name} killed!", (0, 1, 0, 1), prefix="[Kill]")
                return "complete"
            return "fighting"
        
        return "searching"


class ItemPickupState:
    """
    State machine for picking up a dropped item by name.
    
    Usage:
        pickup = ItemPickupState("Corsair Grab")
        
        # In your execution loop:
        result = pickup.Execute(logger)
        if result == "success":
            # Item picked up!
    """
    
    STATE_SEARCH = 0
    STATE_MOVE = 1
    STATE_PICKUP = 2
    STATE_WAIT = 3
    STATE_VERIFY = 4
    
    def __init__(self, item_name, max_distance=2000, pickup_distance=150, timeout_ms=15000):
        """
        Args:
            item_name (str): Name of the item to pick up
            max_distance (float): Search radius
            pickup_distance (float): Distance at which to attempt pickup
            timeout_ms (int): Search timeout
        """
        self.item_name = item_name
        self.max_distance = max_distance
        self.pickup_distance = pickup_distance
        self.timeout_ms = timeout_ms
        
        self._state = self.STATE_SEARCH
        self._item_agent_id = 0
        self._timer = Timer()
        self._timer.Start()
        self._search_timer = Timer()
        self._search_timer.Start()
        self._logged = False
    
    def Reset(self):
        """Reset the pickup state."""
        self._state = self.STATE_SEARCH
        self._item_agent_id = 0
        self._timer.Reset()
        self._search_timer.Reset()
        self._logged = False
    
    def _FindItemByName(self):
        """Find a dropped item by name."""
        try:
            player_pos = Player.GetXY()
            items = AgentArray.GetItemArray()
            items = AgentArray.Filter.ByDistance(items, player_pos, self.max_distance)
            
            for item_agent_id in items:
                try:
                    if not Agent.IsValid(item_agent_id):
                        continue
                    
                    # Get item info - items on ground are agents
                    item_agent = Agent.GetItemAgent(item_agent_id)
                    if item_agent:
                        # Try to get item name via Item class
                        item_id = item_agent.item_id
                        if item_id > 0:
                            Item.RequestName(item_id)
                            if Item.IsNameReady(item_id):
                                name = Item.GetName(item_id)
                                if self.item_name.lower() in name.lower():
                                    return item_agent_id
                except Exception:
                    continue
            
            return 0
        except Exception:
            return 0
    
    def Execute(self, logger=None):
        """
        Execute one tick of the item pickup state machine.
        
        Returns:
            str: "searching", "moving", "picking_up", "success", or "failed"
        """
        if self._state == self.STATE_SEARCH:
            item_id = self._FindItemByName()
            
            if item_id == 0:
                if self._search_timer.HasElapsed(self.timeout_ms):
                    if logger:
                        logger.Add(f"Could not find {self.item_name}", (1, 0.5, 0, 1), prefix="[Warn]")
                    return "failed"
                
                if not self._logged and self._timer.HasElapsed(2000):
                    if logger:
                        logger.Add(f"Looking for {self.item_name}...", (1, 1, 0, 1))
                    self._logged = True
                
                return "searching"
            
            self._item_agent_id = item_id
            self._state = self.STATE_MOVE
            self._timer.Reset()
            return "moving"
        
        elif self._state == self.STATE_MOVE:
            if not Agent.IsValid(self._item_agent_id):
                self._state = self.STATE_SEARCH
                return "searching"
            
            player_pos = Player.GetXY()
            item_pos = Agent.GetXY(self._item_agent_id)
            distance = Utils.Distance(player_pos, item_pos)
            
            if distance <= self.pickup_distance:
                self._state = self.STATE_PICKUP
                self._timer.Reset()
                return "picking_up"
            
            # Move toward item
            if self._timer.HasElapsed(500):
                Player.Move(item_pos[0], item_pos[1])
                self._timer.Reset()
            
            return "moving"
        
        elif self._state == self.STATE_PICKUP:
            if logger:
                logger.Add(f"Picking up {self.item_name}...", (0, 1, 1, 1))
            Player.Interact(self._item_agent_id)
            self._state = self.STATE_WAIT
            self._timer.Reset()
            return "picking_up"
        
        elif self._state == self.STATE_WAIT:
            if self._timer.HasElapsed(1500):
                self._state = self.STATE_VERIFY
            return "picking_up"
        
        elif self._state == self.STATE_VERIFY:
            # Check if item is gone (picked up)
            if not Agent.IsValid(self._item_agent_id):
                if logger:
                    logger.Add(f"Picked up {self.item_name}!", (0, 1, 0, 1))
                return "success"
            
            # Item still there, try again
            self._state = self.STATE_PICKUP
            self._timer.Reset()
            return "picking_up"
        
        return "searching"


class WaitForHostileState:
    """
    State machine for waiting for an NPC to turn hostile.
    
    Usage:
        wait_state = WaitForHostileState("General Kahyet", position=(x, y))
        
        # In your execution loop:
        result = wait_state.Execute(logger)
        if result == "hostile":
            # NPC is now hostile, engage!
    """
    
    STATE_WAITING = 0
    STATE_HOSTILE = 1
    
    def __init__(self, npc_name, position=None, max_distance=2500, timeout_ms=120000):
        """
        Args:
            npc_name (str): Name of the NPC to watch
            position (tuple): Optional (x, y) position to wait at
            max_distance (float): Search radius
            timeout_ms (int): Maximum wait time
        """
        self.npc_name = npc_name
        self.position = position
        self.max_distance = max_distance
        self.timeout_ms = timeout_ms
        
        self._state = self.STATE_WAITING
        self._timer = Timer()
        self._timer.Start()
        self._log_timer = Timer()
        self._log_timer.Start()
        self._logged = False
    
    def Reset(self):
        """Reset the wait state."""
        self._state = self.STATE_WAITING
        self._timer.Reset()
        self._log_timer.Reset()
        self._logged = False
    
    def Execute(self, logger=None):
        """
        Execute one tick of the wait state machine.
        
        Returns:
            str: "waiting", "hostile", or "timeout"
        """
        if self._state == self.STATE_WAITING:
            # Check if NPC is now in enemy array
            enemy_id = EnemyFinder.FindEnemyByName(
                self.npc_name,
                self.max_distance,
                alive_only=True
            )
            
            if enemy_id != 0:
                if logger:
                    logger.Add(f"{self.npc_name} has turned hostile!", (1, 0.5, 0, 1), prefix="[Alert]")
                self._state = self.STATE_HOSTILE
                return "hostile"
            
            # Check timeout
            if self._timer.HasElapsed(self.timeout_ms):
                if logger:
                    logger.Add(f"Timeout waiting for {self.npc_name}", (1, 0, 0, 1), prefix="[Error]")
                return "timeout"
            
            # Log periodically
            if self._log_timer.HasElapsed(10000):
                if logger:
                    logger.Add(f"Waiting for {self.npc_name}...", (1, 1, 0, 1))
                self._log_timer.Reset()
            
            return "waiting"
        
        elif self._state == self.STATE_HOSTILE:
            return "hostile"
        
        return "waiting"


class MultiKillTracker:
    """
    Tracks killing multiple enemies of the same type (for bonus objectives).
    
    Usage:
        tracker = MultiKillTracker("Rinkhal Monitor", required_kills=5)
        
        # When you kill one:
        tracker.RegisterKill()
        
        # Check status:
        if tracker.IsComplete():
            # Bonus complete!
    """
    
    def __init__(self, enemy_name, required_kills):
        """
        Args:
            enemy_name (str): Name of enemies to track
            required_kills (int): Number needed for completion
        """
        self.enemy_name = enemy_name
        self.required_kills = required_kills
        self.current_kills = 0
    
    def Reset(self):
        """Reset kill count."""
        self.current_kills = 0
    
    def RegisterKill(self):
        """Register a kill."""
        self.current_kills += 1
    
    def GetKillCount(self):
        """Get current kill count."""
        return self.current_kills
    
    def GetRequiredKills(self):
        """Get required kills."""
        return self.required_kills
    
    def IsComplete(self):
        """Check if required kills reached."""
        return self.current_kills >= self.required_kills
    
    def GetProgress(self):
        """Get progress string."""
        return f"{self.current_kills}/{self.required_kills}"


class ScanWhileMoving:
    """
    State machine for moving along a path while scanning for specific enemies.
    When a target enemy is found, pauses movement to kill it, then continues.
    
    Usage:
        scanner = ScanWhileMoving(
            path_handler=my_path,
            target_enemy_name="Ironfist's Envoy",
            combat_handler=combat_handler,
            navigation=nav
        )
        
        # In your execution loop:
        result = scanner.Execute(logger)
        if result == "path_complete":
            # Reached destination
        elif result == "enemy_killed":
            # Killed the target enemy!
    """
    
    STATE_MOVING = 0
    STATE_ENGAGING = 1
    STATE_FIGHTING = 2
    STATE_KILL_VERIFIED = 3
    
    def __init__(self, path_handler, target_enemy_name, combat_handler, navigation,
                 scan_distance=1500, kill_once=True):
        """
        Args:
            path_handler: PathHandler with waypoints
            target_enemy_name (str): Name of enemy to scan for
            combat_handler: CombatHandler for combat
            navigation: MissionNavigation for movement
            scan_distance (float): How far to scan for the target
            kill_once (bool): If True, only kills first match then continues
        """
        self.path_handler = path_handler
        self.target_enemy_name = target_enemy_name
        self.combat_handler = combat_handler
        self.navigation = navigation
        self.scan_distance = scan_distance
        self.kill_once = kill_once
        
        self._state = self.STATE_MOVING
        self._target_id = 0
        self._target_killed = False
        self._logged_engage = False
        self._timer = Timer()
        self._timer.Start()
    
    def Reset(self):
        """Reset the scanner state."""
        self._state = self.STATE_MOVING
        self._target_id = 0
        self._target_killed = False
        self._logged_engage = False
        self._timer.Reset()
        self.path_handler.reset()
    
    def WasTargetKilled(self):
        """Check if the target enemy was killed during movement."""
        return self._target_killed
    
    def Execute(self, logger=None):
        """
        Execute one tick of movement with scanning.
        
        Returns:
            str: "moving", "fighting", "enemy_killed", or "path_complete"
        """
        # Always check if target enemy is nearby (unless already killed and kill_once)
        if not (self.kill_once and self._target_killed):
            if self._state == self.STATE_MOVING:
                target_id = EnemyFinder.FindEnemyByName(
                    self.target_enemy_name,
                    self.scan_distance,
                    alive_only=True
                )
                
                if target_id != 0:
                    self._target_id = target_id
                    self._state = self.STATE_ENGAGING
                    self._logged_engage = False
                    return "fighting"
        
        if self._state == self.STATE_MOVING:
            # Normal movement with combat handling
            if self.navigation.Execute(self.path_handler, logger):
                return "path_complete"
            return "moving"
        
        elif self._state == self.STATE_ENGAGING:
            if not self._logged_engage:
                if logger:
                    logger.Add(f"Found {self.target_enemy_name}! Engaging...", (1, 0.5, 0, 1), prefix="[Target]")
                self._logged_engage = True
            
            Player.ChangeTarget(self._target_id)
            self._state = self.STATE_FIGHTING
            self._timer.Reset()
            return "fighting"
        
        elif self._state == self.STATE_FIGHTING:
            # Check if target is dead
            if EnemyFinder.IsEnemyDead(self._target_id):
                self._state = self.STATE_KILL_VERIFIED
                self._timer.Reset()
                return "fighting"
            
            # Keep fighting the target
            if self.combat_handler:
                self.combat_handler.Execute(target_agent_id=self._target_id)
            
            return "fighting"
        
        elif self._state == self.STATE_KILL_VERIFIED:
            # Brief delay to confirm kill
            if self._timer.HasElapsed(500):
                self._target_killed = True
                if logger:
                    logger.Add(f"{self.target_enemy_name} killed!", (0, 1, 0, 1), prefix="[Kill]")
                
                # Return to moving
                self._state = self.STATE_MOVING
                self._target_id = 0
                return "enemy_killed"
            return "fighting"
        
        return "moving"


class ScanWhileMovingMulti:
    """
    Like ScanWhileMoving but tracks multiple kills of the same enemy type.
    Useful for bonus objectives like "Kill 5 Rinkhal Monitors".
    
    Usage:
        scanner = ScanWhileMovingMulti(
            path_handler=my_path,
            target_enemy_name="Rinkhal Monitor",
            combat_handler=combat_handler,
            navigation=nav,
            kill_tracker=my_tracker  # MultiKillTracker instance
        )
    """
    
    STATE_MOVING = 0
    STATE_ENGAGING = 1
    STATE_FIGHTING = 2
    STATE_KILL_VERIFIED = 3
    
    def __init__(self, path_handler, target_enemy_name, combat_handler, navigation,
                 kill_tracker=None, scan_distance=1500):
        """
        Args:
            path_handler: PathHandler with waypoints
            target_enemy_name (str): Name of enemy to scan for
            combat_handler: CombatHandler for combat
            navigation: MissionNavigation for movement
            kill_tracker (MultiKillTracker): Optional tracker for counting kills
            scan_distance (float): How far to scan for the target
        """
        self.path_handler = path_handler
        self.target_enemy_name = target_enemy_name
        self.combat_handler = combat_handler
        self.navigation = navigation
        self.kill_tracker = kill_tracker
        self.scan_distance = scan_distance
        
        self._state = self.STATE_MOVING
        self._target_id = 0
        self._killed_ids = set()  # Track killed enemy IDs to avoid re-targeting corpses
        self._logged_engage = False
        self._timer = Timer()
        self._timer.Start()
    
    def Reset(self):
        """Reset the scanner state."""
        self._state = self.STATE_MOVING
        self._target_id = 0
        self._killed_ids.clear()
        self._logged_engage = False
        self._timer.Reset()
        self.path_handler.reset()
    
    def GetKillCount(self):
        """Get number of kills if tracker is set."""
        if self.kill_tracker:
            return self.kill_tracker.GetKillCount()
        return len(self._killed_ids)
    
    def Execute(self, logger=None):
        """
        Execute one tick of movement with scanning.
        
        Returns:
            str: "moving", "fighting", "enemy_killed", or "path_complete"
        """
        # Scan for target enemies while moving
        if self._state == self.STATE_MOVING:
            # Find target enemies, excluding ones we've already killed
            all_targets = EnemyFinder.FindAllEnemiesByName(
                self.target_enemy_name,
                self.scan_distance,
                alive_only=True
            )
            
            # Filter out already killed
            valid_targets = [t for t in all_targets if t not in self._killed_ids]
            
            if valid_targets:
                self._target_id = valid_targets[0]
                self._state = self.STATE_ENGAGING
                self._logged_engage = False
                return "fighting"
        
        if self._state == self.STATE_MOVING:
            # Normal movement with combat handling
            if self.navigation.Execute(self.path_handler, logger):
                return "path_complete"
            return "moving"
        
        elif self._state == self.STATE_ENGAGING:
            if not self._logged_engage:
                if logger:
                    progress = ""
                    if self.kill_tracker:
                        progress = f" ({self.kill_tracker.GetProgress()})"
                    logger.Add(f"Found {self.target_enemy_name}!{progress} Engaging...", (1, 0.5, 0, 1), prefix="[Target]")
                self._logged_engage = True
            
            Player.ChangeTarget(self._target_id)
            self._state = self.STATE_FIGHTING
            self._timer.Reset()
            return "fighting"
        
        elif self._state == self.STATE_FIGHTING:
            # Check if target is dead
            if EnemyFinder.IsEnemyDead(self._target_id):
                self._state = self.STATE_KILL_VERIFIED
                self._timer.Reset()
                return "fighting"
            
            # Keep fighting the target
            if self.combat_handler:
                self.combat_handler.Execute(target_agent_id=self._target_id)
            
            return "fighting"
        
        elif self._state == self.STATE_KILL_VERIFIED:
            # Brief delay to confirm kill
            if self._timer.HasElapsed(500):
                self._killed_ids.add(self._target_id)
                
                if self.kill_tracker:
                    self.kill_tracker.RegisterKill()
                    progress = self.kill_tracker.GetProgress()
                    if logger:
                        logger.Add(f"{self.target_enemy_name} killed! ({progress})", (0, 1, 0, 1), prefix="[Kill]")
                else:
                    if logger:
                        logger.Add(f"{self.target_enemy_name} killed!", (0, 1, 0, 1), prefix="[Kill]")
                
                # Return to moving
                self._state = self.STATE_MOVING
                self._target_id = 0
                return "enemy_killed"
            return "fighting"
        
        return "moving"
