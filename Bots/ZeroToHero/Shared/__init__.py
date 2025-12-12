"""
ZeroToHero Shared Utilities

This package provides reusable components for mission bots:
- PartyUtils: Party validation, hero checks
- AgentUtils: NPC/Gadget finding
- MapUtils: Map validation, mission state tracking
- InteractionUtils: Bundle handling, gadget interactions, enemy hunting, item pickup
- OutpostHandler: Generic outpost state machine
- CombatHandler: Combat execution
- Navigation: Smart pathfinding with combat
- MissionContext: Base classes for missions
- MissionLoader: Dynamic mission discovery
"""

from .PartyUtils import PartyRequirements, PartyValidator
from .AgentUtils import AgentFinder, AgentPosition
from .MapUtils import MapValidator, MissionStateTracker, MapWaiter
from .InteractionUtils import (
    BundleHandler, 
    BundlePickupState, 
    GadgetInteractionState, 
    NPCInteractionHelper,
    EnemyFinder,
    ItemFinder,  # NEW: Added ItemFinder for ground item detection
    TargetedKillState,
    ItemPickupState,
    WaitForHostileState,
    MultiKillTracker,
    ScanWhileMoving,
    ScanWhileMovingMulti,
    EscortNavigation  # NEW: Follow path while staying near escort NPC
)
from .OutpostHandler import OutpostHandler
from .CombatHandler import CombatHandler
from .Navigation import MissionNavigation
from .MissionContext import MissionContext, BaseMission
from .MissionLoader import MissionLoader

__all__ = [
    # Party
    'PartyRequirements', 'PartyValidator',
    # Agents
    'AgentFinder', 'AgentPosition',
    # Map
    'MapValidator', 'MissionStateTracker', 'MapWaiter',
    # Interaction
    'BundleHandler', 'BundlePickupState', 'GadgetInteractionState', 'NPCInteractionHelper',
    'EnemyFinder', 'ItemFinder', 'TargetedKillState', 'ItemPickupState', 'WaitForHostileState', 
    'MultiKillTracker', 'ScanWhileMoving', 'ScanWhileMovingMulti', 'EscortNavigation',
    # Outpost
    'OutpostHandler',
    # Combat & Navigation
    'CombatHandler', 'MissionNavigation',
    # Base Classes
    'MissionContext', 'BaseMission',
    # Loader
    'MissionLoader',
]
