# Daily sports research (runs 09:00 Europe/Dublin)

Goal: a research page for every competitive sport with events starting in the next 24h. Models only, NO bookmaker odds.

1. **Window.** Get the current time in Europe/Dublin (print it). Window = now to now+24h. All times shown in Irish time.
2. **Fixtures (fan out one subagent per group, each returns JSON in the schema below).**
   - Live data tool for every supported league (football + European comps, MLB, NBA, WNBA, NFL, NCAA, NHL, tennis, cricket, golf, MMA, NASCAR).
   - Web search for gaps: lower-league/cup football (live-footballontv.com), rugby, GAA, darts, snooker, boxing, racing headlines, esports.
   - Skip finished matches.
3. **Models (free only, honestly labelled).** predicd.com (football, statistical-model); covers.com/picks/<league> Odds Shark computer picks (statistical simulation, not a neural net; if scores show 0.00 say "not published yet", do NOT substitute moneylines); the live feed's win probabilities (official-feed). Brief search for other reputable free models. Human picks = human-pick. Never present paywalled or stale data as current.
4. **Staleness.** If a source's fixtures don't match the feed (old dates, wrong matchups), discard it and add it to `skipped` with the reason.
5. **Context (when available).** Form, injuries/team news, probable starters (MLB/NHL), weather, stakes.
6. **Write `fixtures.json`**: `{"skipped":[...], "fixtures":[{sport, competition, home, away, kickoff (ISO-8601 with offset), status (scheduled|live|finished), sources[], models:[{name, kind, source, url, fetched_at, probs:{home,draw,away}}]}]}`. Never invent data; omit rather than guess.
7. **Build.** `python3 -m src.build fixtures.json out/index.html` (also run `python3 -m pytest -q`). Non-zero exit = quality gate failed; the page still carries a WARNING banner, publish it and say why.
8. **Publish** `out/index.html` as an Artifact, updating the SAME artifact URL as the previous run (see CLAUDE.md for the URL).
9. **Final message (becomes the app notification):** first line = artifact link. Then: stale/missing/unreachable sources, and the 2-3 biggest model disagreements. Max ~5 lines.
