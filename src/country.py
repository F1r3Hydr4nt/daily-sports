"""Country flag for a football competition name, so a league is recognisable at a glance.

The data carries only the competition label (no country field), so this is a conservative name match: ambiguous
labels (Super League, Superliga, Liga 1 ...) get NO flag rather than a guess. Regional-flag emoji for England,
Scotland and Wales; Northern Ireland has no flag emoji so uses the UK flag."""
import re
from html import escape


def _cc(code: str) -> str:
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code.upper())


def _sub(tag: str) -> str:  # England gbeng, Scotland gbsct, Wales gbwls
    return "\U0001F3F4" + "".join(chr(0xE0000 + ord(c)) for c in tag) + "\U000E007F"


# (regex on the lower-cased label, flag, country name); first match wins, so specific rows come first
_RULES = [
    (r"concacaf", "\U0001F30E", "North and Central America"),
    (r"\bafc\b|asian", "\U0001F30F", "Asia"),
    (r"\buefa\b|\beuropa\b|conference league|champions league|^nations league", _cc("EU"), "Europe"),
    (r"\bfifa\b|world cup|friendl|youth international", "\U0001F30D", "International"),
    (r"scottish|premier sports cup|swpl|^premiership", _sub("gbsct"), "Scotland"),
    (r"cymru|welsh", _sub("gbwls"), "Wales"),
    (r"northern irish", _cc("GB"), "Northern Ireland"),
    (r"league of ireland|\bfai\b", _cc("IE"), "Ireland"),
    (r"women'?s super league|^championship$|\befl\b|^league (one|two)$|^national league|premier league|^fa cup|women'?s fa cup|^u18 premier",
     _sub("gbeng"), "England"),
    (r"série a|brasileiro|copa do brasil", _cc("BR"), "Brazil"),
    (r"serie (a|b)|^serie|coppa italia", _cc("IT"), "Italy"),
    (r"ligue (1|2)|coupe de france", _cc("FR"), "France"),
    (r"la liga|segunda divisi|copa del rey", _cc("ES"), "Spain"),
    (r"frauen|dfb|bundesliga(?! 2)|bundesliga 2|^3\. liga|regionalliga", _cc("DE"), "Germany"),
    (r"^2\. liga", _cc("AT"), "Austria"),
    (r"eredivisie|eerste divisie|knvb", _cc("NL"), "Netherlands"),
    (r"primeira liga|ta[cç]a de portugal", _cc("PT"), "Portugal"),
    (r"jupiler|belgian", _cc("BE"), "Belgium"),
    (r"s[uü]per lig|turkish", _cc("TR"), "Turkey"),
    (r"swiss super", _cc("CH"), "Switzerland"),
    (r"allsvenskan", _cc("SE"), "Sweden"),
    (r"eliteserien", _cc("NO"), "Norway"),
    (r"ekstraklasa", _cc("PL"), "Poland"),
    (r"veikkausliiga", _cc("FI"), "Finland"),
    (r"chance liga", _cc("CZ"), "Czechia"),
    (r"1\. hnl", _cc("HR"), "Croatia"),
    (r"premjer-liha|premier liha", _cc("UA"), "Ukraine"),
    (r"^mls|\bnwsl|^major league soccer", _cc("US"), "United States"),
    (r"liga mx", _cc("MX"), "Mexico"),
    (r"liga profesional|argentin", _cc("AR"), "Argentina"),
    (r"a-league", _cc("AU"), "Australia"),
    (r"\bj ?league|j1 league|j2 league", _cc("JP"), "Japan"),
    (r"uae|adib", _cc("AE"), "United Arab Emirates"),
]
_COMPILED = [(re.compile(p), flag, name) for p, flag, name in _RULES]


def _clean(competition) -> str:
    return (competition or "").replace("\xa0", " ").replace("’", "'").split("  ")[0].strip().lower()


def _lookup(competition):
    c = _clean(competition)
    if not c:
        return None
    # stage suffixes after a non-breaking space were turned into spaces: also try the part before it
    for rx, flag, name in _COMPILED:
        if rx.search(c):
            return flag, name
    return None


def competition_flag(competition) -> str:
    hit = _lookup(competition)
    return hit[0] if hit else ""


def competition_html(competition) -> str:
    """Escaped competition label, prefixed by its flag (with the country as a tooltip) when known."""
    label = escape(competition or "")
    hit = _lookup(competition)
    if not hit:
        return label
    return f'<span class="flag" title="{escape(hit[1])}">{hit[0]}</span> {label}'
