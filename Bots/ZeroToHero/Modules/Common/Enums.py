from enum import IntEnum

class HeroID(IntEnum):
    None_ = 0
    Norgu = 1
    Goren = 2
    Tahlkora = 3
    MasterOfWhispers = 4
    AcolyteJin = 5
    Koss = 6
    Dunkoro = 7
    AcolyteSousuke = 8
    Melonni = 9
    ZhedShadowhoof = 10
    GeneralMorgahn = 11
    MagridTheSly = 12
    Zenmai = 13
    Olias = 14
    Razah = 15
    MOX = 16
    KeiranThackeray = 17
    Jora = 18
    PyreFierceshot = 19
    Anton = 20
    Livia = 21
    Hayda = 22
    Kahmu = 23
    Gwen = 24
    Xandra = 25
    Vekk = 26
    Ogden = 27
    MercenaryHero1 = 28
    MercenaryHero2 = 29
    MercenaryHero3 = 30
    MercenaryHero4 = 31
    MercenaryHero5 = 32
    MercenaryHero6 = 33
    MercenaryHero7 = 34
    MercenaryHero8 = 35
    Miku = 36
    ZeiRi = 37

    @classmethod
    def get_nice_name(cls, val):
        """Converts Enum name to a spaced, readable string."""
        if val == cls.None_: 
            return "None"
        
        try:
            name = cls(val).name
        except ValueError:
            return f"Unknown ({val})"

        # Manual overrides for specific cases
        overrides = {
            "MasterOfWhispers": "Master of Whispers",
            "AcolyteJin": "Acolyte Jin",
            "AcolyteSousuke": "Acolyte Sousuke",
            "ZhedShadowhoof": "Zhed Shadowhoof",
            "GeneralMorgahn": "General Morgahn",
            "MagridTheSly": "Magrid the Sly",
            "KeiranThackeray": "Keiran Thackeray",
            "PyreFierceshot": "Pyre Fierceshot",
            "MercenaryHero1": "Mercenary Hero 1",
            "MercenaryHero2": "Mercenary Hero 2",
            "MercenaryHero3": "Mercenary Hero 3",
            "MercenaryHero4": "Mercenary Hero 4",
            "MercenaryHero5": "Mercenary Hero 5",
            "MercenaryHero6": "Mercenary Hero 6",
            "MercenaryHero7": "Mercenary Hero 7",
            "MercenaryHero8": "Mercenary Hero 8",
            "ZeiRi": "Zei Ri"
        }
        
        if name in overrides:
            return overrides[name]
            
        return name
