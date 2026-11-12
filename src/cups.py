"""Is a football competition a domestic cup? Cup ties are often rotated or thrown by the favourites, so the page
keeps them in their own collapsed table. Continental and international tournaments are not treated as cups."""
import re

_CUP = re.compile(r"\b(cup|copa|supercopa|pokal|coppa|coupe|taca|beker|trophy|shield)\b")
_NOT = ("world cup", "nations league", "champions league", "europa", "conference league", "africa cup", "asian cup",
        "gold cup", "euro ", "copa america", "libertadores", "sudamericana", "club world", "friendl")


def _plain(s: str) -> str:
    return s.lower().replace("ç", "c").replace("é", "e").replace("ã", "a")


def is_cup(competition) -> bool:
    c = _plain(competition or "")
    return bool(c) and not any(n in c for n in _NOT) and bool(_CUP.search(c))
