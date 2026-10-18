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
- 2026-10-07 09:11 Dublin (Wednesday): collector clean, 70 raw / 66 after gate (tennis 47, football 7, NBA 5, MLB 4, NHL 3, WNBA 2, NCAA 2). Quiet day: 13 fixtures have a model, all single-source (Predicd football, Odds Shark NHL/MLB), so no model-vs-model flags. Same seven sports have no collector.
- 2026-10-08 09:12 Dublin (Thursday): collector clean, 100 raw / 96 after gate (tennis 60, football 16, NHL 10, NBA 6, NCAA 4, NFL 1, MLB 1, rugby 1, golf 1). 21 fixtures have a model, all single-source (Predicd football, Odds Shark NHL/MLB/WNBA/NFL), so no model-vs-model flags. WNBA Odds Shark scores were published today. Same seven sports have no collector.
- 2026-10-09 09:11 Dublin (Friday): collector clean, 128 raw / 126 after gate (football 78, tennis 30, rugby 6, NCAA 5, NHL 4, NBA 2, WNBA 2, golf 1). 59 fixtures have a model, all single-source (Predicd football, Odds Shark NHL/NFL), so no model-vs-model flags. Predicd's offset came out at -60 min today (previously +60); only 4 fixtures overlapped the listings, but I spot-checked Dortmund v Bremen and Heidenheim v Kaiserslautern against known CEST kickoffs and they are right. 49 of 59 modelled football games are Predicd-only (no listing overlap), so their times rest on that alignment. Same seven sports have no collector.
- 2026-10-10 09:12 Dublin (Saturday): collector clean, 313 raw / 308 after gate (football 186, NCAA 46, tennis 34, rugby 22, NHL 14, NBA 7, MMA 2, MLB 1, golf 1). 172 football + a few US fixtures have a model, all single-source, so no model-vs-model flags. Same seven sports have no collector.
  **Bug found and fixed:** Predicd games whose team names differ from the listings ("Málaga" vs "Málaga CF", "Brest" vs "Stade Brest", "QPR" vs "Queens Park Rangers", "Preußen Münster", "Parma  (joins match in progress)") were not matched and appeared as duplicate rows (listing row with no model + Predicd-only row). `collect.football.same_team` now matches by token subset ignoring club-noise words, with a youth-age guard and a spelling-variant fallback (tests added). It only removed 4 duplicates today (190 -> 186), so most Predicd-only games are genuinely absent from the listings. The 2026-10-09 and earlier pages may contain a few such duplicates; their counts were slightly inflated.
- 2026-10-11 09:11 Dublin (Sunday): collector clean, 261 raw / 198 after gate (tennis 126 raw, football 111, NFL 13, NBA 4, NHL 3, rugby 3, MLB 1). 120 fixtures have a model (104 football), all single-source (Predicd football, Odds Shark NFL/NHL), so no model-vs-model flags. Predicd offset -60 min again (two days running); no duplicate rows after the 10-10 matcher fix. Same seven sports have no collector.
  Follow-up fix: `same_team` could have matched a reserve side to its senior club ("1. FC Köln II" vs "1. FC Köln") via the token-subset rule; reserve markers (II/III/B) are now guarded like age groups (tests added). No wrong attachments occurred in published pages.
- 2026-10-12 09:12 Dublin (Monday): collector clean, 140 raw / 131 after gate (tennis 90 raw, football 39, NBA 5, NHL 3, MLB 2, NFL 1). 33 fixtures have a model, all single-source (Predicd football, Odds Shark NHL/NFL), so no model-vs-model flags. No near-duplicate football rows today. Same seven sports have no collector.
  Yesterday's (10-11) page still showed one duplicate pair, "FC Köln v Borussia Mönchengladbach" (no model) and "1. FC Köln v Borussia M'Gladbach" (Predicd); added the Gladbach alias (test added). Name variants are an ongoing source of duplicates: when a page shows a listing row without a model next to a Predicd-only row at the same kickoff, add an alias in `collect.football.ALIASES`.
- 2026-10-13 09:11 Dublin (Tuesday): collector clean, 192 raw / 163 after gate (tennis 99 raw, football 68, NHL 16, NBA 5, NCAA 2, MLB 1, MMA 1). 46 fixtures have a model, all single-source (Predicd football, Odds Shark NHL/NFL), so no model-vs-model flags. Predicd offset -60 min (third day running). No near-duplicate football rows. Same seven sports have no collector.
- 2026-10-14 09:12 Dublin (Wednesday): collector clean, 115 raw / 106 after gate (football 54, tennis 49, NBA 7, NHL 2, NCAA 2, MLB 1). 31 fixtures have a model, all single-source (Predicd football, Odds Shark NHL), so no model-vs-model flags. Predicd offset -60 min (fourth day running). Same seven sports have no collector.
  Two more duplicate pairs found on the first build and fixed before publishing (tests added): live-footballontv truncated "SG Sonnenhof Großaspach" to just "SG" (a listing name with no informative words now acts as a wildcard, provided the other team matches and kickoff is within 30 min), and "Betis Sevilla" vs "Real Betis" (alias). The near-duplicate check (same kickoff, one side with a model, teams similar) is worth running after every collection.
- 2026-10-15 09:13 Dublin (Thursday): collector clean, 106 raw / 94 after gate (football 44, tennis 42, NHL 11, NCAA 3, NBA 2, MLB 2, NFL 1, rugby 1). 50 fixtures have a model, all single-source (Predicd football, Odds Shark NHL), so no model-vs-model flags. Predicd offset -60 min (fifth day running). Same seven sports have no collector.
  Euro-night name variants produced 10 duplicate pairs on the first collection (Gent v "KAA Gent", "Crvena zvezda" v "Red Star Belgrade", Hearts v "Heart of Midlothian", Marseille/Olympiakos, Sparta Prague/Lillestrom, etc.). Rather than adding more aliases, `collect.football.one_team_match` now treats one matching team at a kickoff within 5 min as the same fixture (a club cannot play two games at once; youth/reserve markers must still agree). Tests added; the old "Man Utd v Leeds vs Man City v Leeds stays separate" merge test became a `same_team` assertion, since that case now merges by design. Near-duplicate check after the fix: 0 pairs.
- 2026-10-16 09:12 Dublin (Friday): collector clean, 116 raw / 106 after gate (football 64 raw, tennis 29, NBA 12, rugby 4, NCAA 3, NHL 2, MLB 1, MMA 1). 49 fixtures have a model, all single-source (Predicd football, Odds Shark NHL/NFL), so no model-vs-model flags. Predicd offset -60 min (sixth day running). Near-duplicate check after the 10-15 `one_team_match` change: 0 pairs. Same seven sports have no collector.
- 2026-10-17 09:12 Dublin (Saturday): collector clean, 348 raw / 335 after gate (football 208, tennis 51, NCAA 52, rugby 20, NHL 14, WNBA 1, MLB 1, MMA 1). 187 fixtures have a model, all single-source (Predicd football, Odds Shark NHL), so no model-vs-model flags. No Predicd time-shift note today (aligned offset was zero, first time since 10-08); near-duplicate check: 0 pairs. Same seven sports have no collector.
- 2026-10-18 09:07 Dublin (Sunday): collector clean, 261 raw / 236 after gate (football 140 raw, tennis 100 raw, NFL 12, rugby 6, NHL 2, MLB 1). 131 fixtures have a model, all single-source (Predicd football, Odds Shark NFL/NHL), so no model-vs-model flags. Predicd offset note present again (8 notes). Same seven sports have no collector.
  Latent bug fixed before publishing: `norm` strips a trailing "Women"/"W", so `same_team("Manchester United", "Manchester United Women")` was True and, with `one_team_match`, a men's and a women's game at the same kickoff could merge. `same_team` now requires matching women's markers (tests added). The near-duplicate check flagged three men's v women's pairs today (not merged); after the fix it reports 0.
