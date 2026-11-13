import re
from html import escape
from zoneinfo import ZoneInfo

from .normalise import flags, normalise
from .cups import is_cup
from .preview import predicd_top, star
from .score import favourite, predicted_score, win_gap
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
.scorebox{display:inline-block;padding:6px 12px;border-radius:8px;background:var(--chip);border:2px solid var(--home);margin-bottom:4px}
.scorebox .score{font-size:1.5rem;font-weight:800;line-height:1.2;font-variant-numeric:tabular-nums;white-space:nowrap}
.scorebox.derived{border-style:dashed}
.seccontrol{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;margin:0 0 10px;padding:10px 12px;background:var(--panel);border:2px solid var(--home);border-radius:8px;font-size:.95rem}
.seccontrol label{display:flex;align-items:center;gap:8px;font-weight:700}
.seccontrol input{width:5.5em;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);font:inherit}
td.sc{min-width:9.5em}
span.star{color:#d99a00;font-size:1.55rem;line-height:1;vertical-align:-2px;margin-right:4px;text-shadow:0 0 1px rgba(0,0,0,.35)}
.starbadge{display:inline-block;margin-top:6px;padding:3px 10px;border-radius:999px;background:#d99a00;color:#1b1500;font-weight:700;font-size:.8rem}
.starstrip{margin:14px 0 0;padding:10px 14px;border:2px solid #d99a00;border-radius:8px;background:var(--panel);font-size:.9rem}
.starstrip h2{font-size:1rem;margin:0 0 4px}.starstrip ul{margin:0;padding-left:18px}
.fsprev{margin-top:8px;padding:8px 10px;border:1px solid var(--line);border-left:4px solid #d99a00;border-radius:8px;background:var(--chip);font-size:.85rem}
.fsprev .fspick{margin:4px 0}
.fsprev details>summary{cursor:pointer;font-weight:600;margin-top:4px}
.fsprev details p{margin:6px 0}
details.cups{margin:14px 0 0;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
details.cups>summary{cursor:pointer;list-style:none;display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;padding:12px 14px;border-radius:10px;font-size:1rem}
details.cups>summary::-webkit-details-marker{display:none}
details.cups>summary::before{content:"\\25B8";font-size:1.1rem;transition:transform .15s;display:inline-block;width:1em}
details.cups[open]>summary::before{transform:rotate(90deg)}
details.cups>summary:hover{background:var(--chip)}
details.cups>summary:focus-visible{outline:3px solid var(--away);outline-offset:2px}
details.cups[open]>summary{border-bottom:1px solid var(--line);border-radius:10px 10px 0 0}
details.cups .cup-count{background:var(--chip);border:1px solid var(--line);border-radius:999px;padding:1px 10px;font-size:.82rem;font-weight:600}
details.cups .wrapt{border:0;border-radius:0 0 10px 10px}
@media (prefers-reduced-motion:reduce){details.cups>summary::before{transition:none}}
@media (max-width:640px){table,thead,tbody,tr,td{display:block}thead{display:none}tr{border-bottom:1px solid var(--line);padding:8px 4px}td{border:0;padding:3px 6px}td[data-label]::before{content:attr(data-label);display:block;font-size:.7rem;color:var(--muted)}}
"""


DEFAULT_MIN = {"football": 2.0, "nhl": 0.75, "nfl": 6.5, "tennis": 50.0}
NUM = lambda v: f"{v:g}"

SEC_CONTROL = {
    "football": ("min-football", "Football: only show games with a predicted margin of at least", "goals"),
    "nhl": ("min-nhl", "NHL: only show games with a predicted margin of at least", "goals"),
    "nfl": ("min-nfl", "NFL: only show games with a predicted margin of at least", "points"),
    "tennis": ("min-tennis", "Tennis: only show matches where the difference between the two players' win probabilities is at least", "percentage points (75% v 25% = 50)"),
}


def _sec_control(sport):
    if sport not in SEC_CONTROL:
        return ""
    box, text, unit = SEC_CONTROL[sport]
    if sport == "tennis":
        v = NUM(DEFAULT_MIN[sport])
        return ('<div class="seccontrol" role="group" aria-label="tennis filter">'
                f'<label for="{box}-slider">{escape(text)}</label>'
                f'<input id="{box}-slider" type="range" min="0" max="100" step="1" value="{v}" style="flex:1 1 220px;width:auto">'
                f'<input id="{box}" type="number" min="0" max="100" step="1" value="{v}"> <span>{escape(unit)}</span>'
                '<span class="muted">(0 = show every modelled match; drag the slider or type a number)</span></div>')
    return (f'<div class="seccontrol" role="group" aria-label="{escape(sport)} filter">'
            f'<label for="{box}">{escape(text)}'
            f'<input id="{box}" type="number" min="0" step="{"1" if sport == "tennis" else "0.25"}" value="{NUM(DEFAULT_MIN[sport])}"> {unit}</label>'
            f'<span class="muted">(0 = show every modelled game)</span></div>')


CONTROLS = (
    '<div class="controls" role="group" aria-label="Sort and status">'
    '<label for="sort-by">Sort'
    '<select id="sort-by"><option value="margin" selected>Largest margin first</option>'
    '<option value="time">Kick-off time</option></select></label>'
    '<span id="filter-status" class="muted" role="status">%STATUS%</span>'
    '<span class="muted">Layout v5 (cup-games accordion, Flashscore previews and STAR). Bold = the model favourite (no bold when there is no clear favourite or the models disagree): the predicted score is in the highlighted box in each row, and each table has its '
    'own margin filter just above it. Margin = predicted goals (NFL: points) for the favourite minus the other side; tennis: the favourite\'s win % minus the other player\'s, in percentage points. Football '
    'scores are derived from Predicd win probabilities (dashed box); NHL and NFL scores are published by Odds Shark '
    '(solid box). Other sports are not filtered.</span></div>')

SCRIPT = (
    "<script>(function(){var inputs={football:document.getElementById('min-football'),"
    "nhl:document.getElementById('min-nhl'),nfl:document.getElementById('min-nfl'),tennis:document.getElementById('min-tennis')},"
    "sortBy=document.getElementById('sort-by');"
    "function key(tr,mode){var m=tr.getAttribute('data-margin'),t=tr.getAttribute('data-time')||'';"
    "return mode==='margin'?[m===null?1:0,m===null?0:-parseFloat(m),t]:[0,0,t];}"
    "function cmp(a,b){for(var i=0;i<a.length;i++){if(a[i]<b[i])return -1;if(a[i]>b[i])return 1;}return 0;}"
    "function apply(){var shown=0,total=0,mode=sortBy.value;"
    "document.querySelectorAll('section[data-section]').forEach(function(sec){var s=sec.getAttribute('data-section'),"
    "box=inputs[s],min=box?parseFloat(box.value):NaN,n=0,all=0;"
    "sec.querySelectorAll('tbody').forEach(function(body){var rows=Array.prototype.slice.call(body.querySelectorAll('tr')),k=0;"
    "rows.sort(function(a,b){return cmp(key(a,mode),key(b,mode));}).forEach(function(tr){body.appendChild(tr);});"
    "rows.forEach(function(tr){var m=tr.getAttribute('data-margin'),"
    "hide=!!(box&&!isNaN(min)&&m!==null&&parseFloat(m)<min);tr.classList.toggle('off',hide);if(!hide){k++;n++;}all++;total++;});"
    "var w=body.closest('.wrapt');if(w)w.classList.toggle('off',k===0);"
    "var d=body.closest('details');if(d){var cc=d.querySelector('.cup-count');if(cc)cc.textContent=k+' of '+rows.length+' shown';var ce=d.querySelector('.cup-empty');if(ce)ce.classList.toggle('off',k!==0);}});"
    "var em=sec.querySelector('.empty');if(em)em.classList.toggle('off',n!==0);"
    "var a=document.querySelector('nav a[href=\"#sport-'+s+'\"]');if(a){a.querySelector('.count').textContent=n+' of '+all;}"
    "var sc=sec.querySelector('.sec-count');if(sc)sc.textContent=n+' of '+all+' shown';shown+=n;});"
    "document.getElementById('filter-status').textContent='Showing '+shown+' of '+total+' modelled fixtures.';}"
    "var ts=document.getElementById('min-tennis-slider');if(ts&&inputs.tennis){ts.addEventListener('input',function(){inputs.tennis.value=ts.value;apply();});"
    "inputs.tennis.addEventListener('input',function(){ts.value=inputs.tennis.value;});}"
    "Object.keys(inputs).forEach(function(k){if(inputs[k])inputs[k].addEventListener('input',apply);});"
    "sortBy.addEventListener('change',apply);apply();})();</script>")


def _bar(name, probs):
    p = normalise(probs)
    keys = ["home", "draw", "away"] if "draw" in p else ["home", "away"]
    segs = "".join(f'<span class="seg {k}" style="width:{p[k]:.1f}%">{p[k]:.0f}%</span>' if p[k] >= 9
                   else f'<span class="seg {k}" style="width:{p[k]:.1f}%"></span>' for k in keys if k in p)
    label = ", ".join(f"{k} {p[k]:.0f}%" for k in keys if k in p)
    return (f'<div class="model"><div class="pct">{escape(name)}</div>'
            f'<div class="bar" role="img" aria-label="{escape(name)}: {escape(label)}">{segs}</div></div>')


FACTOR_LABEL = {"elo": "Elo", "h2h": "H2H", "last10": "Last 10", "h2hSurf": "H2H on surface", "surface": "Surface",
                "last10surf": "Last 10 on surface"}


def _factors_line(f, m):
    """The favourite's win chance on each factor a model publishes (SetProb's own components, not separate models)."""
    fac, p = m.get("factors"), m.get("probs") or {}
    if not fac or "home" not in p or "away" not in p:
        return ""
    fav_home = p["home"] >= p["away"]
    bits = " &middot; ".join(f'{escape(FACTOR_LABEL.get(k, k))} {(v if fav_home else 100 - v):.0f}%' for k, v in fac.items())
    return (f'<div class="muted">{escape(m["name"])} factors, chance for {escape(f["home"] if fav_home else f["away"])}: {bits}</div>')


def _models_cell(f):
    ms = f.get("models", [])
    if not ms:
        return '<span class="muted">no model available</span>'
    parts = []
    for m in ms:
        label = f'{m["name"]} ({m["kind"]})'
        if m.get("probs"):
            parts.append(_bar(label, m["probs"]) + _factors_line(f, m))
        elif m.get("score"):
            parts.append(f'<div class="model"><div class="pct">{escape(label)}: '
                         f'<strong>{m["score"]["home"]:.1f} - {m["score"]["away"]:.1f}</strong></div></div>')
    pm = [m for m in ms if m.get("probs")]
    fl = flags([normalise(m["probs"]) for m in pm]) if len(pm) > 1 else {"consensus_gap": False, "model_spread": False}
    if len(ms) == 1:
        parts.append('<span class="muted">single source, low confidence</span>')
    if fl["model_spread"] or fl["consensus_gap"]:
        parts.append('<span class="flag">&#9873; models disagree by 5+ pp</span>')
    return "".join(parts)


def _pick_label(pick):
    sel, mk = pick.get("selection") or "", pick["market"]
    return f"{sel} ({mk})" if sel and sel != mk else mk


def _top_label(f):
    top = predicd_top(f)
    pct = next(m["probs"][top] for m in f["models"] if m.get("name") == "Predicd")
    return f'{f["home"] if top == "home" else f["away"] if top == "away" else "the draw"} ({pct:.0f}%)'


STAR_HTML = ('<span class="star" title="Flashscore pick matches Predicd" aria-label="Flashscore pick matches Predicd">'
             '&#9733;</span>')


def _preview_block(f):
    pv = f.get("preview")
    if not pv:
        return ""
    out = ['<div class="fsprev">']
    if star(f):
        top = predicd_top(f)
        label = f["home"] if top == "home" else f["away"] if top == "away" else "Draw"
        pct = next(m["probs"][top] for m in f["models"] if m.get("name") == "Predicd")
        out.append(f'<div class="starbadge" title="Flashscore\'s pick includes Predicd\'s most likely result">&#9733; Flashscore pick matches Predicd '
                   f'(Predicd favours {escape(label)} {pct:.0f}%)</div>')
    pick = pv.get("pick") or {}
    if pick.get("market"):
        sel = f' &middot; {escape(pick["selection"])}' if pick.get("selection") else ""
        out.append(f'<div class="fspick"><strong>Flashscore pick:</strong> {escape(pick["market"])}{sel}</div>')
    else:
        out.append('<div class="fspick muted">Flashscore pick: no market named in the preview</div>')
    by = f' by {escape(pv["author"])}' if pv.get("author") else ""
    link = f'<a href="{escape(pv["url"])}" rel="noopener">Read the full Flashscore preview</a>'
    st, syn = pv.get("strengths") or {}, pv.get("synopsis")
    if syn or st:
        body = "".join(f'<p><strong>{escape(f[side])}:</strong> {escape(st[side])}</p>' for side in ("home", "away") if st.get(side))
        body += f'<p>{escape(syn)}</p>' if syn else ""
        out.append(f'<details><summary>Preview synopsis</summary>{body}<p class="muted">Summary of the Flashscore preview{by} '
                   f'(written by Claude, not Flashscore\'s own words). {link}</p></details>')
    else:
        out.append(f'<div class="muted">Flashscore preview{by}. {link}</div>')
    out.append("</div>")
    return "".join(out)


def _score_cell(f):
    ps = predicted_score(f)
    if not ps:
        gap = win_gap(f)
        if gap is None:
            return '<span class="muted">&ndash;</span>'
        m = next(m for m in f["models"] if m.get("probs") and "draw" not in m["probs"])
        fav_home = m["probs"]["home"] >= m["probs"]["away"]
        pct = max(m["probs"]["home"], m["probs"]["away"]) / (m["probs"]["home"] + m["probs"]["away"]) * 100
        return (f'<div class="scorebox"><div class="score">{pct:.0f}%</div></div>'
                f'<div><strong>gap {gap:.0f} pts</strong> &middot; {escape(f["home"] if fav_home else f["away"])} favoured</div>'
                f'<div class="muted">win probability published by {escape(m.get("name", "the source"))}; no score</div>')
    src = next((m for m in f.get("models", []) if m.get("score" if not ps["derived"] else "probs")), {})
    if ps["derived"]:
        note = f'derived from win probabilities ({escape(src.get("name", "model"))}); not a published score'
    else:
        note = f'published by {escape(src.get("name", "the source"))}'
    fav = f.get("home", "") if ps["margin"] > 0 else f.get("away", "") if ps["margin"] < 0 else ""
    lead = f' &middot; {escape(fav)} ahead' if fav else " &middot; level"
    cls = "scorebox derived" if ps["derived"] else "scorebox"
    return (f'<div class="{cls}"><div class="score">{ps["home"]:.1f} - {ps["away"]:.1f}</div></div>'
            f'<div><strong>margin {abs(ps["margin"]):.1f}</strong>{lead}</div><div class="muted">{note}</div>')


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
        if ps:
            return abs(ps["margin"])
        return win_gap(f)

    def hidden_by_default(f, s):
        m = margin_of(f)
        return s in DEFAULT_MIN and m is not None and m < DEFAULT_MIN[s]

    shown = {s: sum(not hidden_by_default(f, s) for f in by_sport[s]) for s in order}
    status = f"Showing {sum(shown.values())} of {len(fixtures)} modelled fixtures."
    if errors:
        out.append('<div class="notes"><h2>WARNING</h2>' + escape("; ".join(errors)) + "</div>")
    out.append(CONTROLS.replace("%STATUS%", status))
    starred = [f for f in fixtures if star(f)]
    if starred:
        items = "".join(f'<li><span class="star" style="font-size:1.1rem">&#9733;</span> <strong>{escape(f["home"])} v {escape(f["away"])}</strong> '
                        f'({to_dublin(f["kickoff"]):%a %H:%M}, {escape(f.get("competition", ""))}): Flashscore '
                        f'{escape(_pick_label(f["preview"]["pick"]))}, Predicd favours {escape(_top_label(f))}</li>' for f in starred)
        out.append('<div class="starstrip" role="note"><h2>&#9733; Flashscore agrees with Predicd: '
                   f'{len(starred)} {"match" if len(starred) == 1 else "matches"} (shown here whatever the filters say)</h2><ul>{items}</ul></div>')
    if skipped:
        out.append('<div class="notes"><h2>Coverage notes</h2><ul>' + "".join(f"<li>{escape(x)}</li>" for x in skipped) + "</ul></div>")
    out.append("<nav aria-label=\"Sports\">" + "".join(
        f'<a href="#sport-{escape(s)}"><span class="dot" style="background:{HUES.get(s, DEFAULT_HUE)}"></span>'
        f'{escape(name(s))} <span class="count">{shown[s]} of {len(by_sport[s])}</span></a>' for s in order) + "</nav>")
    def names_html(f):
        """Bold marks the model's favourite only (never merely the first-listed side); no bold when there is none."""
        fav = favourite(f)
        h, a = escape(f["home"]), escape(f["away"])
        b = lambda x: f'<strong title="Model favourite">{x}</strong>'
        return f'{b(h) if fav == "home" else h} v {b(a) if fav == "away" else a}'

    def row_html(f, s):
        t = to_dublin(f["kickoff"])
        live = ' <span class="live">LIVE</span>' if f["status"] == "live" else ""
        day = f'<div class="muted">{t:%a %d %b}</div>' if t.date() != now.date() else ""
        m = margin_of(f)
        star_html = STAR_HTML if star(f) else ""
        attrs = (f' data-sport="{escape(s)}" data-time="{f["kickoff"].astimezone(ZoneInfo("UTC")):%Y%m%d%H%M}"'
                 + (f' data-margin="{m:.2f}"' if m is not None else "")
                 + (' class="off"' if hidden_by_default(f, s) else ""))
        return (f'<tr{attrs}><td class="t" data-label="Time">{t:%H:%M}{live}{day}</td><td data-label="Match">'
                f'{star_html}{names_html(f)}'
                f'<div class="muted">{escape(f.get("competition", ""))}</div>{_preview_block(f)}</td>'
                f'<td class="sc" data-label="Predicted score">{_score_cell(f)}</td>'
                f'<td data-label="Model predictions">{_models_cell(f)}</td></tr>')

    def table_html(group, s):
        vis = sum(not hidden_by_default(f, s) for f in group)
        return (f'<div class="wrapt{" off" if not vis else ""}"><table>'
                '<thead><tr><th>Time (IST/GMT)</th><th>Match</th><th>Predicted score</th><th>Model predictions</th></tr></thead>'
                f'<tbody>{"".join(row_html(f, s) for f in group)}</tbody></table></div>')

    for s in order:
        ordered = sorted(by_sport[s], key=lambda x: (margin_of(x) is None, -(margin_of(x) or 0), x["kickoff"]))
        cups = [f for f in ordered if s == "football" and is_cup(f.get("competition"))]
        main = [f for f in ordered if f not in cups]
        empty = not shown[s]
        body = table_html(main, s) if main else ""
        if cups:
            cup_vis = sum(not hidden_by_default(f, s) for f in cups)
            body += ('<details class="cups"><summary><strong>Cup games</strong>'
                     f'<span class="cup-count">{cup_vis} of {len(cups)} shown</span>'
                     '<span class="muted">Cup ties are often rotated or thrown by the favourites, so predictions are less '
                     'reliable. Click to open.</span></summary>'
                     f'<p class="cup-empty muted{"" if not cup_vis else " off"}" style="padding:12px 14px;margin:0">No cup games at or above this '
                     f'margin. Lower the football filter above to see the {len(cups)} modelled cup '
                     f'{"game" if len(cups) == 1 else "games"}.</p>' + table_html(cups, s) + '</details>')
        out.append(f'<section id="sport-{escape(s)}" data-section="{escape(s)}">'
                   f'<h2 class="sport"><i style="background:{HUES.get(s, DEFAULT_HUE)}"></i>'
                   f'{escape(name(s))} <span class="sec-count muted">{shown[s]} of {len(by_sport[s])} shown</span></h2>{_sec_control(s)}'
                   f'<p class="empty muted{"" if empty else " off"}">No games at or above this margin. '
                   f'Lower the filter above to see the {len(by_sport[s])} modelled '
                   f'{"game" if len(by_sport[s]) == 1 else "games"}.</p>'
                   f'{_legend(by_sport[s])}{body}</section>')
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
