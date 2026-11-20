"""Country flag (an inline SVG image, because flag emoji do not render on Windows) for a football competition name, so a league is recognisable at a glance.

The data carries only the competition label (no country field), so this is a conservative name match: ambiguous
labels (Super League, Superliga, Liga 1 ...) get NO flag rather than a guess. England, Scotland and Wales have their own flags;
Northern Ireland uses the UK flag. Images live in src/flags/ and only the ones on the page are embedded (as CSS)."""
import base64
import re
from html import escape
from pathlib import Path

FLAG_DIR = Path(__file__).parent / "flags"


# (regex on the lower-cased label, flag, country name); first match wins, so specific rows come first
_RULES = [
    (r"concacaf", "world", "North and Central America"),
    (r"\bafc\b|asian", "world", "Asia"),
    (r"\buefa\b|\beuropa\b|conference league|champions league|^nations league", "eu", "Europe"),
    (r"\bfifa\b|world cup|friendl|youth international", "world", "International"),
    (r"scottish|premier sports cup|swpl|^premiership", "gb-sct", "Scotland"),
    (r"cymru|welsh", "gb-wls", "Wales"),
    (r"northern irish", "gb", "Northern Ireland"),
    (r"league of ireland|\bfai\b", "ie", "Ireland"),
    (r"women'?s super league|^championship$|\befl\b|^league (one|two)$|^national league|premier league|^fa cup|women'?s fa cup|^u18 premier",
     "gb-eng", "England"),
    (r"série a|brasileiro|copa do brasil", "br", "Brazil"),
    (r"serie (a|b)|^serie|coppa italia", "it", "Italy"),
    (r"ligue (1|2)|coupe de france", "fr", "France"),
    (r"la liga|segunda divisi|copa del rey", "es", "Spain"),
    (r"frauen|dfb|bundesliga(?! 2)|bundesliga 2|^3\. liga|regionalliga", "de", "Germany"),
    (r"^2\. liga", "at", "Austria"),
    (r"eredivisie|eerste divisie|knvb", "nl", "Netherlands"),
    (r"primeira liga|ta[cç]a de portugal", "pt", "Portugal"),
    (r"jupiler|belgian", "be", "Belgium"),
    (r"s[uü]per lig|turkish", "tr", "Turkey"),
    (r"swiss super", "ch", "Switzerland"),
    (r"allsvenskan", "se", "Sweden"),
    (r"eliteserien", "no", "Norway"),
    (r"ekstraklasa", "pl", "Poland"),
    (r"veikkausliiga", "fi", "Finland"),
    (r"chance liga", "cz", "Czechia"),
    (r"1\. hnl", "hr", "Croatia"),
    (r"premjer-liha|premier liha", "ua", "Ukraine"),
    (r"^mls|\bnwsl|^major league soccer", "us", "United States"),
    (r"liga mx", "mx", "Mexico"),
    (r"liga profesional|argentin", "ar", "Argentina"),
    (r"a-league", "au", "Australia"),
    (r"\bj ?league|j1 league|j2 league", "jp", "Japan"),
    (r"uae|adib", "ae", "United Arab Emirates"),
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
    return f'<span class="flag fl-{hit[0]}" title="{escape(hit[1])}"></span> {label}'


def flag_css(codes) -> str:
    """CSS rules (data-URI backgrounds) for just the flag images used on the page."""
    rules = [".flag{display:inline-block;width:1.3em;height:.98em;vertical-align:-.12em;background-size:cover;"
             "background-position:center;border-radius:2px;box-shadow:0 0 0 1px rgba(128,128,128,.45)}"]
    for code in sorted(set(codes)):
        f = FLAG_DIR / f"{code}.svg"
        if f.exists():
            b64 = base64.b64encode(f.read_bytes()).decode()
            rules.append(f".fl-{code}{{background-image:url(data:image/svg+xml;base64,{b64})}}")
    return "".join(rules)


def competition_codes(competitions):
    return {c for c in (competition_flag(x) for x in competitions) if c}
