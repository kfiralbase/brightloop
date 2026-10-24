# Decision log

Short entries, newest last. Quotes are from the marketer interviews.

## Who and what

**Built for Maya.** All three marketers track competitors by hand, and each opened with a wish
("more signups", "more ad ideas", "tell me what ships"). I chose by asking for the last concrete
time. Maya: 08:30 to 10:30 every Monday before an 11:00 leadership sync, and pricing moves are
"the only thing that's ever shifted a decision in that room."

**Not Daniel.** His pain is bigger in hours (about 3 of 5 weekly hours go to hunting ad proof),
but his proof is Meta ads in the US ("I mostly look at US"). Meta's Ad Library API returns
commercial ads only for EU/UK delivery, and LinkedIn, his other channel, has no public API. The
rest means scraping against the platforms' terms or a paid third-party scraper. He is the clear
next candidate if an official source opens up.

**Not Noa.** Her bottleneck is writing, not finding out ("That's the bottleneck, not the finding
out"), and her core ask can't be met ("nothing reliably beats Twitter"). A drafting tool needs an
LLM, so it can't give a meaningful result on unseen cases without keys, and "half-decent" can't
be verified.

**Only pricing and packaging.** Maya: "if the price didn't move, it's product's problem." Feature
launches go to skipped, including "Agent 4 is live for every plan": I first read that as a
packaging change, asked, and she said no.

**Full plan table, not just the headline price.** Maya listed "price, plan limits, free tier,
seats, credits". Noa: "she cares about the headline number but misses the bundling and tier
changes."

**Competitors: Lovable, Replit, Bolt.** Maya: "Always Lovable, Replit, and Bolt in the deck." v0
is in the brief's list, so it's in config but off. The core handles any competitor in the input.

## Trust

**Only the competitor's own pricing page counts as proof.** Maya was burned by an AI summary
that said a competitor "cut prices 30%"; leadership drafted a promo before it was caught. Since
then: "no link, no number." Third-party pricing claims go to skipped with the reason, so nothing
disappears.

**The competitor's own blog or X account isn't enough either.** I first made these items with
lower confidence and a "confirm first" action. Maya's rule is binary ("pricing page or
nothing"), and she said Monday is soon enough, so they go to skipped with the reason "not on
the pricing page yet". If the price really moved, the live run catches it on the page.

**No launch de-duplication.** I had built detection of the same launch reported twice (Noa's
pain). For Maya every launch is skipped anyway, so it only added a sentence to a skip reason.
Removed. What Maya needs stays: two reports of the same pricing change become one item.

**One generic extractor, not a scraper per competitor.** It finds plan cards by plan names and
prices, not by a site's HTML structure, so a redesign is less likely to break it and a new
competitor is one line in `config/live.json`. It worked on all three sites as is. If a site
ever needs special handling, that goes in its config entry, not a new module.

**Precision over recall.** Maya: "Flagging a false one is worse." The cost was credibility: "we
looked dumb in front of the whole team."

**No number comes from a model.** Every number is read from the source text by deterministic
rules. That's also what makes the repo run on unseen cases with no keys.

**predicted_ctr is never used.** It's a model score, not performance. Daniel was burned by a tool
that ranked a 2-day-old ad first by predicted CTR; "That ad died a week later."

**Rumors are skipped.** Noa nearly posted a reaction to "v0 is shutting down" from Reddit.

## Product

**The core feature is the diff.** Maya: "I re-screenshot everything fresh every Monday because I
have no way to diff against last week's." Real changes come "maybe once a quarter", so a quiet
week must still produce a deck that says "no change", with fresh screenshots as proof.

**Deliver into Drive and Slack, not a dashboard.** Maya: "if it's not already in Google Drive or
Slack where I live, I'm not opening it. New login, new tab, it's dead." The deck fills her
existing Google Slides template. The web app holds history and the run log, linked from Slack.
This is also why the brief's "analytics dashboard" stays out.

**Each item's action points somewhere useful.** Comparison pages are orphaned (Noa: "No one
really owns them"), so a verified change says to update the comparison page. A price rise
suggests checking whether we're now cheaper, which is an angle for Daniel only if it's true.

**Weekly schedule, Monday before 08:30 Jerusalem time (planned).** Maya: "Monday's been working
fine." GitHub's cron runs in UTC and Israel changes clocks on 2026-10-25, so the plan is to
schedule both offsets and skip if it already ran that week. Midweek checks are a possible extension.

## Engineering

**Core and test path use only the Python standard library.** The examiners run a fresh clone with
none of our keys; `python3` is the only requirement. Playwright is needed only for live runs.

**Python backend on GitHub Actions, front end on Base44.** Same code runs on the schedule and in
the CLI. No always-on server: a "run now" press starts a workflow, so it takes a minute, not a
second.

**Confidence is a fixed formula** (see README), so the same input always gives the same output.

**Live mode reads the page in a real browser.** Lovable renders prices with JavaScript, so a plain
HTTP fetch sees no prices. Playwright also gives the cropped per-plan screenshots Maya now makes
by hand ("half of it is just cropping screenshots").

**Live diffs become ordinary signals.** The diff writes plain sentences ("Pro plan shown at
$30/month (was $25/month last week).") into a `cases.json`, and the core decides. One decision
path for live and test, as the brief requires.

**Guards against false flags in live mode**, because a false flag is the worst outcome:
- Switch to monthly billing before reading; if the view still differs from last week, don't
  compare prices (Bolt opens on yearly).
- If more than half the plans vanish, treat it as a broken extraction, not removals.
- Ignore marketing sentences, CTAs and badges; only entitlement lines count as features.
- Packaging changes with no number get lower confidence (0.75) than price or limit changes.
- Two captures a minute apart produced zero changes on all three sites.

**Screenshots live in Base44; JSON recordings stay in the repo.** Screenshots were about 1.5 MB a
run, so they're uploaded to Base44 as public files (pricing pages are public anyway) and not
committed. The JSON snapshots and each run's cases.json and result.json stay in `recordings/`:
they're next week's "before", and the brief needs the repo to run "on data recorded from your
real runs" with no keys, which data behind a Base44 token wouldn't allow.

**The web app only reads.** Entities allow reads for anyone and writes for the admin only; the
Python job writes with a personal access token scoped to this one app. I turned down the App MCP
setup Base44 offered (AI assistants with full read-write access): Maya didn't ask for it, and it
would have put the app behind a sign-in, which she said she won't do ("New login, new tab, it's
dead") and which would lock reviewers out.

**Upserts, not inserts.** Every record is keyed on the run plus its own id, so publishing a run
twice (a retry after a timeout) updates rather than duplicates. Base44's API has no idempotency
key, so this is what makes retries safe.

**Base44's Entities and file APIs are in beta.** All calls to them sit in one module
(`brightloop/store/base44.py`), and a failed publish never fails the run.

**Live runs go out from GitHub Actions, not from the office network.** Low volume: three pages
once a week, pages that robots.txt allows.

**The week filter uses the input's timezone.** An ISO week in Asia/Jerusalem starts Sunday 21:00
or 22:00 UTC depending on DST.

## Disclosure

I work at Base44. The app is built in my personal workspace on the company's Enterprise plan, on
my work laptop, with AI coding tools (Claude Code). No Base44 code, data, prompts or customer
material is used, and no inside knowledge beyond public docs. The interview chat was done with my
work email because the brief asks to keep the same sign-in throughout.
