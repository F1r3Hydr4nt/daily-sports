from .dedupe import canon


def check(fixtures, window) -> dict:
    errors = []
    if not fixtures:
        errors.append("no fixtures found")
    for f in fixtures:
        if f["status"] != "live" and not window.contains(f["kickoff"]):
            errors.append(f"outside window: {f['home']} v {f['away']}")
    return {"ok": not errors, "errors": errors}


def reject_stale(feed, page_fixtures, min_match=0.5):
    """A model page is stale if too few of its fixtures appear in the live feed."""
    if not page_fixtures:
        return False, "page has no fixtures"
    feed_keys = {(canon(f["home"]), canon(f["away"])) for f in feed}
    hits = sum((canon(p["home"]), canon(p["away"])) in feed_keys for p in page_fixtures)
    ratio = hits / len(page_fixtures)
    if ratio < min_match:
        return False, f"only {ratio:.0%} of page fixtures match the feed"
    return True, ""


def check_page(html: str, sports) -> list:
    """The rendered page must carry the predicted-score column and the margin controls it promises."""
    errors = []
    if sports & {"football", "nhl", "nfl"}:
        if "<th>Predicted score</th>" not in html:
            errors.append("page is missing the predicted score column")
        if 'class="scorebox' not in html:
            errors.append("page shows no predicted-score boxes")
    for sport in ("football", "nhl", "nfl"):
        if sport in sports and f'id="min-{sport}"' not in html:
            errors.append(f'page is missing the min-{sport} margin control')
    return errors
