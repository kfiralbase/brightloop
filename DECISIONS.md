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

**Side programs aren't plans.** Lovable's page also has "for students", "for campus" and "for
kids". They aren't steps on the price ladder Maya tracks ("what someone pays or what tier
they're on"), so a card counts as a plan only if it has a known plan name or shows a $ price.
The student discount ("up to 50% off Lovable Pro") is pricing of a sort; left out to keep to
what Maya asked for.

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

**The deck is created in Google Slides in Maya's Drive, not offered as a download.** Maya: "if
it's not already in Google Slides in my Drive when I open my laptop, it's not really saving me
much — I'd still be downloading, converting, checking it looks right." Slack is deferred: "Not
noise if it's accurate and sourced, but I get a hundred pings a day."

**The deck is built by a Base44 backend function, called at the end of the weekly run.** It's
presentation, not a decision, so it can live outside the Python core without breaking "same
logic". Base44's shared Google Slides and Drive connectors hold the OAuth, so no Google refresh
token sits in GitHub. A Base44 trigger on new records wasn't an option: records written through
the API don't fire workflows. Backend functions answer on the app's subdomain even before the
app is published (checked), so the workflow can call it. The function URL is public, so a shared
secret guards it; I generated it and stored it in the app, the repo and `.env` without printing
it. Stacked or side-by-side is decided per slide from the screenshots' sizes, as Maya does by
eye ("depending on how the screenshots came out"). To check the red box before any real change
existed, I added one test change record, rebuilt, looked at the slide, then deleted the record
and rebuilt clean.

**Maya never connects anything.** The Google connector is shared, connected once by whoever
sets the tool up: in production a Brightloop team account with edit rights on the Growth folder,
so decks land where she already looks every Monday ("anything that gets me there without adding
another tab") and nothing depends on one person's login. In this demo my personal Google account
stands in for that team account, and its Growth folder is shared view-only by link so reviewers
can open the deck from the app. Switching to a real account is reconnecting the connector; no
code change.

**The deck copies Maya's layout exactly.** "One slide per competitor, so three slides… Top of
the slide is the homepage screenshot, bottom is the pricing page screenshot… If something
moved, I add a red text box below the pricing shot with a one-liner… If nothing changed, the
slide is just the two screenshots and the competitor name." File "Competitor Deck Wk of
[date]" in the Growth folder. So the capture takes a homepage shot and one pricing-section shot
per competitor, each change carries a `deck_line` for the red box, and each run carries
`week_of` (the Monday) for the file name. Homepage pictures are for the slide only; homepage
changes stay untracked ("features are product's problem").

**Cookie banners are hidden, never accepted.** Lovable's banner offers only "OK", which would
mean consenting on our behalf. The capture presses Reject/Decline when a site has it and
otherwise hides the banner before the screenshot.

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

**Weekly schedule, Monday 07:30 Jerusalem time.** Maya starts at 08:30 ("Monday's been working
fine"). GitHub's cron runs in UTC and Israel changes clocks (2026-10-25), so the workflow is
scheduled at both offsets and only proceeds at 07:xx–08:xx local time, once a day. The same
workflow has a manual "Run workflow" trigger, which is also the "run now" for anyone with repo
access. After each run it commits the JSON recording, so next week's diff has its "before".
Midweek checks are a possible extension.

## Engineering

**Core and test path use only the Python standard library.** The examiners run a fresh clone with
none of our keys; `python3` is the only requirement. Playwright is needed only for live runs.

**The app's file test runs our Python in the browser.** The brief allows a command or an upload
page, and asks for the same logic as the live app. Rewriting the core in JavaScript would make
two implementations; a server-side Python run through GitHub Actions would take a minute or two
and need a token. Pyodide runs the exact modules behind `./run` in the page: no server, no
keys, the file stays on the computer, about 2 seconds including the first load. The modules are
copied into the app as one bundle stamped with its source commit, and a test checks the bundle
alone matches the CLI. The cost is a copy that can go stale; the commit stamp makes that visible.

**Run now is open to anyone, but throttled.** The app has no sign-in (Maya won't log in), so
the button's server function refuses while a run is in progress and for 10 minutes after the
last one started (a run takes about 2 minutes; I first set 30, which was more than needed,
since a running run already blocks a second one). The GitHub token is an app secret scoped to Actions on this one repo, never
sent to the browser. The weekly cron and the button run the same workflow.

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
