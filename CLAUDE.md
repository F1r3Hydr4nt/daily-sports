# daily-sports: project memory

## Purpose
Daily research-only sports page: every competitive sport with events in the next 24h
(Europe/Dublin, all times Irish). **No bookmaker odds** in this version; the value is
fixtures + free model predictions + context. Published as one self-contained HTML artifact.

## Decisions (do not re-litigate)
- Schedule: durable Routine, `CRON_TZ=Europe/Dublin 0 9 * * *`, fresh session per run.
  Routine id: trig_01GRo9osU7e8rptbiVArweg8 (created 2026-10-01). It wakes a dedicated home session
  (session_015XnLaoJGSmGFkRex5FnoEi) that has this repo attached, because the Routine API cannot attach a repo
  and fresh-session Routines start empty. The first Routine (trig_01BsFs...) failed for that reason and was deleted.
  The home session needs `pip install pytest tzdata` after a container restart. Persistent-session Routines
  cannot send a push notification via the API; check the session in the app (or recreate in the claude.ai Routines UI to get push).
- Notification: in-app/push only. NO email. Gmail connector is not used (user wants it disconnected).
- Same artifact URL updated daily: https://claude.ai/artifact/EHjGCjyvys3pUB95UzdF68 (first published 2026-10-01; republish `out/artifact.html` with that `url`).
- Python 3.11 + pytest, TDD (red -> green per module). Run: `python3 -m pytest -q`.
- Data collection is done by Claude (feeds, web search, subagents); everything downstream of
  `fixtures.json` is deterministic code in `src/`, unit-tested without network.

## Rules
- Window = now .. now+24h computed with zoneinfo `Europe/Dublin` (never fixed offsets). Drop finished matches; keep started-not-finished as LIVE.
- Every datum carries provenance {source,url,fetched_at,kind}; kind in
  official-feed | statistical-model | ai-model | human-pick. Be honest: predicd = statistical,
  Covers/Odds Shark = computer simulation, not a neural net; never present paywalled/stale data as current.
- Stale source (fixtures don't match feed) -> discard, list under "Sources skipped".
- Flags: model-vs-model spread >= 10pp; model-vs-consensus >= 5pp when 2+ models. Single model = "low confidence".
- Page must have: dark mode, responsive, timestamp + sources footer, "prices move / gamble responsibly" note.

## Layout
prompts/daily-research.md (the Routine prompt) | src/ (window, schema, normalise, dedupe, elo, render, validate) | tests/ | fixtures/ | out/ (gitignored)

## Data sources that worked (2026-10-01, after allowlisting *.domain wildcards)
- Football: www.live-footballontv.com (HTML `.fixture` blocks, UK/IE local time) + www.predicd.com/en/football (win/draw/loss %, times are Irish time).
- US sports/rugby/tennis/MMA/golf: espn.com pages embed JSON in `window['__espnfitt__']` (schedule/scoreboard per date). Odds Shark picks (predicted scores, not probabilities) from www.covers.com/picks/<league>; 0.00 = not published.
- Blocked/403: atptour.com, espncricinfo.com, site.api.espn.com. Not collected: cricket, darts, snooker, boxing, GAA, racing, esports.
- Subagents may report 'plan mode' and stop after fetching; the main session then parses the saved pages. Parsing scripts are throwaway (scratchpad), the deterministic code is in src/.
- Collector: `python3 -m collect.run fixtures.json` (modules in collect/, pure parsers unit-tested; live runs found two bugs the unit tests missed, so keep running it live after changes). Predicd's time zone has flipped between Irish time and UTC between fetches: `collect.football.align` detects the shift from fixtures present in both sources. Predicd drops games once they start, so a late-day run loses models for in-progress games (the 09:00 run is unaffected).
- Covers puts the down-arrow marker in different positions (0.00 layout vs real scores); the parser accepts both.
- Publish step: `python3 -m src.build fixtures.json out/index.html`, then `artifact_fragment()` in src/render.py strips the document wrapper into `out/artifact.html` for the Artifact tool.

## Gaps vs. the chat-built example page (user-shared, 2026-10-01)
- That page was built in claude.ai chat, which had a live sports data tool: per-game win probabilities for NFL/MLB/WNBA/NCAAF (a second model) and football leagues. Claude Code sessions here have no such tool, so US rows only have Odds Shark predicted scores (no win %).
- Ideas to close the gap: use ESPN game pages' win-probability/predictor if present in the embedded JSON; per-sport colour coding and a jump nav; show 12 vs 24h by request.

## Run log
- 2026-10-02 09:07 Dublin: collector ran clean (116 raw, 106 after quality gate; tennis 54, football 44, rugby 7, NHL 5). Only Predicd (football) and Odds Shark (NHL/NFL/MLB) models, so no model-vs-model comparisons were possible; all rows single-source. Home session needs `pip install pytest tzdata` after container restart (confirmed again).
- 2026-10-03 09:10 Dublin (Saturday): collector clean, 298 raw / 291 after gate (football 149, NCAA 54, tennis 50, rugby 25, NHL 13, MLB 4, NBA 1). 123 fixtures have a model, all single-source (Predicd football, Odds Shark NHL/MLB), so no model-vs-model flags. Cricket, darts, snooker, boxing, GAA, racing, esports still have no collector.
- 2026-10-04 09:10 Dublin (Sunday): collector clean, 157 raw / 124 after gate (tennis 71, football 59, NFL 14, NHL 5). 48 fixtures have a model, all single-source (Predicd football, Odds Shark NFL/NHL/MLB), so no model-vs-model flags. WNBA Odds Shark still 0.00. Same seven sports (cricket, darts, snooker, boxing, GAA, racing, esports) have no collector.
- 2026-10-05 09:11 Dublin (Monday): collector clean, 102 raw / 94 after gate (tennis 68, football 22, NBA 5, NHL 4, MLB 2, NFL 1). 18 fixtures have a model, all single-source (Predicd football, Odds Shark NHL), so no model-vs-model flags. Same seven sports have no collector.
- 2026-10-06 09:11 Dublin (Tuesday): collector clean, 140 raw / 131 after gate (tennis 76, football 47, NHL 9, NBA 4, MLB 2, NCAA 1, MMA 1). 27 fixtures have a model, all single-source (Predicd football, Odds Shark NHL/NFL), so no model-vs-model flags. Same seven sports have no collector.
