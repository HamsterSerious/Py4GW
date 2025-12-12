import importlib
import pkgutil
import inspect

class MissionLoader:
    @staticmethod
    def GetMissionsForCampaign(campaign_name):
        """
        Dynamically scans the 'Missions' folder of the specified campaign
        and returns a list of (MissionName, MissionClass).
        
        Expected structure: Bots/ZeroToHero/{Campaign}/Missions/Mission_{Name}.py
        """
        missions = []
        
        # Construct the package path (Note: This assumes the bot is running from the root or properly installed)
        # We try to import the package dynamically
        package_path = f"Bots.ZeroToHero.{campaign_name}.Missions"
        
        try:
            # Import the package to find its file path
            package = importlib.import_module(package_path)
            
            # Iterate over all modules in the package
            for _, name, _ in pkgutil.iter_modules(package.__path__):
                if name.startswith("Mission_"):
                    # Import the specific mission module
                    full_module_name = f"{package_path}.{name}"
                    module = importlib.import_module(full_module_name)
                    
                    # Look for a class that matches the naming convention or has a GetInfo method
                    # For simplicity, we assume the class name matches the filename suffix or we take the first class
                    for attribute_name in dir(module):
                        attribute = getattr(module, attribute_name)
                        
                        if inspect.isclass(attribute):
                            # Check if it has the required method
                            if hasattr(attribute, "GetInfo") and hasattr(attribute, "Execution_Routine"):
                                # Create a temporary instance to get the Name
                                temp_instance = attribute()
                                info = temp_instance.GetInfo()
                                missions.append((info.get("Name", name), attribute))
                                break
                                
        except ImportError as e:
            print(f"Failed to load missions for {campaign_name}: {e}")
            # Fallback for empty folders
            return []
            
        return missions