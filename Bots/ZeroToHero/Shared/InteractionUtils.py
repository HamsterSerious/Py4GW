"""
InteractionUtils.py - Interaction utilities for ZeroToHero missions.

Provides:
- Bundle (environmental item) handling
- Gadget interaction state machines
- NPC interaction helpers
- Enemy hunting/killing state machines
- Dropped item pickup (by ModelID or position)
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
                    if agent_name and name.lower() in agent_name.lower():
                        return agent_id
                except Exception:
                    continue
            
            return 0
        except Exception:
            return 0
    
    @staticmethod
    def FindEnemyByModelID(model_id, max_distance=5000, alive_only=True):
        """
        Find an enemy by ModelID within range.
        
        Args:
            model_id (int): ModelID to search for
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
                    living = Agent.GetLivingAgent(agent_id)
                    if living and living.player_number == model_id:
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
                    if agent_name and name.lower() in agent_name.lower():
                        result.append(agent_id)
                except Exception:
                    continue
            
            return result
        except Exception:
            return []
    
    @staticmethod
    def FindNearestEnemy(max_distance=1200, alive_only=True):
        """
        Find the nearest enemy within range (regardless of name).
        
        Args:
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
            
            enemies = AgentArray.Sort.ByDistance(enemies, player_pos)
            return enemies[0] if enemies else 0
        except Exception:
            return 0
    
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
    
    @staticmethod
    def GetEnemyCount(max_distance=1200):
        """
        Get count of all alive enemies within range.
        
        Args:
            max_distance (float): Search radius
            
        Returns:
            int: Number of alive enemies
        """
        try:
            player_pos = Player.GetXY()
            enemies = AgentArray.GetEnemyArray()
            enemies = AgentArray.Filter.ByDistance(enemies, player_pos, max_distance)
            enemies = AgentArray.Filter.ByCondition(enemies, lambda id: Agent.IsAlive(id))
            return len(enemies)
        except Exception:
            return 0


class ItemFinder:
    """
    Utility class for finding dropped items on the ground.
    Uses the same approach as LootManager.py
    """
    
    @staticmethod
    def GetAllGroundItems(max_distance=5000):
        """
        Get all items on the ground within range.
        
        Args:
            max_distance (float): Search radius
            
        Returns:
            list: List of tuples (agent_id, model_id, distance)
        """
        result = []
        try:
            player_pos = Player.GetXY()
            items = AgentArray.GetItemArray()
            items = AgentArray.Filter.ByDistance(items, player_pos, max_distance)
            
            for agent_id in items:
                try:
                    if not Agent.IsValid(agent_id):
                        continue
                    item_agent = Agent.GetItemAgent(agent_id)
                    if item_agent and item_agent.item_id > 0:
                        model_id = Item.GetModelID(item_agent.item_id)
                        item_pos = Agent.GetXY(agent_id)
                        dist = Utils.Distance(player_pos, item_pos)
                        result.append((agent_id, model_id, dist))
                except Exception:
                    continue
            
            # Sort by distance
            result.sort(key=lambda x: x[2])
            return result
        except Exception:
            return []
    
    @staticmethod
    def FindItemByModelID(model_id, max_distance=2000):
        """
        Find a ground item by its ModelID.
        
        Args:
            model_id (int): The ModelID to search for
            max_distance (float): Search radius
            
        Returns:
            int: Agent ID if found, 0 otherwise
        """
        try:
            player_pos = Player.GetXY()
            items = AgentArray.GetItemArray()
            items = AgentArray.Filter.ByDistance(items, player_pos, max_distance)
            
            for agent_id in items:
                try:
                    if not Agent.IsValid(agent_id):
                        continue
                    item_agent = Agent.GetItemAgent(agent_id)
                    if item_agent and item_agent.item_id > 0:
                        item_model_id = Item.GetModelID(item_agent.item_id)
                        if item_model_id == model_id:
                            return agent_id
                except Exception:
                    continue
            
            return 0
        except Exception:
            return 0
    
    @staticmethod
    def FindNearestItem(max_distance=2000):
        """
        Find the nearest ground item.
        
        Args:
            max_distance (float): Search radius
            
        Returns:
            int: Agent ID if found, 0 otherwise
        """
        items = ItemFinder.GetAllGroundItems(max_distance)
        if items:
            return items[0][0]  # Return agent_id of nearest
        return 0
    
    @staticmethod
    def FindItemNearPosition(x, y, max_distance=500):
        """
        Find any item near a specific position.
        
        Args:
            x (float): X coordinate
            y (float): Y coordinate
            max_distance (float): Search radius from position
            
        Returns:
            int: Agent ID if found, 0 otherwise
        """
        try:
            target_pos = (x, y)
            items = AgentArray.GetItemArray()
            
            nearest_id = 0
            nearest_dist = max_distance + 1
            
            for agent_id in items:
                try:
                    if not Agent.IsValid(agent_id):
                        continue
                    item_pos = Agent.GetXY(agent_id)
                    dist = Utils.Distance(target_pos, item_pos)
                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest_id = agent_id
                except Exception:
                    continue
            
            return nearest_id if nearest_dist <= max_distance else 0
        except Exception:
            return 0


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
            # Target and engage the enemy - UPDATED LOG MESSAGE
            if not self._logged_engage:
                if logger:
                    logger.Add(f"{self.enemy_name} detected, engaging combat!", (1, 0.5, 0, 1), prefix="[Target]")
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
    State machine for picking up a dropped item.
    Now supports both name-based and ModelID-based searching.
    
    Usage:
        # By name (legacy)
        pickup = ItemPickupState("Corsair Garb")
        
        # By ModelID (preferred)
        pickup = ItemPickupState(model_id=12345)
        
        # By position (for any item near a location)
        pickup = ItemPickupState(near_position=(x, y))
        
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
    
    def __init__(self, item_name=None, model_id=None, near_position=None, 
                 max_distance=2000, pickup_distance=150, timeout_ms=15000):
        """
        Args:
            item_name (str): Name of the item to pick up (legacy)
            model_id (int): ModelID of the item to pick up (preferred)
            near_position (tuple): (x, y) position to search near
            max_distance (float): Search radius
            pickup_distance (float): Distance at which to attempt pickup
            timeout_ms (int): Search timeout
        """
        self.item_name = item_name
        self.model_id = model_id
        self.near_position = near_position
        self.max_distance = max_distance
        self.pickup_distance = pickup_distance
        self.timeout_ms = timeout_ms
        
        self._state = self.STATE_SEARCH
        self._item_agent_id = 0
        self._timer = Timer()
        self._timer.Start()
        self._search_timer = Timer()
        self._search_timer.Start()
        self._move_timer = Timer()
        self._move_timer.Start()
        self._logged = False
        self._pickup_attempts = 0
        self._max_pickup_attempts = 5
    
    def Reset(self):
        """Reset the pickup state."""
        self._state = self.STATE_SEARCH
        self._item_agent_id = 0
        self._timer.Reset()
        self._search_timer.Reset()
        self._move_timer.Reset()
        self._logged = False
        self._pickup_attempts = 0
    
    def _FindItem(self):
        """Find the item using the configured method."""
        # Method 1: By ModelID (most reliable)
        if self.model_id:
            return ItemFinder.FindItemByModelID(self.model_id, self.max_distance)
        
        # Method 2: By position (find any item near a spot)
        # FIXED: Use larger radius (was 800, now uses max_distance/2 or 1500)
        if self.near_position:
            search_radius = min(self.max_distance, 1500)
            return ItemFinder.FindItemNearPosition(
                self.near_position[0], 
                self.near_position[1], 
                search_radius
            )
        
        # Method 3: By name (legacy, less reliable)
        if self.item_name:
            return self._FindItemByName()
        
        # Method 4: Just find nearest item
        return ItemFinder.FindNearestItem(self.max_distance)
    
    def _FindItemByName(self):
        """Find a dropped item by name (legacy method)."""
        try:
            player_pos = Player.GetXY()
            items = AgentArray.GetItemArray()
            items = AgentArray.Filter.ByDistance(items, player_pos, self.max_distance)
            
            for item_agent_id in items:
                try:
                    if not Agent.IsValid(item_agent_id):
                        continue
                    
                    item_agent = Agent.GetItemAgent(item_agent_id)
                    if item_agent and item_agent.item_id > 0:
                        # Try to get item name
                        Item.RequestName(item_agent.item_id)
                        if Item.IsNameReady(item_agent.item_id):
                            name = Item.GetName(item_agent.item_id)
                            if name and self.item_name.lower() in name.lower():
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
            item_id = self._FindItem()
            
            if item_id == 0:
                if self._search_timer.HasElapsed(self.timeout_ms):
                    search_desc = self.item_name or f"ModelID {self.model_id}" or "item"
                    if logger:
                        logger.Add(f"Could not find {search_desc}", (1, 0.5, 0, 1), prefix="[Warn]")
                    return "failed"
                
                if not self._logged and self._timer.HasElapsed(2000):
                    search_desc = self.item_name or f"item"
                    if logger:
                        logger.Add(f"Looking for {search_desc}...", (1, 1, 0, 1))
                    self._logged = True
                
                return "searching"
            
            self._item_agent_id = item_id
            self._state = self.STATE_MOVE
            self._timer.Reset()
            self._move_timer.Reset()
            return "moving"
        
        elif self._state == self.STATE_MOVE:
            if not Agent.IsValid(self._item_agent_id):
                # Item might have been picked up by someone else or despawned
                self._state = self.STATE_SEARCH
                self._search_timer.Reset()  # Reset search timer to give more time
                return "searching"
            
            player_pos = Player.GetXY()
            item_pos = Agent.GetXY(self._item_agent_id)
            distance = Utils.Distance(player_pos, item_pos)
            
            if distance <= self.pickup_distance:
                self._state = self.STATE_PICKUP
                self._timer.Reset()
                return "picking_up"
            
            # Move toward item (throttled)
            if self._move_timer.HasElapsed(500):
                Player.Move(item_pos[0], item_pos[1])
                self._move_timer.Reset()
            
            return "moving"
        
        elif self._state == self.STATE_PICKUP:
            search_desc = self.item_name or "item"
            if logger and self._pickup_attempts == 0:
                logger.Add(f"Picking up {search_desc}...", (0, 1, 1, 1))
            
            Player.Interact(self._item_agent_id)
            self._state = self.STATE_WAIT
            self._timer.Reset()
            self._pickup_attempts += 1
            return "picking_up"
        
        elif self._state == self.STATE_WAIT:
            if self._timer.HasElapsed(1500):
                self._state = self.STATE_VERIFY
            return "picking_up"
        
        elif self._state == self.STATE_VERIFY:
            # Check if item is gone (picked up)
            if not Agent.IsValid(self._item_agent_id):
                search_desc = self.item_name or "item"
                if logger:
                    logger.Add(f"Picked up {search_desc}!", (0, 1, 0, 1))
                return "success"
            
            # Item still there, retry
            if self._pickup_attempts >= self._max_pickup_attempts:
                if logger:
                    logger.Add("Failed to pick up item after multiple attempts.", (1, 0, 0, 1), prefix="[Error]")
                return "failed"
            
            # Try again - move closer
            self._state = self.STATE_MOVE
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
    
    Now also scans ALL living agents, not just enemies, to catch neutral NPCs
    that haven't aggroed yet.
    
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
        self._scan_timer = Timer()
        self._scan_timer.Start()
    
    def Reset(self):
        """Reset the scanner state."""
        self._state = self.STATE_MOVING
        self._target_id = 0
        self._target_killed = False
        self._logged_engage = False
        self._timer.Reset()
        self._scan_timer.Reset()
        self.path_handler.reset()
    
    def WasTargetKilled(self):
        """Check if the target enemy was killed during movement."""
        return self._target_killed
    
    def _ScanForTarget(self):
        """
        Scan for target enemy in both enemy array AND all living agents.
        Returns agent_id if found, 0 otherwise.
        """
        # First check enemy array (already hostile)
        target_id = EnemyFinder.FindEnemyByName(
            self.target_enemy_name,
            self.scan_distance,
            alive_only=True
        )
        if target_id != 0:
            return target_id
        
        # Also check all living agents (might be neutral/friendly until aggro)
        try:
            player_pos = Player.GetXY()
            all_agents = AgentArray.GetAgentArray()
            all_agents = AgentArray.Filter.ByDistance(all_agents, player_pos, self.scan_distance)
            
            for agent_id in all_agents:
                try:
                    if not Agent.IsValid(agent_id):
                        continue
                    if not Agent.IsLiving(agent_id):
                        continue
                    if not Agent.IsAlive(agent_id):
                        continue
                    
                    agent_name = Agent.GetName(agent_id)
                    if agent_name and self.target_enemy_name.lower() in agent_name.lower():
                        return agent_id
                except Exception:
                    continue
        except Exception:
            pass
        
        return 0
    
    def Execute(self, logger=None):
        """
        Execute one tick of movement with scanning.
        
        Returns:
            str: "moving", "fighting", "enemy_killed", or "path_complete"
        """
        # Always check if target enemy is nearby (unless already killed and kill_once)
        if not (self.kill_once and self._target_killed):
            if self._state == self.STATE_MOVING:
                # Scan periodically to avoid performance issues
                if self._scan_timer.HasElapsed(500):
                    target_id = self._ScanForTarget()
                    self._scan_timer.Reset()
                    
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
            # UPDATED: Changed log message to "detected, engaging combat!"
            if not self._logged_engage:
                if logger:
                    logger.Add(f"{self.target_enemy_name} detected, engaging combat!", (1, 0.5, 0, 1), prefix="[Target]")
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


class EscortNavigation:
    """
    Navigation that follows a path while staying within range of an escort NPC.
    If the escort falls too far behind, waits for them to catch up.
    
    Usage:
        escort_nav = EscortNavigation(
            path_handler=my_path,
            escort_name="Captain Besuz",
            combat_handler=combat_handler,
            navigation=nav,
            max_escort_distance=1500
        )
        
        # In your execution loop:
        result = escort_nav.Execute(logger)
        if result == "path_complete":
            # Reached destination with escort!
    """
    
    STATE_FIND_ESCORT = 0
    STATE_MOVING = 1
    STATE_WAITING_FOR_ESCORT = 2
    STATE_FIGHTING = 3
    
    def __init__(self, path_handler, escort_name, combat_handler, navigation,
                 max_escort_distance=1500, escort_search_distance=5000):
        """
        Args:
            path_handler: PathHandler with waypoints
            escort_name (str): Name of the escort NPC to stay near
            combat_handler: CombatHandler for combat
            navigation: MissionNavigation for movement
            max_escort_distance (float): Max distance from escort before waiting
            escort_search_distance (float): Distance to search for escort
        """
        self.path_handler = path_handler
        self.escort_name = escort_name
        self.combat_handler = combat_handler
        self.navigation = navigation
        self.max_escort_distance = max_escort_distance
        self.escort_search_distance = escort_search_distance
        
        self._state = self.STATE_FIND_ESCORT
        self._escort_id = 0
        self._timer = Timer()
        self._timer.Start()
        self._wait_logged = False
    
    def Reset(self):
        """Reset the escort navigation state."""
        self._state = self.STATE_FIND_ESCORT
        self._escort_id = 0
        self._timer.Reset()
        self._wait_logged = False
        self.path_handler.reset()
    
    def _FindEscort(self):
        """Find the escort NPC."""
        try:
            player_pos = Player.GetXY()
            all_agents = AgentArray.GetAgentArray()
            all_agents = AgentArray.Filter.ByDistance(all_agents, player_pos, self.escort_search_distance)
            
            for agent_id in all_agents:
                try:
                    if not Agent.IsValid(agent_id):
                        continue
                    if not Agent.IsLiving(agent_id):
                        continue
                    if not Agent.IsAlive(agent_id):
                        continue
                    
                    agent_name = Agent.GetName(agent_id)
                    if agent_name and self.escort_name.lower() in agent_name.lower():
                        return agent_id
                except Exception:
                    continue
        except Exception:
            pass
        return 0
    
    def _GetEscortDistance(self):
        """Get distance to escort NPC."""
        if self._escort_id == 0 or not Agent.IsValid(self._escort_id):
            return -1
        try:
            player_pos = Player.GetXY()
            escort_pos = Agent.GetXY(self._escort_id)
            return Utils.Distance(player_pos, escort_pos)
        except Exception:
            return -1
    
    def Execute(self, logger=None):
        """
        Execute one tick of escort navigation.
        
        Returns:
            str: "searching", "moving", "waiting", "fighting", or "path_complete"
        """
        # Check for enemies first
        enemies = self.navigation.GetNearbyEnemies()
        if enemies:
            self.combat_handler.Execute(target_agent_id=enemies[0])
            self._wait_logged = False
            return "fighting"
        
        if self._state == self.STATE_FIND_ESCORT:
            self._escort_id = self._FindEscort()
            
            if self._escort_id != 0:
                if logger:
                    logger.Add(f"Found {self.escort_name}. Staying close!", (0, 1, 1, 1))
                self._state = self.STATE_MOVING
            else:
                # Can't find escort - continue anyway but keep searching
                if self._timer.HasElapsed(5000):
                    if logger:
                        logger.Add(f"Searching for {self.escort_name}...", (1, 1, 0, 1))
                    self._timer.Reset()
                
                # Try moving anyway
                self._state = self.STATE_MOVING
            
            return "searching"
        
        elif self._state == self.STATE_MOVING:
            # Re-find escort if lost
            if self._escort_id == 0 or not Agent.IsValid(self._escort_id):
                self._escort_id = self._FindEscort()
            
            # Check escort distance
            escort_dist = self._GetEscortDistance()
            
            if escort_dist > 0 and escort_dist > self.max_escort_distance:
                # Too far from escort - wait
                self._state = self.STATE_WAITING_FOR_ESCORT
                self._wait_logged = False
                self._timer.Reset()
                return "waiting"
            
            # Execute normal navigation
            if self.navigation.Execute(self.path_handler, logger):
                return "path_complete"
            
            self._wait_logged = False
            return "moving"
        
        elif self._state == self.STATE_WAITING_FOR_ESCORT:
            # Log waiting message once
            if not self._wait_logged:
                if logger:
                    logger.Add(f"Waiting for {self.escort_name} to catch up...", (1, 1, 0, 1))
                self._wait_logged = True
            
            # Re-find escort if needed
            if self._escort_id == 0 or not Agent.IsValid(self._escort_id):
                self._escort_id = self._FindEscort()
            
            # Check if escort is close enough now
            escort_dist = self._GetEscortDistance()
            
            if escort_dist > 0 and escort_dist <= self.max_escort_distance * 0.7:  # Some hysteresis
                self._state = self.STATE_MOVING
                if logger:
                    logger.Add(f"{self.escort_name} caught up! Continuing...", (0, 1, 0, 1))
                return "moving"
            
            # Timeout - continue anyway after 30 seconds
            if self._timer.HasElapsed(30000):
                if logger:
                    logger.Add(f"Waited too long. Continuing without {self.escort_name}...", (1, 0.5, 0, 1), prefix="[Warn]")
                self._state = self.STATE_MOVING
                return "moving"
            
            return "waiting"
        
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
        self._scan_timer = Timer()
        self._scan_timer.Start()
    
    def Reset(self):
        """Reset the scanner state."""
        self._state = self.STATE_MOVING
        self._target_id = 0
        self._killed_ids.clear()
        self._logged_engage = False
        self._timer.Reset()
        self._scan_timer.Reset()
        self.path_handler.reset()
    
    def GetKillCount(self):
        """Get number of kills if tracker is set."""
        if self.kill_tracker:
            return self.kill_tracker.GetKillCount()
        return len(self._killed_ids)
    
    def _ScanForTargets(self):
        """
        Scan for target enemies, returns list of valid agent IDs.
        Checks both enemy array and all living agents.
        """
        found = []
        
        # Check enemy array first
        found.extend(EnemyFinder.FindAllEnemiesByName(
            self.target_enemy_name,
            self.scan_distance,
            alive_only=True
        ))
        
        # Also check all living agents for neutral targets
        try:
            player_pos = Player.GetXY()
            all_agents = AgentArray.GetAgentArray()
            all_agents = AgentArray.Filter.ByDistance(all_agents, player_pos, self.scan_distance)
            
            for agent_id in all_agents:
                if agent_id in found:
                    continue
                try:
                    if not Agent.IsValid(agent_id):
                        continue
                    if not Agent.IsLiving(agent_id):
                        continue
                    if not Agent.IsAlive(agent_id):
                        continue
                    
                    agent_name = Agent.GetName(agent_id)
                    if agent_name and self.target_enemy_name.lower() in agent_name.lower():
                        found.append(agent_id)
                except Exception:
                    continue
        except Exception:
            pass
        
        return found
    
    def Execute(self, logger=None):
        """
        Execute one tick of movement with scanning.
        
        Returns:
            str: "moving", "fighting", "enemy_killed", or "path_complete"
        """
        # Scan for target enemies while moving
        if self._state == self.STATE_MOVING:
            # Scan periodically
            if self._scan_timer.HasElapsed(500):
                all_targets = self._ScanForTargets()
                self._scan_timer.Reset()
                
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
            # UPDATED: Changed log message to "detected, engaging combat!"
            if not self._logged_engage:
                if logger:
                    progress = ""
                    if self.kill_tracker:
                        progress = f" ({self.kill_tracker.GetProgress()})"
                    logger.Add(f"{self.target_enemy_name} detected, engaging combat!{progress}", (1, 0.5, 0, 1), prefix="[Target]")
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
                        logger.Add(f"{self.target_enemy_name} killed! ({progress})", (0, 1, 0, 1), prefix="[Bonus]")
                else:
                    if logger:
                        logger.Add(f"{self.target_enemy_name} killed!", (0, 1, 0, 1), prefix="[Kill]")
                
                # Return to moving
                self._state = self.STATE_MOVING
                self._target_id = 0
                return "enemy_killed"
            return "fighting"
        
        return "moving"
