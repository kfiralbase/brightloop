# Brightloop pricing watch

Built for **Maya, Head of Growth**. Every Monday she spends 08:30 to 10:30 rebuilding a competitor
deck by hand for the 11:00 leadership sync, and the only thing that ever moves a decision in that
room is a pricing or packaging change. This tool tells her what moved on Lovable's, Replit's and
Bolt's pricing pages since last week, with the number and the link next to every claim, and says
so plainly when nothing moved.

## The proof command

Needs only `python3` (3.10 or newer). No install, no keys, no network.

```bash
./run --input cases.json --output result.json
```

Same thing without the wrapper script: `python3 -m brightloop run --input cases.json --output result.json`.

Try it on the example from the brief:

```bash
./run --input tests/fixtures/brief_example.json --output result.json
```

Tests:

```bash
python3 -m unittest -v
```

## Live mode

The weekly run opens each competitor's pricing page in a headless browser, switches to monthly
billing, reads every plan card (price, credits, limits, features) and screenshots each card. It
compares against the last recording and turns what moved into signals in the same format as
`cases.json`, which go through the same core.

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[live]' && .venv/bin/playwright install chromium
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

## How it decides

One decision path (`brightloop/core/pipeline.py`) for live runs and file runs. Only the source changes.

1. **Clean the text.** Hidden HTML comments and tags are removed before anything reads it.
   Text that tries to instruct an AI is flagged and ignored.
2. **Keep only pricing changes.** Ads, feature launches without a price change, and rumors go to
   `skipped` with the reason.
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
| `change` | `field` (price, a unit like credits, tier, packaging), `plan`, `before`, `after`, `direction` |
| `evidence` | One entry per source: `source_id`, `source`, `ts_utc`, `quote` (visible text only), `source_tier` |
| `cta` | `label` and `utm` query string (from `config.utm_source`) for the Brightloop link the action points to |

In live runs each evidence entry also has `screenshot`: the cropped plan card.

`run.cost_usd` is 0.0: the decision path uses no paid API. `run.mode` is `file`, `live` or
`replay`. `run.baselines` lists competitors captured for the first time (nothing to compare yet).

## Status

| Part | State |
|---|---|
| Core rules, CLI, tests, CI | Done |
| Live collection of pricing pages (Playwright), recorded snapshots, offline replay | Done |
| History from the Wayback Machine | Next |
| Google Slides deck from Maya's template, Slack message | Planned |
| Base44 app: change history, run log, run now | Planned |
| Weekly schedule (GitHub Actions) | Planned |

See [DECISIONS.md](DECISIONS.md) for why it's built this way.
