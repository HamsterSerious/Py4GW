import os
import json
import copy
import time
import Py4GW
import PyImGui
from Py4GWCoreLib import *
from Py4GWCoreLib.GlobalCache import GLOBAL_CACHE
from .Enums import HeroID

class TeamManager:
    def __init__(self, bot):
        self.bot = bot
        self.config_path = ""
        self.character_name = ""
        
        self.profiles = {}
        self.custom_hero_names = {} 
        self.mission_hero_assignments = {} 
        
        self.show_window = False
        self.is_new_config = True
        self.is_party_ready = False
        
        self.test_routine = None
        self.selected_rename_hero_id = HeroID.Norgu.value 
        
        self.default_profile = {
            "slots": [0] * 7,
            "builds": [""] * 7
        }
        
        self.hero_options = [] 

    def Initialize(self):
        raw_name = GLOBAL_CACHE.Player.GetName()
        if not raw_name: return
        self.character_name = raw_name.replace('\0', '').strip()

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config_dir = os.path.join(base_dir, "Configs")
        if not os.path.exists(config_dir): os.makedirs(config_dir)
            
        self.config_path = os.path.join(config_dir, f"TeamConfig_{self.character_name}.json")
        
        if os.path.exists(self.config_path):
            self.is_new_config = False
            self.LoadConfig()
        else:
            self.is_new_config = True
            self.LoadConfig()
            self._PopulateDefaultMercNames()
            
        self.RefreshHeroList()

    def _PopulateDefaultMercNames(self):
        if not self.custom_hero_names:
            for i in range(1, 9):
                enum_name = f"MercenaryHero{i}"
                if hasattr(HeroID, enum_name):
                    hero_id = getattr(HeroID, enum_name)
                    self.custom_hero_names[str(hero_id.value)] = f"Mercenary {i}"

    def HasValidConfig(self): return not self.is_new_config
    def IsPartyReady(self): return self.is_party_ready

    def RefreshHeroList(self):
        self.hero_options = []
        for hero in HeroID:
            if hero.value == 0: continue
            original_name = HeroID.get_nice_name(hero.value)
            str_id = str(hero.value)
            if str_id in self.custom_hero_names and self.custom_hero_names[str_id]:
                display_name = f"{self.custom_hero_names[str_id]} ({original_name})"
            else:
                display_name = original_name
            self.hero_options.append((hero.value, display_name))
        self.hero_options.sort(key=lambda x: x[1])

    def LoadConfig(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    self.profiles = data.get("profiles", {})
                    self.custom_hero_names = data.get("custom_hero_names", {})
                    self.mission_hero_assignments = data.get("mission_hero_assignments", {})
                    
                    for key, profile in self.profiles.items():
                        if "mandatory_slot" in profile: del profile["mandatory_slot"]
                        if "replaceable_slot" in profile: del profile["replaceable_slot"]
                            
            except Exception as e:
                Py4GW.Console.Log("TeamManager", f"Error loading config: {e}", Py4GW.Console.MessageType.Error)
        
        keys = ["4_NM", "4_HM", "6_NM", "6_HM", "8_NM", "8_HM"]
        for k in keys:
            if k not in self.profiles:
                self.profiles[k] = copy.deepcopy(self.default_profile)
        self.RefreshHeroList()

    def _sanitize_string(self, s):
        if isinstance(s, str): return s.replace('\0', '').strip()
        return s

    def SaveConfig(self):
        if self.config_path:
            try:
                sanitized_profiles = copy.deepcopy(self.profiles)
                for p_key, profile in sanitized_profiles.items():
                    profile["builds"] = [self._sanitize_string(b) for b in profile["builds"]]
                sanitized_names = {k: self._sanitize_string(v) for k, v in self.custom_hero_names.items()}

                save_data = {
                    "profiles": sanitized_profiles,
                    "custom_hero_names": sanitized_names,
                    "mission_hero_assignments": self.mission_hero_assignments
                }
                with open(self.config_path, "w") as f:
                    json.dump(save_data, f, indent=4)
                self.is_new_config = False
                Py4GW.Console.Log("TeamManager", "Configuration Saved.", Py4GW.Console.MessageType.Success)
                self.RefreshHeroList()
            except Exception as e:
                Py4GW.Console.Log("TeamManager", f"Error saving config: {e}", Py4GW.Console.MessageType.Error)

    def Update(self):
        if self.test_routine:
            try:
                next(self.test_routine)
            except StopIteration:
                self.test_routine = None
                Py4GW.Console.Log("TeamManager", "Test Sequence Complete.", Py4GW.Console.MessageType.Success)
            except Exception as e:
                self.test_routine = None
                import traceback
                Py4GW.Console.Log("TeamManager", f"Test Sequence Crash: {e}", Py4GW.Console.MessageType.Error)
                Py4GW.Console.Log("TeamManager", traceback.format_exc(), Py4GW.Console.MessageType.Error)

    def GetAssignedHero(self, mission_name, slot_index, default_hero_id=0):
        key = f"{mission_name}_{slot_index}"
        return self.mission_hero_assignments.get(key, default_hero_id)

    def SetAssignedHero(self, mission_name, slot_index, hero_id):
        key = f"{mission_name}_{slot_index}"
        if self.mission_hero_assignments.get(key) != hero_id:
            self.mission_hero_assignments[key] = hero_id
            self.SaveConfig()

    def _FindHeroSlot(self, hero_id):
        try:
            heroes = GLOBAL_CACHE.Party.GetHeroes()
            for i, hero in enumerate(heroes):
                if hero.hero_id.GetID() == hero_id:
                    return i + 1 
        except Exception as e:
            pass
        return -1

    def DisbandParty(self):
        if GLOBAL_CACHE.Party.GetHeroCount() > 0:
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()

    def LoadBuildToHero(self, hero_id, build_code):
        if not build_code or build_code == "Any": return
        found_slot = self._FindHeroSlot(hero_id)
        if found_slot == -1: return
        try:
            GLOBAL_CACHE.SkillBar.LoadHeroSkillTemplate(found_slot, build_code)
        except: pass

    # --- Test Loadout Routines ---
    def TestMandatoryHeroes(self, hero_requirements, mission_name):
        Py4GW.Console.Log("TeamManager", "Starting Mandatory Hero Test...", Py4GW.Console.MessageType.Info)
        
        if GLOBAL_CACHE.Party.GetHeroCount() > 0:
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            timeout = time.time() + 2.0
            while GLOBAL_CACHE.Party.GetHeroCount() > 0 and time.time() < timeout:
                yield from Routines.Yield.wait(100)
            yield from Routines.Yield.wait(200)

        for idx, req in enumerate(hero_requirements):
            hero_id = req.get("HeroID", 0)
            if hero_id == 0:
                hero_id = self.GetAssignedHero(mission_name, idx, 0)
                if hero_id == 0:
                    Py4GW.Console.Log("TeamManager", f"Skipping Slot {idx+1}: No hero selected.", Py4GW.Console.MessageType.Warning)
                    continue
            
            hero_name = self._GetHeroDisplayName(hero_id)
            Py4GW.Console.Log("TeamManager", f"Adding {hero_name} (Slot {idx+1})...", Py4GW.Console.MessageType.Info)
            GLOBAL_CACHE.Party.Heroes.AddHero(hero_id)
            
            found_slot = -1
            timeout = time.time() + 3.0
            while time.time() < timeout:
                found_slot = self._FindHeroSlot(hero_id)
                if found_slot != -1: break
                yield from Routines.Yield.wait(100)
            
            if found_slot == -1:
                Py4GW.Console.Log("TeamManager", f"Failed to add {hero_name}.", Py4GW.Console.MessageType.Error)
                continue
                
            build_code = req.get("Build", "")
            expected_skills = req.get("Expected_Skills", 8)
            
            if build_code and build_code != "Any":
                yield from Routines.Yield.wait(200)
                GLOBAL_CACHE.SkillBar.LoadHeroSkillTemplate(found_slot, build_code)
                yield from Routines.Yield.wait(1000) 
                
                try:
                    loaded_count = 0
                    if hasattr(GLOBAL_CACHE.SkillBar, "GetHeroSkillbar"):
                        hero_data = GLOBAL_CACHE.SkillBar.GetHeroSkillbar(found_slot)
                        if isinstance(hero_data, (list, tuple)):
                            for item in hero_data:
                                val = 0
                                if isinstance(item, int): val = item
                                else:
                                    try: val = item.id.id
                                    except:
                                        try: val = item.id
                                        except: pass
                                if val != 0: loaded_count += 1
                        elif hasattr(hero_data, "GetSkill"):
                            for i in range(8):
                                try:
                                    skill = hero_data.GetSkill(i)
                                    if skill and skill.id.id != 0: loaded_count += 1
                                except: pass
                        
                        if loaded_count >= expected_skills:
                            Py4GW.Console.Log("TeamManager", f"{hero_name}: Success ({loaded_count}/{expected_skills} skills).", Py4GW.Console.MessageType.Success)
                        else:
                            Py4GW.Console.Log("TeamManager", f"{hero_name}: Warning! Only loaded {loaded_count}/{expected_skills} skills. Click the build code in the info window to copy and verify.", Py4GW.Console.MessageType.Warning)
                    else:
                        Py4GW.Console.Log("TeamManager", f"{hero_name}: Build loaded (Verification unavailable).", Py4GW.Console.MessageType.Success)
                except Exception as e:
                    Py4GW.Console.Log("TeamManager", f"Verification Error: {str(e)}", Py4GW.Console.MessageType.Error)
            else:
                Py4GW.Console.Log("TeamManager", f"{hero_name} ready (Any build).", Py4GW.Console.MessageType.Success)
            yield from Routines.Yield.wait(300)

        Py4GW.Console.Log("TeamManager", "Mandatory Hero Check Complete.", Py4GW.Console.MessageType.Info)

    def TestPlayerLoadout(self, build_code, expected_skills=8):
        Py4GW.Console.Log("TeamManager", "Testing Player Loadout...", Py4GW.Console.MessageType.Info)
        if build_code and build_code != "Any":
            GLOBAL_CACHE.SkillBar.LoadSkillTemplate(build_code)
            yield from Routines.Yield.wait(1000)
            skill_ids = GLOBAL_CACHE.SkillBar.GetSkillbar()
            equipped_count = len([s for s in skill_ids if s != 0])
            if equipped_count >= expected_skills:
                Py4GW.Console.Log("TeamManager", f"Success! Equipped {equipped_count}/{expected_skills} skills.", Py4GW.Console.MessageType.Success)
            else:
                Py4GW.Console.Log("TeamManager", f"Warning: Only {equipped_count} skills loaded. Expected {expected_skills}. Click the build code in the info window to copy and verify.", Py4GW.Console.MessageType.Warning)
        else:
             Py4GW.Console.Log("TeamManager", "No build code provided.", Py4GW.Console.MessageType.Warning)

    # --- Loading Logic ---
    def LoadTeam(self, party_size, mode="NM"):
        self.is_party_ready = False
        key = f"{party_size}_{mode}"
        profile = self.profiles.get(key, self.default_profile)
        
        Py4GW.Console.Log("TeamManager", f"Loading Profile: [{key}]", Py4GW.Console.MessageType.Info)

        if GLOBAL_CACHE.Party.GetHeroCount() > 0:
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            yield from Routines.Yield.wait(500)

        yield from self._RecruitHeroes(party_size, profile["slots"], profile["builds"])
        self.is_party_ready = True
        Py4GW.Console.Log("TeamManager", "Party Assembled.", Py4GW.Console.MessageType.Success)

    def LoadTeamWithMandatoryHeroes(self, party_size, mode, mandatory_list, mission_name=""):
        """
        Loads team profile, then overwrites the first N slots with the mandatory heroes list.
        Resolves flexible hero selections using mission_name.
        """
        self.is_party_ready = False
        key = f"{party_size}_{mode}"
        profile = self.profiles.get(key, self.default_profile)
        
        Py4GW.Console.Log("TeamManager", f"Loading Profile: [{key}] with {len(mandatory_list)} mandatory heroes.", Py4GW.Console.MessageType.Info)

        if GLOBAL_CACHE.Party.GetHeroCount() > 0:
            GLOBAL_CACHE.Party.Heroes.KickAllHeroes()
            yield from Routines.Yield.wait(500)

        # 1. Start with copy of profile
        modified_slots = list(profile["slots"])
        modified_builds = list(profile["builds"])
        
        # 2. Overwrite first N slots with mandatory heroes
        for i, req in enumerate(mandatory_list):
            if i >= len(modified_slots): break # Safety for party size limits
            
            hero_id = req.get("HeroID", 0)
            build_code = req.get("Build", "")
            
            # Resolve flexible heroes
            if hero_id == 0:
                hero_id = self.GetAssignedHero(mission_name, i, 0)
                if hero_id == 0:
                    Py4GW.Console.Log("TeamManager", f"Warning: No hero assigned for mandatory slot {i+1}!", Py4GW.Console.MessageType.Warning)
            

            modified_slots[i] = hero_id

            if build_code == "Any":
                modified_builds[i] = ""
            else:
                modified_builds[i] = build_code
                
            h_name = self._GetHeroDisplayName(hero_id)
            Py4GW.Console.Log("TeamManager", f"Mandatory Slot {i+1}: {h_name}", Py4GW.Console.MessageType.Info)

        # 3. Recruit
        yield from self._RecruitHeroes(party_size, modified_slots, modified_builds)
        self.is_party_ready = True
        Py4GW.Console.Log("TeamManager", "Party Assembled.", Py4GW.Console.MessageType.Success)

    def _RecruitHeroes(self, party_size, slots, builds):
        slots_needed = party_size - 1
        party_slot_index = 1 
        for i in range(slots_needed):
            if i >= len(slots): break
            hero_id = slots[i]
            build_code = builds[i]
            if hero_id > 0:
                hero_name = self._GetHeroDisplayName(hero_id)
                Py4GW.Console.Log("TeamManager", f"Slot {i + 1}: Adding {hero_name}", Py4GW.Console.MessageType.Info)
                GLOBAL_CACHE.Party.Heroes.AddHero(hero_id)
                yield from Routines.Yield.wait(300)
                if build_code and build_code != "Any":
                    yield from self._ApplyHeroBuild(party_slot_index, build_code, hero_name)
                party_slot_index += 1

    def _ApplyHeroBuild(self, party_slot, build_code, hero_name="Hero"):
        if not build_code or build_code == "Any": return
        try:
            GLOBAL_CACHE.SkillBar.LoadHeroSkillTemplate(party_slot, build_code)
            yield from Routines.Yield.wait(200)
            Py4GW.Console.Log("TeamManager", f"Applied build to {hero_name}.", Py4GW.Console.MessageType.Info)
        except Exception as e:
            Py4GW.Console.Log("TeamManager", f"Failed to apply build to {hero_name}: {e}", Py4GW.Console.MessageType.Warning)

    def _GetHeroDisplayName(self, hero_id):
        if hero_id == 0: return "None"
        for id_val, name in self.hero_options:
            if id_val == hero_id: return name
        return f"Hero {hero_id}"

    def DrawWindow(self):
        if not self.show_window: return
        if PyImGui.begin("Team Setup", 0):
            if self.is_new_config:
                PyImGui.text_colored("Please configure and Save your teams!", (1, 0, 0, 1))
                PyImGui.separator()
            if PyImGui.begin_tab_bar("Profiles"):
                for size in [4, 6, 8]:
                    if PyImGui.begin_tab_item(f"{size}-Man"):
                        self._DrawProfileSelector(size)
                        PyImGui.end_tab_item()
                if PyImGui.begin_tab_item("Hero Rename"):
                    self._DrawRenamingEditor()
                    PyImGui.end_tab_item()
                PyImGui.end_tab_bar()
            PyImGui.separator()
            if PyImGui.button("Save & Close", -1, 30):
                self.SaveConfig()
                self.show_window = False
        PyImGui.end()

    def _DrawRenamingEditor(self):
        PyImGui.text("Give your heroes custom names (e.g. build names):")
        PyImGui.separator()
        current_display_name = HeroID.get_nice_name(self.selected_rename_hero_id)
        if str(self.selected_rename_hero_id) in self.custom_hero_names:
             current_display_name = f"{self.custom_hero_names[str(self.selected_rename_hero_id)]} ({current_display_name})"
        if PyImGui.begin_combo("Select Hero", current_display_name, 0):
            for hero in HeroID:
                if hero.value == 0: continue
                std_name = HeroID.get_nice_name(hero.value)
                if PyImGui.selectable(std_name, hero.value == self.selected_rename_hero_id, 0, (0,0)):
                    self.selected_rename_hero_id = hero.value
            PyImGui.end_combo()
        str_id = str(self.selected_rename_hero_id)
        current_custom = self.custom_hero_names.get(str_id, "")
        new_val = PyImGui.input_text("Custom Name", current_custom, 64)
        new_val = self._sanitize_string(new_val)
        if new_val != current_custom:
            self.custom_hero_names[str_id] = new_val
        PyImGui.same_line(0, 5)
        if PyImGui.button("Save", 0, 0): self.SaveConfig()
        PyImGui.separator()
        PyImGui.text_disabled("Note: Changes update the 'Setup Team' dropdowns after Saving.")

    def _DrawProfileSelector(self, size):
        PyImGui.text_colored("How to configure your team:", (0.7, 0.7, 0.7, 1.0))
        PyImGui.bullet()
        PyImGui.same_line(0.0, 0.0)
        PyImGui.text("Select a hero for each slot from the dropdown.")
        PyImGui.bullet()
        PyImGui.same_line(0.0, 0.0)
        PyImGui.text("Paste a build template code (optional) to auto-load skills.")
        PyImGui.dummy(0, 10)
        PyImGui.text_colored("Note:", (1.0, 0.5, 0.3, 1.0))
        PyImGui.same_line(0.0, 5.0)
        PyImGui.text("Mandatory heroes (from missions) will automatically")
        PyImGui.text("replace the first available hero slots (1, 2, etc).")
        PyImGui.separator()
        PyImGui.dummy(0, 5)
        if PyImGui.collapsing_header(f"{size}-Man Normal Mode", PyImGui.TreeNodeFlags.DefaultOpen):
            self._DrawEditor(f"{size}_NM", size, "NM")
        if PyImGui.collapsing_header(f"{size}-Man Hard Mode", PyImGui.TreeNodeFlags.DefaultOpen):
            self._DrawEditor(f"{size}_HM", size, "HM")

    def _DrawEditor(self, key, size, mode):
        profile = self.profiles[key]
        if PyImGui.button(f"Test Load ({size}-Man {mode})", 0, 0):
            Py4GW.Console.Log("TeamManager", f"Test Load Initiated for [{key}]", Py4GW.Console.MessageType.Info)
            self.test_routine = self.LoadTeam(size, mode)
        PyImGui.dummy(0, 5)
        for i in range(size - 1):
            PyImGui.push_id(f"{key}_slot_{i}")
            PyImGui.text(f"{i + 1}.")
            PyImGui.same_line(0.0, 10.0)
            current_hero_val = profile["slots"][i]
            current_name = "-- Select Hero --"
            for id_val, name in self.hero_options:
                if id_val == current_hero_val:
                    current_name = name
                    break
            if current_hero_val == 0: current_name = "-- Select Hero --"
            PyImGui.set_next_item_width(180)
            if PyImGui.begin_combo("##Hero", current_name, 0):
                if PyImGui.selectable("-- None --", current_hero_val == 0, 0, (0, 0)):
                    profile["slots"][i] = 0
                PyImGui.separator()
                for id_val, name in self.hero_options:
                    is_selected = (id_val == current_hero_val)
                    if PyImGui.selectable(name, is_selected, 0, (0, 0)):
                        profile["slots"][i] = id_val
                PyImGui.end_combo()
            PyImGui.same_line(0.0, 10.0)
            PyImGui.set_next_item_width(200)
            new_build = PyImGui.input_text("##Build", profile["builds"][i], 64)
            new_build = self._sanitize_string(new_build)
            if new_build != profile["builds"][i]:
                profile["builds"][i] = new_build
            PyImGui.pop_id()
        PyImGui.dummy(0, 5)
        PyImGui.separator()