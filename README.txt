NFL 2026 consensus board
========================

Open index.html in Chrome. Everything runs locally; nothing is uploaded anywhere.

Views
  Teams        formlines per game (trimmed to the predictive columns), Diggs note, almanac summary
  League table season averages, sortable, with ATS and O/U records
  This week    every game as a card with line and total movement — click a game to compare the teams
  Matchup      side by side season numbers, offense-v-defense pairings, game logs, Diggs/FTN notes
  Almanac notes

Files
  index.html                    the app (do not edit)
  data.js                       generated data the app reads — rebuild weekly
  build_data.py                 rebuilds data.js from nflverse + betql_lines.json + the almanac doc
  betql_lines.json              opening/closing lines by week (BetQL)
  nfl_2026_almanac_summary.md   almanac summaries and Diggs comparisons — edit this to add new previews
  COWORK_TASK_PROMPT.txt        standing instructions for the Tuesday scheduled task

One-off setup
  pip install pandas pyarrow markdown
  python build_data.py          (should print "data.js written — weeks [1] — 15 games, 32 teams")

Adding a Diggs preview
  Paste the comparison paragraph into nfl_2026_almanac_summary.md under the team, starting with
  "**Diggs vs FTN" — the build picks it up automatically and shows it on the team page.

Stat definitions
  Filter          pre-snap win probability 10–90% (toggle in the app to see raw)
  EPA             turnovers (interceptions, lost fumbles) removed by default (toggle in the app to include)
  Dropback EPA    passes, sacks and scrambles; Rush EPA = designed runs only
  Explosive       passes 15+ yds or runs 10+ yds, share of plays
  Pace            seconds per offensive snap (possession time / plays)
  Neutral pace    seconds between consecutive snaps, counted only at 35–65% win probability
  Lines           from the team's side, negative = favourite; open = BetQL Open, close = BetQL Live
