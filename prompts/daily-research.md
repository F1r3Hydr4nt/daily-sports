# Daily sports research (runs 09:00 Europe/Dublin)

Goal: a research page for every competitive sport with events in the next 24h. Free model predictions only, NO bookmaker odds. Times in Irish time.

1. **Setup.** `git pull origin claude/wonderful-cori-vxwyn9`; `pip install -q pytest tzdata`; `python3 -m pytest -q` must pass.
2. **Collect.** `python3 -m collect.run fixtures.json` fetches live-footballontv + Predicd (football), ESPN (NHL, NFL, NBA, WNBA, MLB, NCAA, tennis, rugby, MMA, golf) and Covers/Odds Shark picks, merges them, aligns Predicd's time zone against the listings, and records every blocked or missing source under `skipped`. It never invents fixtures.
3. **Fill gaps (optional, only with data you actually fetched).** Cricket, darts, snooker, boxing, GAA, horse/greyhound racing, esports are not collected yet. If you can fetch a reliable source showing fixtures inside the window, append them to `fixtures.json` in the same schema (kickoff in ISO-8601 with offset, `models: []` unless a free source publishes a prediction) and remove that sport's "no collector yet" note. Otherwise leave the note. Do not use paywalled or stale data as current, and do not collect bookmaker odds.
4. **Build.** `python3 -m src.build fixtures.json out/index.html` (non-zero exit = quality gate failed; the page carries a WARNING banner, publish it anyway and say why), then create `out/artifact.html` with `artifact_fragment` from `src/render.py`.
5. **Publish** `out/artifact.html` as an Artifact, updating the SAME URL recorded in CLAUDE.md (read it first, then publish with `url`).
6. **Save.** Copy `fixtures.json` to `fixtures/YYYY-MM-DD.json`, commit and push to `claude/wonderful-cori-vxwyn9`. Put new learnings (blocked hosts, layout changes) in CLAUDE.md.
7. **Final message** (this is what the user reads): first line = artifact link. Then at most 4 lines: stale/missing/blocked sources, and the 2-3 most notable model disagreements (model vs model; there is no bookmaker comparison). Max ~5 lines.
