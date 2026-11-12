"""Flashscore (www.flashscore.com): the day's football feed (the one its own page loads), and the written match
previews, which end in a 'Betting Analysis' paragraph naming the market Flashscore's writer picked.
We read the pick's market and selection only (no prices or odds), keep the quote short, and record the author."""
import html as H
import re
from datetime import datetime, timezone

FEED = "https://www.flashscore.com/x/feed/f_1_{day}_0_en_1"       # day 0 = today (UTC), 1 = tomorrow
FSIGN = "SW9D1eZo"                                                  # header the site's own page sends with the feed
MATCH_URL = "https://www.flashscore.com/match/{id}/"


def parse_feed(text: str) -> list:
    out, comp = [], ""
    for rec in (text or "").split("¬~"):
        d = dict(f.split("÷", 1) for f in rec.split("¬") if "÷" in f)
        if "ZA" in d:
            comp = d["ZA"]
        if "AA" in d and "AE" in d and "AF" in d and d.get("AD", "").isdigit():
            out.append({"id": d["AA"], "home": d["AE"], "away": d["AF"], "competition": comp,
                        "kickoff": datetime.fromtimestamp(int(d["AD"]), tz=timezone.utc)})
    return out


def _text(fragment: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", fragment, flags=re.S)
    t = re.sub(r"</p>", "\n", t)
    t = H.unescape(re.sub(r"<[^>]+>", "", t))
    return " ".join(" ".join(line.split()) for line in t.split("\n") if line.strip())


def parse_preview(page: str):
    i = (page or "").find('id="eventPreview"')
    if i < 0:
        return None
    seg = page[page.rfind("<", 0, i):]
    end = seg.find("</article>")
    seg = seg[:end] if end > 0 else seg[:20000]
    parts = re.split(r"<h2[^>]*>(.*?)</h2>", seg, flags=re.S)
    intro = _text(parts[0])
    sections, author = {}, ""
    for title, body in zip(parts[1::2], parts[2::2]):
        t = _text(body)
        m = re.search(r"Author:\s*(.+?)\s*$", t)
        if m:
            author, t = m.group(1).strip(), t[:m.start()].strip()
        sections[_text(title)] = t
    if not sections and not intro:
        return None
    m = re.search(r"Author:\s*([^\n]+)", intro)
    if m and not author:
        author, intro = m.group(1).strip(), intro[:m.start()].strip()
    return {"intro": intro, "sections": sections, "author": author, "betting": sections.get("Betting Analysis", "")}


def _name_re(name: str) -> str:
    return re.escape(name.strip())


def _side(sentence: str, home: str, away: str):
    """'home' or 'away' for the first of the two team names found in the sentence."""
    best = None
    for side, name in (("home", home), ("away", away)):
        toks = [name] + [t for t in re.findall(r"[\w'’\-]{5,}", name)]
        for t in toks:
            m = re.search(r"\b" + _name_re(t) + r"\b", sentence, re.I)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), side, name)
                break
    return (best[1], best[2]) if best else (None, None)


def parse_pick(text: str, home: str, away: str) -> dict:
    """{'market','selection','covers','text'}; covers lists the outcomes ('home','draw','away') the pick wins on, or None."""
    text = " ".join((text or "").split())
    names = f"{_name_re(home)}|{_name_re(away)}|draw"
    for sentence in re.split(r"(?<=[a-z\)\.’'])\.\s+(?=[A-Z])", text):
        s = sentence.strip()
        low = s.lower()
        m = re.search(rf"\b((?:{names})\s*(?:/|\bor\b)\s*(?:{names}))\b", s, re.I)
        if "double chance" in low or re.search(r"\b(1x|x2)\b", low):
            sel, covers = None, None
            if m:
                sel = re.sub(r"\s*/\s*", "/", m.group(1))
                covers = []
                for part in re.split(r"/|\bor\b", sel, flags=re.I):
                    part = part.strip()
                    covers.append("draw" if part.lower() == "draw" else "home" if part.lower() == home.lower() else "away")
            elif re.search(r"\b1x\b", low):
                sel, covers = "1X", ["home", "draw"]
            elif re.search(r"\bx2\b", low):
                sel, covers = "X2", ["draw", "away"]
            return {"market": "Double chance", "selection": sel or "", "covers": covers, "text": s[:400]}
        hm = re.search(r"([+-]\d+(?:\.\d+)?)\s*(?:goal\s+|asian\s+)?handicap|handicap\s*(?:of\s*)?([+-]\d+(?:\.\d+)?)", s, re.I)
        if hm:
            h = hm.group(1) or hm.group(2)
            side, nm = _side(s[:hm.start()] or s, home, away)
            covers = [side] if side and float(h) < 0 else None
            return {"market": f"Handicap {h}", "selection": f"{nm} {h}" if nm else h, "covers": covers, "text": s[:400]}
        rm = re.search(r"\b(home|away)\s+win\b", s, re.I)
        if rm:
            side = "home" if rm.group(1).lower() == "home" else "away"
            gm = re.search(r"\b(over|under)\s+(\d+(?:\.\d+)?)\s*goals?", s, re.I)
            if gm:
                return {"market": f"{rm.group(1).capitalize()} win + {gm.group(1).capitalize()} {gm.group(2)} goals",
                        "selection": "", "covers": [side], "text": s[:400]}
            return {"market": "Match result", "selection": f"{home if side == 'home' else away} to win", "covers": [side], "text": s[:400]}
        om = re.search(r"\b(over|under)\s+(\d+(?:\.\d+)?)\s*(?:goals?|\b)", s, re.I)
        if om and ("goal" in low or "total" in low):
            return {"market": f"{om.group(1).capitalize()} {om.group(2)} goals", "selection": "", "covers": None, "text": s[:400]}
        if "both teams to score" in low or re.search(r"\bbtts\b", low):
            return {"market": "Both teams to score", "selection": "", "covers": None, "text": s[:400]}
        tn = rf"({_name_re(home)}|{_name_re(away)})"
        def side_of(name):
            return "home" if name.lower() == home.lower() else "away"
        mm = re.search(rf"\b{tn}\s+to\s+win\s+by\b", s, re.I)
        if mm:
            return {"market": "Winning margin", "selection": s[mm.start():][:80].rstrip(" .,;"), "covers": [side_of(mm.group(1))], "text": s[:400]}
        nm = re.search(rf"\b{tn}\s+(?:clean[- ]sheet\s+win|win\s+to\s+nil|to\s+win\s+to\s+nil)", s, re.I)
        if nm:
            side = side_of(nm.group(1))
            return {"market": "Win to nil", "selection": f"{home if side == 'home' else away} win to nil", "covers": [side], "text": s[:400]}
        hm2 = re.search(rf"\b{tn}\s+to\s+lead\s+at\s+(?:both\s+)?half-?time", s, re.I)
        if hm2:
            side = side_of(hm2.group(1))
            return {"market": "Half-time/full-time", "selection": f"{home if side == 'home' else away} to lead at half-time and full-time",
                    "covers": [side], "text": s[:400]}
        wm = re.search(rf"\b({_name_re(home)}|{_name_re(away)})\s+(?:to win|to beat|win\b|victory)", s, re.I)
        if wm and not re.search(r"to win by", low):
            side = "home" if wm.group(1).lower() == home.lower() else "away"
            return {"market": "Match result", "selection": f"{home if side == 'home' else away} to win",
                    "covers": [side], "text": s[:400]}
    return {"market": None, "selection": "", "covers": None, "text": text[:400]}
