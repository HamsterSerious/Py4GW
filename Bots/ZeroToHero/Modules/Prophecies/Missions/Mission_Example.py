from Bots.ZeroToHero.Modules.BaseTask import BaseTask
from Bots.ZeroToHero.Modules.Common.Enums import HeroID
import Py4GW

class Mission_Example(BaseTask):
    def __init__(self):
        super().__init__()
        self.name = "Example Mission (Ascalon)"
        self.description = "This is a tutorial mission to demonstrate the framework."
        self.task_type = "Mission" 

    def GetInfo(self):
        """
        Returns metadata about the mission.
        """
        return {
            "Name": self.name,
            "Type": self.task_type,
            "Description": "An example mission where we fight our way through the Ascalon breach. Requires standard team setup.",
            "Recommended_Builds": ["OACjE...", "OQGkA..."],
            "HM_Tips": "Bring plenty of condition removal for the burning.",
            
            # --- NEW MANDATORY LOADOUT SECTION ---
            "Mandatory_Loadout": {
                # Normal Mode Requirements
                "NM": {
                     # Example: No specific requirements for NM
                },
                
                # Hard Mode Requirements
                "HM": {
                    # Optional: Verify that the player loaded at least X skills
                    "Expected_Skills": 8, 

                    # Dictionary keyed by Primary Profession
                    "Player_Build": {
                        "Warrior": "OQASE5ybM+s8146lE8146lE81",
                        "Mesmer": "OQBDAqwDSzZzJzJzJzJzJzJzJ",
                        "Any": "OACjEjiM5MXT20658m4e5u172A" # Fallback for other classes
                    },
                    
                    # New Equipment Section (Runes/Insignias)
                    "Equipment": {
                        "Runes": "Superior Vigor, +1+3 Fire Magic",
                        "Insignias": "Survivor Insignias on all armor pieces"
                    },

                    # New Weapons Section
                    "Weapons": {
                        "Set 1": "40/40 Fire Staff (HCT 20% / HSR 20%)",
                        "Set 2": "Longbow + Shield (for pulling)"
                    },

                    "Required_Heroes": [
                        # 1. FIXED Requirement (Game requires Koss)
                        { 
                            "HeroID": HeroID.Koss.value, 
                            "Build": "OQcUERKXzvMXFeSfh8N14K8VcHA",
                            "Expected_Skills": 8
                        },
                        # 2. STRATEGY Requirement (Bot needs a Healer/Prot)
                        { 
                            "HeroID": 0, # 0 = Generic/Flexible Slot
                            "Role": "Necro",
                            "Build": "OAdTUYD6VSBcXcBKm8LAAAAAAA",
                            "Expected_Skills": 5,
                            "Equipment": "Radiant Insignias, +1+3 Divine Favor",
                            "Weapons": "40/40 Divine Set"
                        }
                    ],
                    "Notes": "Do NOT bring Minion Masters, as they steal aggro in the final room."
                }
            }
        }

    def Execution_Routine(self, bot):
        # 1. Travel
        yield from bot.transition.TravelTo(map_id=123) 
        
        # 2. Setup Team (Handles HM/NM automatically)
        yield from bot.transition.SetupMission(bot, use_hard_mode=self.use_hard_mode)
        
        # 3. Enter Mission
        yield from bot.transition.MoveToAndInteract(bot, npc_id=456)
        
        # 4. Logic Loop
        while not bot.movement.IsMapReady():
            yield from bot.movement.Wait(100)
            
        Py4GW.Console.Log(bot.bot_name, "Mission Started!", Py4GW.Console.MessageType.Info)
        
        # ... Mission Logic ...
        yield from bot.movement.Wait(1000)
        
        self.finished = True