"""Is a fixture a women's fixture? The competition label is the authority (it says 'Women', 'WTA', 'Frauen', 'LPGA',
or explicitly 'Men's'); team names are only a last resort, because a men's college game can list a team called
'Mississippi U for Women Owls' or 'Centenary (LA) Ladies'."""
import re

_FEM = re.compile(r"\b(women|wta|lpga|wnba|nwsl|wsl|frauen|damen|damallsvenskan|toppserien|girls|ladies)\b|f[eé]minin|femenin|femmin|\bliga f\b|\bw(?:15|25|35|40|50|60|75|80|100)\b")
_MEN = re.compile(r"\bmen['’]?s\b")
_TEAM_SUFFIX = re.compile(r"\s(?:women|w|ladies|feminino|femenino|frauen)(?:\s+u\d{2})?$", re.I)


def is_female(f) -> bool:
    if f.get("sport") == "wnba":
        return True
    comp = (f.get("competition") or "").replace("\xa0", " ").lower()
    if _FEM.search(comp):
        return True
    if _MEN.search(comp):
        return False
    return any(_TEAM_SUFFIX.search((f.get(side) or "").strip()) for side in ("home", "away"))
