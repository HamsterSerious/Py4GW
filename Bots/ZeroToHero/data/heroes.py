"""
Hero display name utilities for Zero To Hero bot.

Hero IDs and enums come from Py4GWCoreLib.enums_src.Hero_enums.HeroType.
This module only provides display name formatting.
"""
from Py4GWCoreLib.enums_src.Hero_enums import HeroType


# Display name overrides for heroes with compound names
# Maps HeroType enum to human-readable name
_DISPLAY_NAME_OVERRIDES = {
    HeroType.None_: "None",
    HeroType.MasterOfWhispers: "Master of Whispers",
    HeroType.AcolyteJin: "Acolyte Jin",
    HeroType.AcolyteSousuke: "Acolyte Sousuke",
    HeroType.ZhedShadowhoof: "Zhed Shadowhoof",
    HeroType.GeneralMorgahn: "General Morgahn",
    HeroType.MagridTheSly: "Magrid the Sly",
    HeroType.KeiranThackeray: "Keiran Thackeray",
    HeroType.PyreFierceshot: "Pyre Fierceshot",
    HeroType.MercenaryHero1: "Mercenary 1",
    HeroType.MercenaryHero2: "Mercenary 2",
    HeroType.MercenaryHero3: "Mercenary 3",
    HeroType.MercenaryHero4: "Mercenary 4",
    HeroType.MercenaryHero5: "Mercenary 5",
    HeroType.MercenaryHero6: "Mercenary 6",
    HeroType.MercenaryHero7: "Mercenary 7",
    HeroType.MercenaryHero8: "Mercenary 8",
    HeroType.ZeiRi: "Zei Ri",
}


def get_hero_display_name(hero_id: int) -> str:
    """
    Get the display name for a hero ID.
    
    This is the single source of truth for hero display names.
    
    Args:
        hero_id: Hero ID from HeroType enum
        
    Returns:
        Human-readable display name
    """
    if hero_id == 0:
        return "None"
    
    try:
        hero_type = HeroType(hero_id)
        # Check for override, otherwise use enum name
        return _DISPLAY_NAME_OVERRIDES.get(hero_type, hero_type.name)
    except ValueError:
        return f"Unknown ({hero_id})"


def get_all_hero_options() -> list:
    """
    Get list of all heroes for UI dropdowns.
    
    Returns:
        List of (hero_id, display_name) tuples, sorted alphabetically by name.
        Excludes None_ (hero_id 0).
    """
    options = []
    
    for hero in HeroType:
        if hero.value == 0:
            continue
        options.append((hero.value, get_hero_display_name(hero.value)))
    
    # Sort alphabetically by display name
    options.sort(key=lambda x: x[1])
    return options


def get_mercenary_hero_ids() -> list:
    """
    Get list of mercenary hero IDs.
    
    Returns:
        List of hero IDs for mercenary slots (1-8)
    """
    return [
        HeroType.MercenaryHero1.value,
        HeroType.MercenaryHero2.value,
        HeroType.MercenaryHero3.value,
        HeroType.MercenaryHero4.value,
        HeroType.MercenaryHero5.value,
        HeroType.MercenaryHero6.value,
        HeroType.MercenaryHero7.value,
        HeroType.MercenaryHero8.value,
    ]
