"""
Items System - Handles item pickup and loot management.

Provides:
- Loot whitelist/blacklist management
- Item pickup (ground items)
- Finding items by ModelID
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
    - find_item_by_model_id(): Find ground item by ModelID
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
    # ITEM PICKUP (Yielding)
    # ==================
    
    def pickup_items(self, pickup_timeout_ms: int = 5000):
        """
        Pick up all whitelisted items within range.
        
        Uses the core LootConfig filtering to find valid items.
        
        Args:
            pickup_timeout_ms: Max time to spend picking up items
            
        Yields for coroutine execution.
        Returns True if at least one item was picked up.
        """
        from Py4GWCoreLib.enums import Range as CoreRange
        
        # Get filtered loot array from LootConfig
        filtered_items = self._loot_config.GetfilteredLootArray(
            distance=CoreRange.Earshot.value,
            multibox_loot=True,
            allow_unasigned_loot=True
        )
        
        if not filtered_items:
            return False
        
        picked_up_any = False
        
        # Use the core loot routine
        yield from Routines.Yield.Items.LootItems(
            filtered_items, 
            pickup_timeout=pickup_timeout_ms
        )
        
        # Check if we're now holding something (for bundle items)
        picked_up_any = len(filtered_items) > 0
        
        return picked_up_any
    
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
    
    def pickup_nearest_by_model_id(self, model_id: int, max_range: int = None, timeout_ms: int = 5000):
        """
        Find and pick up the nearest item with a specific ModelID.
        
        This is useful for mission-specific items like Stone Tablets
        where you need to pick up the closest one.
        
        Args:
            model_id: The ModelID of the item to pick up
            max_range: Maximum search range (default: Range.SPIRIT)
            timeout_ms: Max time to wait for pickup
            
        Yields for coroutine execution.
        Returns True if item was found and picked up.
        """
        max_range = max_range or Range.SPIRIT
        
        # Find the nearest item with this ModelID
        agent_id = self.find_nearest_item_by_model_id(model_id, max_range)
        
        if agent_id == 0:
            Py4GW.Console.Log(
                "Items", 
                f"No item with ModelID {model_id} found within range {max_range}.", 
                Py4GW.Console.MessageType.Warning
            )
            return False
        
        # Move to and pick up the item
        item_pos = GLOBAL_CACHE.Agent.GetXY(agent_id)
        Py4GW.Console.Log(
            "Items", 
            f"Found item {model_id} at ({item_pos[0]:.0f}, {item_pos[1]:.0f}), picking up...", 
            Py4GW.Console.MessageType.Info
        )
        
        yield from self.bot.movement.move_to(item_pos[0], item_pos[1], tolerance=100)
        
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