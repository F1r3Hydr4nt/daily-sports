from html import escape
from .normalise import consensus, flags, normalise
from .window import to_dublin

SPORT_ORDER = ["football", "mlb", "nba", "wnba", "nfl", "ncaa", "nhl", "tennis", "cricket", "golf",
               "mma", "nascar", "rugby", "gaa", "darts", "snooker", "boxing", "racing", "esports"]
LABELS = {"mlb": "MLB", "nba": "NBA", "wnba": "WNBA", "nfl": "NFL", "ncaa": "NCAA", "nhl": "NHL",
          "mma": "MMA", "nascar": "NASCAR", "gaa": "GAA"}

CSS = """
:root{--bg:#fff;--fg:#1b1f24;--muted:#5b6670;--card:#f5f7f9;--line:#d8dee4;--bar:#2f7ae5;--flag:#c2410c;--warn:#b91c1c}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0f1318;--fg:#e6e9ed;--muted:#9aa5b1;--card:#171c23;--line:#2a323c;--bar:#5b9dff;--flag:#fb923c;--warn:#f87171}}
:root[data-theme="dark"]{--bg:#0f1318;--fg:#e6e9ed;--muted:#9aa5b1;--card:#171c23;--line:#2a323c;--bar:#5b9dff;--flag:#fb923c;--warn:#f87171}
*{box-sizing:border-box}body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;max-width:1100px;margin-inline:auto}
h1{font-size:1.4rem;margin:.2rem 0}h2{font-size:1.1rem;margin:1.6rem 0 .5rem}.muted{color:var(--muted);font-size:.85rem}
.wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;background:var(--card);border-radius:8px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{font-size:.8rem;color:var(--muted)}
.bar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--line);min-width:120px}.bar i{display:block;background:var(--bar)}
.bar i:nth-child(2){opacity:.55}.bar i:nth-child(3){opacity:.3}.pct{font-size:.8rem}.model{margin-bottom:8px}
.flag{color:var(--flag);font-weight:600}.warn{border:1px solid var(--warn);color:var(--warn);padding:10px;border-radius:8px;margin:12px 0}
.live{color:var(--warn);font-weight:600}footer{margin-top:2rem;border-top:1px solid var(--line);padding-top:1rem}
"""


def _bar(name, probs):
    p = normalise(probs)
    segs = "".join(f'<i style="width:{v:.1f}%"></i>' for v in p.values())
    label = ", ".join(f"{k} {v:.0f}%" for k, v in p.items())
    return (f'<div class="model"><div class="pct">{escape(name)}: {escape(label)}</div>'
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
    fl = flags([normalise(m["probs"]) for m in pm]) if pm else {"low_confidence": False, "consensus_gap": False, "model_spread": False}
    if len(pm) == 1:
        parts.append('<span class="muted">single source, low confidence</span>')
    if fl["model_spread"] or fl["consensus_gap"]:
        parts.append('<span class="flag">&#9873; models disagree by 5+ pp</span>')
    return "".join(parts)


def render(fixtures, now, skipped, errors=()) -> str:
    now = to_dublin(now)
    by_sport = {}
    for f in fixtures:
        by_sport.setdefault(f["sport"], []).append(f)
    order = [s for s in SPORT_ORDER if s in by_sport] + sorted(s for s in by_sport if s not in SPORT_ORDER)
    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>Daily Sports Research</title><style>{CSS}</style></head><body>'
           f'<h1>Daily sports research</h1><div class="muted">Next 24h from {now:%a %d %b %Y %H:%M} '
           f'(Europe/Dublin). Model predictions only, no bookmaker odds.</div>']
    if errors:
        out.append('<div class="warn">WARNING: quality checks failed: ' + escape("; ".join(errors)) + "</div>")
    for s in order:
        rows = []
        for f in sorted(by_sport[s], key=lambda x: x["kickoff"]):
            t = to_dublin(f["kickoff"])
            live = ' <span class="live">LIVE</span>' if f["status"] == "live" else ""
            rows.append(f'<tr><td>{t:%H:%M}{live}</td><td><strong>{escape(f["home"])}</strong> v '
                        f'{escape(f["away"])}<div class="muted">{escape(f.get("competition", ""))}</div></td>'
                        f'<td>{_models_cell(f)}</td></tr>')
        out.append(f'<h2>{escape(LABELS.get(s, s.title()))}</h2><div class="wrap"><table>'
                   '<thead><tr><th>Time (IST/GMT)</th><th>Match</th><th>Model predictions</th></tr></thead>'
                   f'<tbody>{"".join(rows)}</tbody></table></div>')
    sources = sorted({src for f in fixtures for src in f.get("sources", [])} |
                     {f'{m["source"]} ({m["kind"]})' for f in fixtures for m in f.get("models", [])})
    out.append('<footer><h2>Sources</h2><ul>' + "".join(f"<li>{escape(x)}</li>" for x in sources) + "</ul>")
    if skipped:
        out.append("<h2>Sources skipped</h2><ul>" + "".join(f"<li>{escape(x)}</li>" for x in skipped) + "</ul>")
    out.append(f'<p class="muted">Generated {now:%Y-%m-%d %H:%M} Europe/Dublin. Predictions are statistical '
               f'estimates, not advice; prices and odds move. Please gamble responsibly (18+). '
               f'Support: gamblingcare.ie.</p></footer></body></html>')
    return "".join(out)
