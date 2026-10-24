# Brightloop pricing watch

Built for **Maya, Head of Growth**. Every Monday she spends 08:30 to 10:30 rebuilding a competitor
deck by hand for the 11:00 leadership sync, and the only thing that ever moves a decision in that
room is a pricing or packaging change. This tool tells her what moved on Lovable's, Replit's and
Bolt's pricing pages since last week, with the number and the link next to every claim, and says
so plainly when nothing moved.

## The proof command

Needs only `python3` (3.9 or newer, so the one that ships with macOS works). No install, no keys, no network.

It always writes a valid `result.json`: a missing or broken input file, broken signals, or even a bug
in the decision code end up in `run.errors`, with every input id still placed (in `skipped` if it
couldn't be processed). On Windows, use `python -m brightloop run --input … --output …` (the
`./run` wrapper is a bash script); if Windows' Python lacks time-zone data, install `tzdata`, or the
run falls back to UTC and says so in `run.errors`.

```bash
./run --input cases.json --output result.json
```

Same thing without the wrapper script: `python3 -m brightloop run --input cases.json --output result.json`.
Or install it and use the brief's exact command (still no dependencies):

```bash
pip install . && run --input cases.json --output result.json
```

Try it on the example from the brief, or on a harder one (26 signals: the same change from two
sources in two time formats, `€` prices, an unknown competitor, injected text, rumors, sponsored
claims, a limited-time promo, an annual price move, an out-of-week change, a bad timestamp,
missing and duplicate ids, a non-object entry):

```bash
./run --input tests/fixtures/brief_example.json --output result.json
./run --input examples/valid_cases.json --output result.json     # clean input, no errors
./run --input examples/tricky_cases.json --output result.json    # traps and broken entries
```

Expected outputs: `examples/valid_result.json` and `examples/tricky_result.json`.

Tests:

```bash
python3 -m unittest -v
```

## Running it

| What | How |
|---|---|
| **Test on a file** (what reviewers run) | `./run --input cases.json --output result.json`. No install, no keys, no network. |
| **Test on a file, in the app** | **Test a file** page: upload `cases.json`, download `result.json`. Runs the same Python (`brightloop/file_run.py`) in the browser with Pyodide; the file never leaves the computer. |
| **Scan now, from the app** | **Run now** on the home page. Starts the weekly workflow; refused while one is running or within 10 minutes of the last. |
| **Scan now, from GitHub** | Actions → **weekly** → **Run workflow**, or `gh workflow run weekly`. Captures, decides, publishes to the app, commits the recording. |
| **Scan now, on your machine** | `.venv/bin/python -m brightloop live` (setup below). Publishes too if `.env` has the Base44 keys; add `--no-publish` to keep it local. |
| **Every Monday** | Automatic: the Base44 app's **Monday pricing run** workflow starts `.github/workflows/weekly.yml` at 07:30 Jerusalem time; GitHub's own cron is the fallback at 07:45. |

The weekly workflow needs the repository secrets `BASE44_APP_ID`, `BASE44_TOKEN` and
`DECK_SECRET`; `SLACK_WEBHOOK_URL` is optional (the Monday message).

**Two clocks for the Monday run.** GitHub can start scheduled jobs late (a test schedule here
started more than 15 minutes late), so the main trigger is a scheduled workflow in the Base44 app:
Mondays 07:30, `Asia/Jerusalem` (Base44 handles the clock change). It calls the app's
`/api/start-weekly` route, which starts the GitHub workflow the same way Run now does, with
`notify` on; only the app's admin can call it. GitHub's cron is the fallback at 07:45: it runs in
UTC and Israel changes clocks, so it's scheduled at both 04:45 and 05:45 UTC and proceeds only
when it's 07:xx or 08:xx in Jerusalem and nothing has run that day. Both clocks would have to fail
the same morning for the deck to be missing.

**Run now** needs an app secret `GITHUB_TOKEN` in Base44: a fine-grained GitHub token for this
repository only, with Actions read and write. It stays on the server; the button only gets
"started", "running" or "refused" back.

**Test a file** loads `public/py/bundle.json` in the app, built from this repo with
`python3 scripts/browser_bundle.py`. It lists `BROWSER_FILES` from `brightloop/file_run.py`,
and `tests/test_browser_bundle.py` checks those files alone give the same result as the CLI.
The page shows the commit the bundle came from; rebuild it when the core changes.

## Live mode

The weekly run opens each competitor's pricing page in a headless browser, switches to monthly
billing, reads every plan card (price, credits, limits, features) and screenshots each card.
Where the page also has a Yearly toggle (Lovable, Bolt), it switches to it and reads each plan's
annual price too; an annual move gets its own line, `Pro (annual): $21→$23/month`. It
compares against the last recording and turns what moved into signals in the same format as
`cases.json`, which go through the same core.

For Maya's deck it also takes two pictures per competitor: the whole pricing section (one
rectangle around all plan cards) and the homepage above the fold. Homepage changes aren't
tracked; the picture is only for the slide. Cookie banners are hidden for the screenshot, never
accepted: Reject is pressed if the site offers it, otherwise the banner is just not shown.

**A last check before the deck** (`brightloop/verify.py`): each plan card's screenshot is read
back with OCR (Tesseract) and must show the price and every line that was read from the page
text; the annual picture must show the annual prices, and the pricing section must not be cut
off. On a mismatch the page is captured once more. If it still doesn't match, the slide goes in
anyway, marked "check before 11", and the Slack message names it. Nothing it finds changes a
decision. Without Tesseract the check is skipped and says so (`verification: skipped`).

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[live]' && .venv/bin/playwright install chromium
brew install tesseract   # or: apt-get install tesseract-ocr (optional: the OCR check)
.venv/bin/python -m brightloop live
```

Every live run is recorded in `recordings/`: a snapshot and cropped screenshots per competitor,
plus `runs/<stamp>/cases.json` and `result.json`. These are real captures, so the live logic also
runs with no keys and no network:

```bash
python3 -m brightloop live --offline   # replays the two latest recordings
./run --input recordings/runs/<stamp>/cases.json --output result.json
```

Competitors and pages are in `config/live.json`.

## Maya's Monday deck

After each weekly run, the workflow asks the app to build **"Competitor Deck Wk of
&lt;Monday&gt;"** in the **Growth** folder of the connected Google Drive, in her layout: one slide
per competitor (Lovable, Replit, Bolt), the homepage and pricing-section screenshots (stacked or
side by side, with the pricing shot taking about two thirds of the space so the cards are
readable), and a red box under the pricing shot with each
change's `deck_line` (short, e.g. `Pro: $25→$30/month`) only when something moved. The link
appears on the app's home page.

**Each deck belongs to a Monday.** Every run, scheduled or Run now, feeds the deck for the Monday
on or after its date (Jerusalem time), and that deck shows every change from all the runs that
feed it. So a price spotted by a Thursday Run now still appears on Monday's slide, marked
"(spotted Thu)", and a midweek run never rewrites the deck leadership already saw.

**A site that didn't load keeps its slide.** The run reuses its last capture, and the slide
says "Not checked this week (site didn't load) · screenshots from &lt;date&gt;". All three
competitors always get a slide.

**One Slack message on Monday** with the deck link and the red-box lines (or that the deck
failed, and where to look). Only the scheduled Monday run sends it; Run now doesn't, unless the
workflow is started with **notify** checked. Needs a `SLACK_WEBHOOK_URL` repository secret
(a Slack incoming webhook; the webhook decides the channel or DM). Without it the step is skipped.
Try the text locally: `python3 -m brightloop notify --deck out/deck.json` prints it when no
webhook is set.

It's the `build-deck` backend function in the Base44 app, using Base44's shared Google Slides and
Google Drive connectors (Base44 handles the OAuth). Function URLs are public, so it requires an
`X-Deck-Secret` header matching the `DECK_SECRET` secret, set in both the app and this repo.
A deck failure is recorded on the run; the recording is still committed.

## Base44 app

**Its code is in [`app/`](app/)**: the React front end (`app/src/`), the entity schemas
(`app/base44/entities/`), the `build-deck` backend function (`app/base44/functions/`) and the
connector declarations. The app is edited in Base44; `python3 scripts/export_app.py` copies its
current source here (Base44's export API, with the PAT from `.env`), and the result is committed.
`tests/test_app_copy.py` fails if the core copy the app runs in the browser
(`app/public/py/bundle.json`) drifts from `brightloop/`.

The web app ([bright-loop-watch.base44.app](https://bright-loop-watch.base44.app)) shows this
week's changes with their screenshots, the change history, and the run log. It reads four
entities: `Run`, `Change`, `Skipped`, `Snapshot`. The Python job writes them through the Base44
REST API; viewers only read.

With `BASE44_APP_ID` and `BASE44_TOKEN` in `.env` (or the environment), a live run uploads its
screenshots as public files and upserts its records. To publish a run that's already recorded:

```bash
python3 -m brightloop publish            # the latest run
python3 -m brightloop publish --run 2026-10-23T1508Z
```

Publishing never blocks a run: if Base44 is down, the result and recording are still written
and the error goes into `run.errors`. Re-publishing a run updates its records (upsert on
`run_key` plus the record's own id) rather than duplicating them.

**Where data lives:** screenshots (about 99% of the size) go to Base44 and aren't committed.
The JSON snapshots and each run's `cases.json` and `result.json` stay in `recordings/`, because
they're next week's "before" and the no-keys replay data.

## How it decides

One decision path (`brightloop/core/pipeline.py`) for live runs and file runs. Only the source changes.

1. **Clean the text.** Hidden HTML comments and tags are removed before anything reads it.
   Text that tries to instruct an AI is flagged and ignored.
2. **Keep only pricing changes.** Ads, feature launches without a price change, rumors and
   limited-time promos go to `skipped` with the reason.
3. **Trust only the competitor's own pricing page** (`brightloop/core/trust.py`). A pricing
   claim from anywhere else goes to `skipped`: a sponsored post, a news site or a reddit thread
   as unverified, and the competitor's own blog or X account as "not on the pricing page yet".
4. **Read the numbers from the text.** Price, credits, seats and other limits, and tier moves.
   A price with no previous value is not a change. No number is ever estimated.
5. **Merge the same change reported twice** into one item with every source id.
6. **Score confidence from the evidence**, never from the input: 0.9 for the pricing page,
   +0.05 when both before and after are numbers, +0.04 per extra independent source, −0.15 for
   a packaging change with no number, −0.2 if a source tried to inject instructions.
7. **Check the contract:** every input id lands in exactly one place, or the run reports an error.

Times are normalized to UTC. The `week` filter is read in the input's `timezone`, so
Sunday 23:30 UTC can already be Monday in Jerusalem.

## Output

The required wrapper, plus these fields inside each item:

| Field | Meaning |
|---|---|
| `competitor` | Whose pricing changed |
| `deck_line` | The one-liner for the red box on that competitor's slide, e.g. `Pro: $20/month → $25/month` |
| `change` | `field` (price, a unit like credits, tier, packaging), `plan`, `before`, `after`, `direction` |
| `evidence` | One entry per source: `source_id`, `source`, `ts_utc`, `quote` (visible text only), `source_tier` |
| `cta` | `label` and `utm` query string (from `config.utm_source`) for the Brightloop link the action points to |

In live runs each evidence entry also has `screenshot`: the cropped plan card.

`run.cost_usd` is 0.0: the decision path uses no paid API. `run.mode` is `file`, `live` or
`replay`. `run.baselines` lists competitors captured for the first time (nothing to compare yet).
`run.notes` lists things that were degraded but didn't fail, such as a homepage picture reused
from an earlier run because this week's page showed a bot check.

## How I know it works

- **The contract on the brief's example:** CI runs `./run` on it on every push (Python 3.9 and
  3.13) and checks that every input id is placed exactly once. Only `pr-401` becomes an item;
  the sponsored claim, the ads, the launches, the rumor and the injected comment are skipped,
  each with a reason. The injected text never reaches the output.
- **Unit tests for each rule and each trap** (`tests/`), including phrasings not in the example
  (`5→3 projects`, `€`/`£` prices, `from 100 to 50` with the unit first) and broken input
  (bad JSON, missing or duplicate ids, unreadable timestamps). Nothing crashes; problems land in
  `run.errors`.
- **Cases I hadn't written for:** I wrote new inputs against the rules, not against the code
  (`10M tokens → 5M tokens`, `from 5 projects to 3`, a new plan with its price, a blog URL ending
  in `/pricing`, visible "ignore previous instructions", epoch timestamps). Each one that came out
  wrong was fixed and became a test (`UnseenPhrasings` in `tests/test_pipeline.py`).
- **The screenshots show what was read:** before each deck, OCR checks every plan card's
  picture against the text read from the page. On 282 lines from three real captures of all three
  sites none was missed, and a price, line or annual price changed in the text alone is caught
  (`tests/test_verify.py`).
- **The browser copy matches the CLI:** a test runs only the files the app ships, isolated, and
  compares the result with the CLI's. The app page shows which commit its copy came from.
- **Live runs on the real sites:** repeated captures of Lovable, Replit and Bolt minutes and
  hours apart produced zero changes, so there's no noise to cause false flags. The diff that
  finds real changes is tested on snapshots built from the real cards; no competitor has changed
  a price since recording started, so a real change hasn't been seen live yet.
- **End to end:** one press of Run now in the app started the GitHub workflow, which captured,
  decided, published to Base44, built the deck in Google Slides and committed the recording.

## Status

| Part | State |
|---|---|
| Core rules, CLI, tests, CI | Done |
| Live collection (Playwright), recordings, offline replay | Done |
| Base44 app: this week, history, run log, Test a file, Run now | Done, published |
| Google Slides deck in Maya's layout, built after each run | Done |
| Weekly schedule (GitHub Actions) | Done |
| Monday Slack message with the deck link | Done; needs the `SLACK_WEBHOOK_URL` secret |

See [DECISIONS.md](DECISIONS.md) for why it's built this way, and [SPOTTED.md](SPOTTED.md) for
every trap found in the brief and its data, and what was done about each.
