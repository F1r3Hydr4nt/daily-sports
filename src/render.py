import re
from html import escape

from .normalise import flags, normalise
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
@media (max-width:640px){table,thead,tbody,tr,td{display:block}thead{display:none}tr{border-bottom:1px solid var(--line);padding:8px 4px}td{border:0;padding:3px 6px}td[data-label]::before{content:attr(data-label);display:block;font-size:.7rem;color:var(--muted)}}
"""


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
    for m in ms:
        if m.get("score"):
            sc = m["score"]
            parts.append(f'<div class="model pct">{escape(m["name"])} ({escape(m["kind"])}): predicted score '
                         f'{escape(f.get("home", ""))} {sc["home"]:.1f} - {sc["away"]:.1f} {escape(f.get("away", ""))}</div>')
    fl = flags([normalise(m["probs"]) for m in pm]) if len(pm) > 1 else {"consensus_gap": False, "model_spread": False}
    if len(pm) == 1:
        parts.append('<span class="muted">single source, low confidence</span>')
    if fl["model_spread"] or fl["consensus_gap"]:
        parts.append('<span class="flag">&#9873; models disagree by 5+ pp</span>')
    return "".join(parts)


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


def render(fixtures, now, skipped, errors=()) -> str:
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
    if errors:
        out.append('<div class="notes"><h2>WARNING</h2>' + escape("; ".join(errors)) + "</div>")
    if skipped:
        out.append('<div class="notes"><h2>Coverage notes</h2><ul>' + "".join(f"<li>{escape(x)}</li>" for x in skipped) + "</ul></div>")
    out.append("<nav aria-label=\"Sports\">" + "".join(
        f'<a href="#sport-{escape(s)}"><span class="dot" style="background:{HUES.get(s, DEFAULT_HUE)}"></span>'
        f'{escape(name(s))} <span class="count">{len(by_sport[s])}</span></a>' for s in order) + "</nav>")
    for s in order:
        rows = []
        for f in sorted(by_sport[s], key=lambda x: x["kickoff"]):
            t = to_dublin(f["kickoff"])
            live = ' <span class="live">LIVE</span>' if f["status"] == "live" else ""
            day = f'<div class="muted">{t:%a %d %b}</div>' if t.date() != now.date() else ""
            rows.append(f'<tr><td class="t" data-label="Time">{t:%H:%M}{live}{day}</td><td data-label="Match"><strong>'
                        f'{escape(f["home"])}</strong> v {escape(f["away"])}'
                        f'<div class="muted">{escape(f.get("competition", ""))}</div></td>'
                        f'<td data-label="Model predictions">{_models_cell(f)}</td></tr>')
        out.append(f'<section id="sport-{escape(s)}"><h2 class="sport"><i style="background:{HUES.get(s, DEFAULT_HUE)}"></i>'
                   f'{escape(name(s))}</h2>{_legend(by_sport[s])}<div class="wrapt"><table>'
                   '<thead><tr><th>Time (IST/GMT)</th><th>Match</th><th>Model predictions</th></tr></thead>'
                   f'<tbody>{"".join(rows)}</tbody></table></div></section>')
    sources = sorted({src for f in fixtures for src in f.get("sources", [])} |
                     {f'{m["source"]} ({m["kind"]})' for f in fixtures for m in f.get("models", [])})
    out.append('<footer><h2>Sources</h2><ul>' + "".join(f"<li>{escape(x)}</li>" for x in sources) + "</ul>")
    out.append(f'<p>Generated {now:%Y-%m-%d %H:%M} Europe/Dublin. Predictions are statistical estimates, not advice; '
               f'prices and odds move. Please gamble responsibly (18+). Support: gamblingcare.ie.</p></footer></div></body></html>')
    return "".join(out)


def artifact_fragment(doc: str) -> str:
    """Strip the document wrapper: the Artifact host supplies doctype, head and body."""
    title = re.search(r"<title>.*?</title>", doc, re.S).group(0)
    style = re.search(r"<style>.*?</style>", doc, re.S).group(0)
    body = re.search(r"<body>(.*)</body>", doc, re.S).group(1)
    return f"{title}\n{style}\n{body}"
