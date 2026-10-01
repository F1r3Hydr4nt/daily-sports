# daily-sports: project memory

## Purpose
Daily research-only sports page: every competitive sport with events in the next 24h
(Europe/Dublin, all times Irish). **No bookmaker odds** in this version; the value is
fixtures + free model predictions + context. Published as one self-contained HTML artifact.

## Decisions (do not re-litigate)
- Schedule: durable Routine, `CRON_TZ=Europe/Dublin 0 9 * * *`, fresh session per run.
  Routine id: trig_01BsFsY8cQQUHSiNg9q9yqeL (created 2026-10-01; push notification only; no repo source or connectors attached, so the prompt tells the session to check out the branch itself).
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
- Publish step: `python3 -m src.build fixtures.json out/index.html`, then `artifact_fragment()` in src/render.py strips the document wrapper into `out/artifact.html` for the Artifact tool.
