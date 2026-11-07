import re
from html import escape
from zoneinfo import ZoneInfo

from .normalise import flags, normalise
from .score import predicted_score
from .window import to_dublin

SPORT_ORDER = ["football", "mlb", "nba", "wnba", "nfl", "ncaa", "nhl", "tennis", "cricket", "golf",
               "mma", "nascar", "rugby", "gaa", "darts", "snooker", "boxing", "racing", "esports"]
LABELS = {"mlb": "MLB", "nba": "NBA", "wnba": "WNBA", "nfl": "NFL", "ncaa": "NCAA", "nhl": "NHL",
          "mma": "MMA", "nascar": "NASCAR", "gaa": "GAA", "mls": "MLS"}
# One hue per sport family, used for the nav dot and section rule.
HUES = {"football": "#2f8f5b", "tennis": "#c98a1a", "rugby": "#8a5a2b", "golf": "#4c9a52", "mma": "#b23a3f",
        "nhl": "#3b78b8", "nfl": "#7a4e2d", "mlb": "#b23a3f", "wnba": "#d9731a", "ncaa": "#6b4fa0"}
DEFAULT_HUE = "#5a6778"

CSS = """
:root{--bg:#eef1f5;--panel:#fff;--fg:#18212e;--muted:#5a6778;--line:#d6dde6;--chip:#f1f4f8;
--home:#2f8f5b;--draw:#9aa6b4;--away:#3b6ea8;--flag:#b23a3f;--warn:#b23a3f}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#121821;--panel:#1a222d;--fg:#e6ecf2;--muted:#9aa7b6;--line:#2a3544;--chip:#222c39;
--home:#4fae74;--draw:#6c7a8b;--away:#7fa2d0;--flag:#f08a8d;--warn:#f08a8d;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#121821;--panel:#1a222d;--fg:#e6ecf2;--muted:#9aa7b6;--line:#2a3544;--chip:#222c39;
--home:#4fae74;--draw:#6c7a8b;--away:#7fa2d0;--flag:#f08a8d;--warn:#f08a8d;color-scheme:dark}
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px 48px}
h1{font-size:clamp(1.9rem,5vw,2.8rem);line-height:1.05;margin:28px 0 6px;letter-spacing:-.01em}
.sub{color:var(--muted);margin:0;max-width:68ch}
.notes{margin:16px 0 0;padding:12px 14px;background:var(--panel);border:1px solid var(--line);border-left:5px solid var(--flag);border-radius:8px;font-size:.9rem;max-width:80ch}
.notes h2{font-size:.95rem;margin:0 0 4px}.notes ul{margin:0;padding-left:18px}
nav{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);display:flex;gap:8px;flex-wrap:wrap;padding:10px 0;margin:18px 0 22px;border-bottom:1px solid var(--line)}
nav a{display:inline-flex;align-items:center;gap:7px;text-decoration:none;color:var(--fg);padding:5px 12px;border-radius:999px;background:var(--panel);border:1px solid var(--line);font-weight:600;font-size:.9rem}
nav a:focus-visible{outline:3px solid var(--away);outline-offset:2px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}.count{color:var(--muted);font-weight:500}
section{margin:0 0 36px;scroll-margin-top:70px}
h2.sport{font-size:1.5rem;margin:0 0 8px;display:flex;align-items:center;gap:10px}
h2.sport i{width:6px;height:1.2em;border-radius:3px;display:inline-block}
.legend{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:.82rem;margin:0 0 8px}
.legend span::before{content:"";display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:5px;vertical-align:-1px;background:var(--c)}
.wrapt{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px}
table{width:100%;border-collapse:collapse}
th,td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font-size:.78rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
tr:last-child td{border-bottom:0}
td.t{white-space:nowrap;font-weight:600;font-variant-numeric:tabular-nums}
.muted{color:var(--muted);font-size:.82rem;font-weight:400}
.model{margin-bottom:8px}.pct{font-size:.8rem;color:var(--muted)}
.bar{display:flex;height:20px;border-radius:5px;overflow:hidden;background:var(--line);min-width:170px}
.seg{display:block;height:100%;color:#fff;font:600 .72rem/20px system-ui,sans-serif;text-align:center;overflow:hidden;white-space:nowrap}
.seg.home{background:var(--home)}.seg.draw{background:var(--draw)}.seg.away{background:var(--away)}
.flag{color:var(--flag);font-weight:600}.live{color:var(--warn);font-weight:700}
footer{border-top:1px solid var(--line);padding-top:16px;color:var(--muted);font-size:.85rem}
footer h2{font-size:.95rem;color:var(--fg)}footer p{max-width:80ch}
.off{display:none!important}
.controls{display:flex;flex-wrap:wrap;gap:12px 20px;align-items:center;margin:16px 0 0;padding:12px 14px;background:var(--panel);border:1px solid var(--line);border-radius:8px;font-size:.9rem}
.controls label{display:flex;align-items:center;gap:8px;font-weight:600}
.controls input{width:5.5em;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);font:inherit}
.controls .muted{flex-basis:100%}
.controls select{padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);font:inherit}
.score{font-size:1.25rem;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
td.sc{min-width:9.5em}
@media (max-width:640px){table,thead,tbody,tr,td{display:block}thead{display:none}tr{border-bottom:1px solid var(--line);padding:8px 4px}td{border:0;padding:3px 6px}td[data-label]::before{content:attr(data-label);display:block;font-size:.7rem;color:var(--muted)}}
"""


DEFAULT_MIN = {"football": 2.0, "nhl": 0.75}
NUM = lambda v: f"{v:g}"

CONTROLS = (
    '<div class="controls" role="group" aria-label="Filters and sort">'
    '<label for="min-football">Football: min predicted margin (goals)'
    f'<input id="min-football" type="number" min="0" step="0.25" value="{NUM(DEFAULT_MIN["football"])}"></label>'
    '<label for="min-nhl">NHL: min predicted margin (goals)'
    f'<input id="min-nhl" type="number" min="0" step="0.25" value="{NUM(DEFAULT_MIN["nhl"])}"></label>'
    '<label for="sort-by">Sort'
    '<select id="sort-by"><option value="margin" selected>Largest margin first</option>'
    '<option value="time">Kick-off time</option></select></label>'
    '<span id="filter-status" class="muted" role="status">%STATUS%</span>'
    '<span class="muted">Margin = predicted goals for the favourite minus the other side. Football scores are derived '
    'from Predicd win probabilities; NHL scores are Odds Shark\'s. Set 0 to see every modelled game. '
    'Other sports are not filtered.</span></div>')

SCRIPT = (
    "<script>(function(){var inputs={football:document.getElementById('min-football'),"
    "nhl:document.getElementById('min-nhl')},sortBy=document.getElementById('sort-by');"
    "function key(tr,mode){var m=tr.getAttribute('data-margin'),t=tr.getAttribute('data-time')||'';"
    "return mode==='margin'?[m===null?1:0,m===null?0:-parseFloat(m),t]:[0,0,t];}"
    "function cmp(a,b){for(var i=0;i<a.length;i++){if(a[i]<b[i])return -1;if(a[i]>b[i])return 1;}return 0;}"
    "function apply(){var shown=0,total=0,mode=sortBy.value;"
    "document.querySelectorAll('section[data-section]').forEach(function(sec){var s=sec.getAttribute('data-section'),"
    "box=inputs[s],min=box?parseFloat(box.value):NaN,n=0,body=sec.querySelector('tbody'),"
    "rows=Array.prototype.slice.call(body.querySelectorAll('tr'));"
    "rows.sort(function(a,b){return cmp(key(a,mode),key(b,mode));}).forEach(function(tr){body.appendChild(tr);});"
    "rows.forEach(function(tr){var m=tr.getAttribute('data-margin'),"
    "hide=!!(box&&!isNaN(min)&&m!==null&&parseFloat(m)<min);tr.classList.toggle('off',hide);if(!hide)n++;total++;});"
    "sec.classList.toggle('off',n===0);var a=document.querySelector('nav a[href=\"#sport-'+s+'\"]');"
    "if(a){a.classList.toggle('off',n===0);a.querySelector('.count').textContent=n;}shown+=n;});"
    "document.getElementById('filter-status').textContent='Showing '+shown+' of '+total+' modelled fixtures.';}"
    "Object.keys(inputs).forEach(function(k){inputs[k].addEventListener('input',apply);});"
    "sortBy.addEventListener('change',apply);apply();})();</script>")


def _bar(name, probs):
    p = normalise(probs)
    keys = ["home", "draw", "away"] if "draw" in p else ["home", "away"]
    segs = "".join(f'<span class="seg {k}" style="width:{p[k]:.1f}%">{p[k]:.0f}%</span>' if p[k] >= 9
                   else f'<span class="seg {k}" style="width:{p[k]:.1f}%"></span>' for k in keys if k in p)
    label = ", ".join(f"{k} {p[k]:.0f}%" for k in keys if k in p)
    return (f'<div class="model"><div class="pct">{escape(name)}</div>'
            f'<div class="bar" role="img" aria-label="{escape(name)}: {escape(label)}">{segs}</div></div>')


def _models_cell(f):
    ms = f.get("models", [])
    if not ms:
        return '<span class="muted">no model available</span>'
    pm = [m for m in ms if m.get("probs")]
    parts = [_bar(f'{m["name"]} ({m["kind"]})', m["probs"]) for m in pm]
    fl = flags([normalise(m["probs"]) for m in pm]) if len(pm) > 1 else {"consensus_gap": False, "model_spread": False}
    if len(pm) == 1:
        parts.append('<span class="muted">single source, low confidence</span>')
    if fl["model_spread"] or fl["consensus_gap"]:
        parts.append('<span class="flag">&#9873; models disagree by 5+ pp</span>')
    return "".join(parts)


def _score_cell(f):
    ps = predicted_score(f)
    if not ps:
        return '<span class="muted">&ndash;</span>'
    src = next((m for m in f.get("models", []) if m.get("score" if not ps["derived"] else "probs")), {})
    if ps["derived"]:
        note = f'derived from win probabilities ({escape(src.get("name", "model"))}); not a published score'
    else:
        note = f'published by {escape(src.get("name", "the source"))}'
    fav = f.get("home", "") if ps["margin"] > 0 else f.get("away", "") if ps["margin"] < 0 else ""
    lead = f' &middot; {escape(fav)} ahead' if fav else " &middot; level"
    return (f'<div class="score">{ps["home"]:.1f} - {ps["away"]:.1f}</div>'
            f'<div class="muted">margin {abs(ps["margin"]):.1f}{lead}</div><div class="muted">{note}</div>')


def _legend(rows):
    three = any("draw" in m.get("probs", {}) for f in rows for m in f.get("models", []))
    two = any(m.get("probs") and "draw" not in m["probs"] for f in rows for m in f.get("models", []))
    if not (three or two):
        return ""
    items = ['<span style="--c:var(--home)">Home</span>']
    if three:
        items.append('<span style="--c:var(--draw)">Draw</span>')
    items.append('<span style="--c:var(--away)">Away</span>')
    return f'<div class="legend">{"".join(items)}</div>'


def render(fixtures, now, skipped, errors=(), hidden=0) -> str:
    now = to_dublin(now)
    by_sport = {}
    for f in fixtures:
        by_sport.setdefault(f["sport"], []).append(f)
    order = [s for s in SPORT_ORDER if s in by_sport] + sorted(s for s in by_sport if s not in SPORT_ORDER)
    name = lambda s: LABELS.get(s, s.title())
    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>Daily Sports Research</title><style>{CSS}</style></head><body><div class="wrap">'
           f'<h1>Daily sports research</h1><p class="sub">Next 24 hours from {now:%a %d %b %Y %H:%M} '
           f'(Europe/Dublin): {len(fixtures)} fixtures across {len(order)} sports. Free model predictions only, '
           f'no bookmaker odds. All times are Irish time.</p>']
    if hidden:
        out.append(f'<p class="sub">Only fixtures with a model prediction are shown: {hidden} '
                   f'{"fixture" if hidden == 1 else "fixtures"} without a model prediction '
                   f'{"is" if hidden == 1 else "are"} not shown.</p>')
    def margin_of(f):
        ps = predicted_score(f)
        return abs(ps["margin"]) if ps else None

    def hidden_by_default(f, s):
        m = margin_of(f)
        return s in DEFAULT_MIN and m is not None and m < DEFAULT_MIN[s]

    shown = {s: sum(not hidden_by_default(f, s) for f in by_sport[s]) for s in order}
    status = f"Showing {sum(shown.values())} of {len(fixtures)} modelled fixtures."
    if errors:
        out.append('<div class="notes"><h2>WARNING</h2>' + escape("; ".join(errors)) + "</div>")
    out.append(CONTROLS.replace("%STATUS%", status))
    if skipped:
        out.append('<div class="notes"><h2>Coverage notes</h2><ul>' + "".join(f"<li>{escape(x)}</li>" for x in skipped) + "</ul></div>")
    out.append("<nav aria-label=\"Sports\">" + "".join(
        f'<a href="#sport-{escape(s)}"{" class=off" if not shown[s] else ""}><span class="dot" style="background:{HUES.get(s, DEFAULT_HUE)}"></span>'
        f'{escape(name(s))} <span class="count">{shown[s]}</span></a>' for s in order) + "</nav>")
    for s in order:
        rows = []
        ordered = sorted(by_sport[s], key=lambda x: (margin_of(x) is None, -(margin_of(x) or 0), x["kickoff"]))
        for f in ordered:
            t = to_dublin(f["kickoff"])
            live = ' <span class="live">LIVE</span>' if f["status"] == "live" else ""
            day = f'<div class="muted">{t:%a %d %b}</div>' if t.date() != now.date() else ""
            m = margin_of(f)
            attrs = (f' data-sport="{escape(s)}" data-time="{f["kickoff"].astimezone(ZoneInfo("UTC")):%Y%m%d%H%M}"'
                     + (f' data-margin="{m:.2f}"' if m is not None else "")
                     + (' class="off"' if hidden_by_default(f, s) else ""))
            rows.append(f'<tr{attrs}><td class="t" data-label="Time">{t:%H:%M}{live}{day}</td><td data-label="Match"><strong>'
                        f'{escape(f["home"])}</strong> v {escape(f["away"])}'
                        f'<div class="muted">{escape(f.get("competition", ""))}</div></td>'
                        f'<td class="sc" data-label="Predicted score">{_score_cell(f)}</td>'
                        f'<td data-label="Model predictions">{_models_cell(f)}</td></tr>')
        out.append(f'<section id="sport-{escape(s)}" data-section="{escape(s)}"{" class=off" if not shown[s] else ""}>'
                   f'<h2 class="sport"><i style="background:{HUES.get(s, DEFAULT_HUE)}"></i>'
                   f'{escape(name(s))}</h2>{_legend(by_sport[s])}<div class="wrapt"><table>'
                   '<thead><tr><th>Time (IST/GMT)</th><th>Match</th><th>Predicted score</th><th>Model predictions</th></tr></thead>'
                   f'<tbody>{"".join(rows)}</tbody></table></div></section>')
    sources = sorted({src for f in fixtures for src in f.get("sources", [])} |
                     {f'{m["source"]} ({m["kind"]})' for f in fixtures for m in f.get("models", [])})
    out.append('<footer><h2>Sources</h2><ul>' + "".join(f"<li>{escape(x)}</li>" for x in sources) + "</ul>")
    out.append(f'<p>Generated {now:%Y-%m-%d %H:%M} Europe/Dublin. Predictions are statistical estimates, not advice; '
               f'prices and odds move. Please gamble responsibly (18+). Support: gamblingcare.ie.</p></footer></div>' + SCRIPT + '</body></html>')
    return "".join(out)


def artifact_fragment(doc: str) -> str:
    """Strip the document wrapper: the Artifact host supplies doctype, head and body."""
    title = re.search(r"<title>.*?</title>", doc, re.S).group(0)
    style = re.search(r"<style>.*?</style>", doc, re.S).group(0)
    body = re.search(r"<body>(.*)</body>", doc, re.S).group(1)
    return f"{title}\n{style}\n{body}"
