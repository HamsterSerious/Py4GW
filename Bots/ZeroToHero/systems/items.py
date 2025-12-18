"""
Items System - Handles item pickup and loot management.

Provides:
- Loot whitelist/blacklist management
- Item pickup (ground items)
- Finding items by ModelID
- Direct pickup for specific mission items
"""
import Py4GW
from Py4GWCoreLib import Player, Utils, Routines
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from Py4GWCoreLib.Py4GWcorelib import LootConfig

from data.timing import Timing, Range


class Items:
    """
    Handles item pickup and loot management.
    
    Uses the core LootConfig singleton for whitelist/blacklist management,
    and provides coroutine-based pickup methods for use in missions.
    
    Key methods for missions:
    - add_to_whitelist(): Add ModelID to pickup whitelist
    - pickup_items(): Pick up whitelisted items nearby
    - pickup_item_by_model_id(): Direct pickup of specific item (best for mission items)
    - find_nearest_item_by_model_id(): Find ground item by ModelID
    """
    
    def __init__(self, bot):
        self.bot = bot
        self._loot_config = LootConfig()
    
    # ==================
    # WHITELIST MANAGEMENT (Non-yielding)
    # ==================
    
    def add_to_whitelist(self, model_id: int):
        """
        Add a ModelID to the loot whitelist.
        
        Items with this ModelID will be picked up by pickup_items().
        This is a synchronous operation - no yield needed.
        
        Args:
            model_id: The item ModelID to whitelist
        """
        self._loot_config.AddToWhitelist(model_id)
        Py4GW.Console.Log(
            "Items", 
            f"Added ModelID {model_id} to loot whitelist.", 
            Py4GW.Console.MessageType.Info
        )
    
    def remove_from_whitelist(self, model_id: int):
        """Remove a ModelID from the loot whitelist."""
        self._loot_config.RemoveFromWhitelist(model_id)
        Py4GW.Console.Log(
            "Items", 
            f"Removed ModelID {model_id} from loot whitelist.", 
            Py4GW.Console.MessageType.Info
        )
    
    def clear_whitelist(self):
        """Clear all entries from the loot whitelist."""
        self._loot_config.ClearWhitelist()
        Py4GW.Console.Log(
            "Items", 
            "Loot whitelist cleared.", 
            Py4GW.Console.MessageType.Info
        )
    
    # ==================
    # BLACKLIST MANAGEMENT (Non-yielding)
    # ==================
    
    def add_to_blacklist(self, model_id: int):
        """Add a ModelID to the loot blacklist (won't be picked up)."""
        self._loot_config.AddToBlacklist(model_id)
    
    def remove_from_blacklist(self, model_id: int):
        """Remove a ModelID from the loot blacklist."""
        self._loot_config.RemoveFromBlacklist(model_id)
    
    def clear_blacklist(self):
        """Clear all entries from the loot blacklist."""
        self._loot_config.ClearBlacklist()
    
    # ==================
    # DIRECT ITEM PICKUP (Yielding) - Best for mission items
    # ==================
    
    def pickup_item_by_model_id(self, model_id: int, max_range: int = None, timeout_ms: int = 5000):
        """
        Find and pick up a specific item by ModelID.
        
        This is the RECOMMENDED method for picking up mission-specific items
        like Stone Tablets, quest items, etc. It directly targets the item
        rather than relying on whitelist filtering.
        
        Args:
            model_id: The ModelID of the item to pick up
            max_range: Maximum search range (default: Range.SPIRIT)
            timeout_ms: Max time to wait for pickup
            
        Yields for coroutine execution.
        Returns True if item was found and picked up.
        """
        max_range = max_range or Range.SPIRIT
        
        # Find the item
        agent_id = self.find_nearest_item_by_model_id(model_id, max_range)
        
        if agent_id == 0:
            Py4GW.Console.Log(
                "Items", 
                f"No item with ModelID {model_id} found within range {max_range}.", 
                Py4GW.Console.MessageType.Warning
            )
            return False
        
        # Get item position
        try:
            item_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
            Py4GW.Console.Log(
                "Items", 
                f"Found item {model_id} (agent {agent_id}) at ({item_pos[0]:.0f}, {item_pos[1]:.0f})", 
                Py4GW.Console.MessageType.Info
            )
        except Exception as e:
            Py4GW.Console.Log(
                "Items", 
                f"Error getting item position: {e}", 
                Py4GW.Console.MessageType.Error
            )
            return False
        
        # Move close to the item
        my_pos = Player.GetXY()
        dist = Utils.Distance(my_pos, item_pos)
        
        if dist > 200:
            Py4GW.Console.Log(
                "Items", 
                f"Moving to item (distance: {dist:.0f})...", 
                Py4GW.Console.MessageType.Info
            )
            yield from self.bot.movement.move_to(item_pos[0], item_pos[1], tolerance=150)
        
        # Pick up the item
        Py4GW.Console.Log(
            "Items", 
            f"Picking up item {model_id}...", 
            Py4GW.Console.MessageType.Info
        )
        
        Player.PickUpItem(agent_id)
        yield from Routines.Yield.wait(500)
        
        # Verify pickup - check if item is still there
        still_exists = self.find_nearest_item_by_model_id(model_id, max_range)
        if still_exists == 0:
            Py4GW.Console.Log(
                "Items", 
                f"Item {model_id} picked up successfully!", 
                Py4GW.Console.MessageType.Success
            )
            return True
        else:
            # Item still exists - maybe we picked up a different one, or failed
            # Check if we're holding a bundle
            if self.bot.interaction.is_holding_bundle():
                Py4GW.Console.Log(
                    "Items", 
                    f"Now holding bundle (item pickup succeeded).", 
                    Py4GW.Console.MessageType.Success
                )
                return True
            else:
                Py4GW.Console.Log(
                    "Items", 
                    f"Item {model_id} may not have been picked up.", 
                    Py4GW.Console.MessageType.Warning
                )
                return False
    
    def wait_for_item_drop(self, model_id: int, timeout_ms: int = 5000, check_interval_ms: int = 250):
        """
        Wait for an item to appear on the ground.
        
        Useful after killing a boss that drops a quest item.
        
        Args:
            model_id: The ModelID to wait for
            timeout_ms: Maximum time to wait
            check_interval_ms: How often to check for the item
            
        Yields for coroutine execution.
        Returns True if item appeared, False if timeout.
        """
        from utils.timer import Timeout
        
        timeout = Timeout(timeout_ms)
        
        while not timeout.expired:
            agent_id = self.find_nearest_item_by_model_id(model_id, Range.SPIRIT)
            if agent_id != 0:
                Py4GW.Console.Log(
                    "Items", 
                    f"Item {model_id} appeared on ground (agent {agent_id}).", 
                    Py4GW.Console.MessageType.Info
                )
                return True
            
            yield from Routines.Yield.wait(check_interval_ms)
        
        Py4GW.Console.Log(
            "Items", 
            f"Timeout waiting for item {model_id} to drop.", 
            Py4GW.Console.MessageType.Warning
        )
        return False
    
    # ==================
    # WHITELIST-BASED PICKUP (Yielding)
    # ==================
    
    def pickup_items(self, pickup_timeout_ms: int = 5000, max_distance: int = None):
        """
        Pick up all whitelisted items within range.
        
        Uses the core LootConfig filtering to find valid items.
        For mission-specific items, prefer pickup_item_by_model_id() instead.
        
        Args:
            pickup_timeout_ms: Max time to spend picking up items
            max_distance: Maximum search distance (default: Earshot ~1012)
            
        Yields for coroutine execution.
        Returns True if at least one item was picked up.
        """
        from Py4GWCoreLib.enums import Range as CoreRange
        
        # Use provided distance or default to Earshot
        search_distance = max_distance if max_distance else CoreRange.Earshot.value
        
        # Get filtered loot array from LootConfig
        try:
            filtered_items = self._loot_config.GetfilteredLootArray(
                distance=search_distance,
                multibox_loot=True,
                allow_unasigned_loot=True
            )
        except Exception as e:
            Py4GW.Console.Log(
                "Items", 
                f"Error getting filtered loot array: {e}", 
                Py4GW.Console.MessageType.Error
            )
            return False
        
        if not filtered_items:
            Py4GW.Console.Log(
                "Items", 
                f"No whitelisted items found within {search_distance} units.", 
                Py4GW.Console.MessageType.Info
            )
            return False
        
        Py4GW.Console.Log(
            "Items", 
            f"Found {len(filtered_items)} whitelisted item(s) to pick up.", 
            Py4GW.Console.MessageType.Info
        )
        
        # Use the core loot routine
        try:
            yield from Routines.Yield.Items.LootItems(
                filtered_items, 
                pickup_timeout=pickup_timeout_ms
            )
        except Exception as e:
            Py4GW.Console.Log(
                "Items", 
                f"Error during LootItems: {e}", 
                Py4GW.Console.MessageType.Error
            )
            return False
        
        return True
    
    def pickup_item_by_agent_id(self, agent_id: int, timeout_ms: int = 5000):
        """
        Pick up a specific item by its agent ID.
        
        Args:
            agent_id: The agent ID of the item to pick up
            timeout_ms: Max time to wait for pickup
            
        Yields for coroutine execution.
        Returns True if item was picked up.
        """
        if agent_id == 0:
            return False
        
        # Move toward the item
        item_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
        yield from self.bot.movement.move_to(item_pos[0], item_pos[1], tolerance=100)
        
        # Pick it up
        Player.PickUpItem(agent_id)
        yield from Routines.Yield.wait(500)
        
        return True
    
    # ==================
    # ITEM FINDING (Non-yielding)
    # ==================
    
    def find_nearest_item_by_model_id(self, model_id: int, max_range: int = None) -> int:
        """
        Find the nearest ground item with a specific ModelID.
        
        Args:
            model_id: The ModelID to search for
            max_range: Maximum search distance (default: Range.SPIRIT)
            
        Returns:
            Agent ID of the nearest matching item, or 0 if not found
        """
        max_range = max_range or Range.SPIRIT
        
        try:
            items = GLOBAL_CACHE.AgentArray.GetItemArray()
            my_pos = Player.GetXY()
            
            candidates = []
            for agent_id in items:
                # Check if this is the item we want
                # Items use GetPlayerNumber for their ModelID
                item_model = GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id)
                if item_model != model_id:
                    continue
                
                # Check distance
                item_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
                dist = Utils.Distance(my_pos, item_pos)
                
                if dist <= max_range:
                    candidates.append((dist, agent_id))
            
            if not candidates:
                return 0
            
            # Return nearest
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
            
        except Exception as e:
            Py4GW.Console.Log(
                "Items", 
                f"Error finding item: {e}", 
                Py4GW.Console.MessageType.Error
            )
            return 0
    
    def find_all_items_by_model_id(self, model_id: int, max_range: int = None) -> list:
        """
        Find all ground items with a specific ModelID within range.
        
        Args:
            model_id: The ModelID to search for
            max_range: Maximum search distance (default: Range.SPIRIT)
            
        Returns:
            List of (distance, agent_id) tuples sorted by distance
        """
        max_range = max_range or Range.SPIRIT
        
        try:
            items = GLOBAL_CACHE.AgentArray.GetItemArray()
            my_pos = Player.GetXY()
            
            candidates = []
            for agent_id in items:
                item_model = GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id)
                if item_model != model_id:
                    continue
                
                item_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
                dist = Utils.Distance(my_pos, item_pos)
                
                if dist <= max_range:
                    candidates.append((dist, agent_id))
            
            candidates.sort(key=lambda x: x[0])
            return candidates
            
        except Exception:
            return []
    
    def count_items_by_model_id(self, model_id: int, max_range: int = None) -> int:
        """
        Count how many items with a specific ModelID are on the ground.
        
        Args:
            model_id: The ModelID to count
            max_range: Maximum search distance
            
        Returns:
            Number of matching items
        """
        return len(self.find_all_items_by_model_id(model_id, max_range))
    
    # ==================
    # UTILITY
    # ==================
    
    def is_item_nearby(self, model_id: int, max_range: int = None) -> bool:
        """
        Check if an item with the specified ModelID is nearby.
        
        Args:
            model_id: The ModelID to check for
            max_range: Maximum search range
            
        Returns:
            True if at least one matching item is nearby
        """
        return self.find_nearest_item_by_model_id(model_id, max_range) != 0
    
    def debug_nearby_items(self, max_range: int = None):
        """
        Log all items nearby for debugging purposes.
        
        Args:
            max_range: Maximum search range (default: Range.SPIRIT)
        """
        max_range = max_range or Range.SPIRIT
        
        try:
            items = GLOBAL_CACHE.AgentArray.GetItemArray()
            my_pos = Player.GetXY()
            
            Py4GW.Console.Log(
                "Items", 
                f"=== DEBUG: Items within range {max_range} ===", 
                Py4GW.Console.MessageType.Info
            )
            
            count = 0
            for agent_id in items:
                item_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
                dist = Utils.Distance(my_pos, item_pos)
                
                if dist <= max_range:
                    item_model = GLOBAL_CACHE.Agent.GetPlayerNumber(agent_id)
                    Py4GW.Console.Log(
                        "Items", 
                        f"  Item: ModelID={item_model}, AgentID={agent_id}, Dist={dist:.0f}", 
                        Py4GW.Console.MessageType.Info
                    )
                    count += 1
            
            Py4GW.Console.Log(
                "Items", 
                f"=== Total: {count} items ===", 
                Py4GW.Console.MessageType.Info
            )
            
        except Exception as e:
            Py4GW.Console.Log(
                "Items", 
                f"Debug error: {e}", 
                Py4GW.Console.MessageType.Error
            )