# Decision log

Why I built what I built. Quotes are from the marketer interviews.

## Who I built for

**Maya.** All three marketers track competitors by hand, and each one opened with a wish rather
than a problem: Maya wanted "more signups", Daniel "more ad ideas", Noa to know what ships. So I
asked each of them about the last time it actually hurt. Maya's answer was the clearest: every
Monday from 08:30 to 10:30 she rebuilds a competitor deck by hand for the 11:00 leadership sync,
and a pricing move is "the only thing that's ever shifted a decision in that room." She has also
paid for getting it wrong: an AI summary told the team a competitor "cut prices 30%", leadership
started drafting a promo, and it turned out to be false. Since then her rule is "no link, no
number." Her source is public and stable, a competitor's own pricing page, so I can collect it
live, record it, and let anyone rerun it with no keys.

**Not Daniel.** His pain is bigger in hours (about 3 of his 5 weekly hours go to hunting proof
for ad briefs), but his proof lives in ad platforms I can't read properly. He mostly looks at
the US, and Meta's Ad Library API only returns commercial ads delivered in the EU or UK; LinkedIn,
his other channel, has no public API. What's left is scraping against the platforms' terms or a
paid scraping service, which means a key the reviewers would need and the brief says they won't
have. He also needs an "expected CPA" for every brief, and no public source has one; making it up
is exactly the mistake Maya got burned by. He's the obvious next user if an official source opens.

**Not Noa.** She wants to know what competitors ship "before Twitter does", but launches are
usually announced on Twitter first, and as she put it, "nothing reliably beats Twitter." Her real
bottleneck is writing the take afterwards ("That's the bottleneck, not the finding out"). A
writing tool needs an LLM and an API key, so it couldn't give a checkable result on unseen cases
without keys. Maya's problem has none of these limits.

## What counts as a change

**Pricing and packaging only.** Maya: "if the price didn't move, it's product's problem." So
feature launches are skipped, even "Agent 4 is live for every plan"; I first read that as
packaging, asked, and she said no.

**The whole plan, not just the headline price.** She listed "price, plan limits, free tier,
seats, credits", and Noa warned that Maya "misses the bundling and tier changes." When I asked
whether a credit cut or SSO moving up a tier counts even if the price stays the same: "yeah, that
goes in the red box—that's packaging, not features, and it changes what someone gets for their
money."

**Monthly and annual.** "Annual price changes count, I look at both monthly and annual." The
capture reads each page in its monthly view and then its yearly view. An annual move gets its own
line, like `Pro (annual): $21→$23/month`. Replit shows no annual plans, so it has monthly only.
The slide shows the monthly view, because that's what she screenshots today ("whatever the default
view is when the page loads—usually monthly"). But she admitted the gap that leaves: "If only the
annual moved, I'd want to see that... I'd probably miss an annual-only change." So the capture
also photographs the annual view, and when only annual prices moved, that slide shows it instead,
labeled, so the number in the red box is in the picture.

**Promos are noise.** "Promos I ignore until they stick—if it says 'limited time,' it's noise."
Anything with limited-time, promo, coupon or "first month" wording is skipped. If the price stays
after the promo wording is gone, the next run flags it as a real change.

**Three competitors.** "Always Lovable, Replit, and Bolt in the deck." The brief also names v0,
Codex and Claude Code, so I asked about them too: "Always just those three. Leadership doesn't
think of v0 or coding agents as direct pricing competitors—they're more 'developer tools' in
their minds." v0 is in the config, switched off (turning it on adds a fourth slide with no code
change). The core handles any competitor that shows up in an input file.

## Trust

The whole tool rests on Maya's rule, so trust decisions come first.

**Only the competitor's own pricing page counts.** A claim from a news site, a sponsored post or
Reddit is skipped as unverified, with the reason written next to it. Even the competitor's own
blog or X account isn't enough: I first gave those lower confidence, but Maya's rule is binary
and Monday is soon enough, so they're skipped as "not on the pricing page yet." If the price
really moved, the live run will see it on the page. A URL only counts if its path starts with
`/pricing` (or `/plans`), so `lovable.dev/blog/pricing` doesn't sneak in.

**False alarms are worse than misses.** "Flagging a false one is worse," because "we looked dumb
in front of the whole team." So every rule leans toward precision: no change without a before and
an after, rumors skipped, injected instructions stripped and penalized.

**No number comes from a model.** Every number is read straight from the source text by fixed
rules, and confidence is a fixed formula (see the README). The same input always gives the same
output, it runs on unseen cases with no keys, and nothing can be invented. That's also why
`predicted_ctr` is never used: it's a model score, and Daniel lost a brief to a tool that ranked a
2-day-old ad first by it ("That ad died a week later").

**The picture has to match the text.** The numbers come from the page text, but Maya presents the
screenshot. So before the deck, OCR reads each plan card's picture back and checks that it shows
the price and every line under it, that the annual picture shows the annual prices, and that the
pricing section isn't cut off. OCR misreads (S for $, wrapped lines), so prices must match after
cleanup and lines with a little tolerance. On a mismatch the page is captured once more; if it
still doesn't match, the slide goes in marked "check before 11" rather than being dropped, since
she'd rather have the slide than a gap. It adds about half a minute to a run and changes no
decision. I first ran it on real captures and it flagged good cards: small screenshots lost big
price digits and dark cards came back almost empty. Preparing each image (gray, inverted when
dark, enlarged) fixed it: 282 lines from three captures, none missed, while a changed price, line
or annual price is still caught. GitHub's runner has an older Tesseract, and its first run flagged
two more good pictures ("$0" read as "SO", Bolt's "$18*" as "$138" from the whole annual section);
reading each annual card on its own and two more cleanups fixed those, and the next run on the
runner passed for all three sites.

**The live capture never cheats.** If a site shows a bot check, the capture waits up to 20
seconds for it to clear and otherwise doesn't use the page; it never tries to solve it. Cookie
banners are rejected or hidden, never accepted on anyone's behalf. From GitHub's servers Lovable's
homepage often shows a bot check; the slide then reuses the last good homepage picture. I first
captioned it with its date, then dropped the caption: the homepage is only context on the slide,
and the run's notes still record it. Site headers pinned to the top
of the screen are hidden for the pricing pictures (on GitHub's runner Replit's nav sat on top of
the cards); the homepage picture keeps its nav.

## The deck and how it reaches her

**It lands in her Drive, in her layout.** "If it's not already in Google Slides in my Drive when
I open my laptop, it's not really saving me much." She described the slide exactly: one per
competitor, the homepage screenshot, the pricing screenshot, and a red box with a one-liner only
if something moved. The file is "Competitor Deck Wk of [date]" in the Growth folder, and she
presents it as is ("there's no bigger deck"). The pricing shot gets about two thirds of the
slide, because that's what leadership reads; with an even split the cards were too small on
screen-share.

**The red box is short.** "'Pro: $25→$30/month'—keep it short, it's a red box, not a paragraph."

**A midweek change still makes Monday's slide.** If someone presses Run now on Thursday, Monday's
diff would no longer see that change. Maya: "It still goes in Monday's deck, because leadership
doesn't read Slack, they read the slide. If it's not on the slide, it didn't happen." So each deck
belongs to a Monday and collects every change found since the last one, marked "(spotted Thu)."
A deck leadership has already seen is never rewritten.

**A site that didn't load keeps its slide.** "I'd rather see last week's screenshot marked 'not
checked' than an empty slide, because an empty slide just gets me questions I don't have answers
to." The run reuses the last capture, labels it on the slide, and next week compares against the
last real one.

**One Slack message on Monday.** I held off on Slack at first because she gets "a hundred pings a
day". When I asked, she said: "File in the folder plus one Slack message with the link would be
ideal—I'm not hunting through Drive on Monday morning." So only the Monday run posts, once, with
the link and the red-box lines. Run now stays quiet. Brightloop's Slack doesn't exist, so the demo
posts to a Slack workspace of my own through an incoming webhook. I know reviewers can't open it;
it's there to show the delivery works end to end (the screen recording shows a message landing),
and pointing it at a real team's channel is a new webhook URL in the repo secrets, no code change.
Without the secret the step is skipped, so a fresh clone never needs Slack.

**She'll still check it.** "If something's off, it's my name on it." So the deck has to be easy
to check, not perfect: a site that didn't load is labeled on its slide, and every change links to
its source.

**Maya never connects anything.** The Google connection is set up once by whoever runs the tool.
In this demo that's my personal Google account standing in for a team account.

## When it runs

**Monday 07:30, on two clocks.** She starts at 08:30, so the deck has to be there by then. I
first relied on GitHub's scheduler, then tested it: a one-off schedule still hadn't started 20
minutes after its time. So a scheduled workflow in the Base44 app starts the run at 07:30 Israel
time, and GitHub's own schedule is a fallback at 07:45 that skips itself if a run already
happened that day. Base44's workflows are in beta, which is exactly why they aren't the only
clock. Both would have to fail the same morning for the deck to be missing.

## How it's built

**Base44 for what Maya and the reviewers see, Python for the logic.** The Base44 app is the
front end (this week, history, the run log, a file test page), the database (runs, changes,
skipped signals, snapshots), the scheduler, and the function that builds the deck through Base44's
Google Slides and Drive connectors. The logic and the backend are Python, run by GitHub Actions,
for three reasons:
- The brief's test runs on a fresh clone with no keys, so the core uses only the Python standard
  library: `./run --input cases.json --output result.json` needs nothing but `python3` (3.9 is
  enough, the version macOS ships).
- The capture needs a real browser: Lovable renders its prices with JavaScript, and Maya needs
  screenshots. Playwright on a GitHub runner does that; a Base44 function can't.
- One decision path. The live run turns what changed into plain sentences in the same format as
  `cases.json` ("Pro plan shown at $30/month (was $25/month last week)."), and the same core
  decides. Only the source changes, as the brief asks.

**The file test page runs the same Python in the browser.** Rewriting the core in JavaScript
would mean two implementations to keep in sync. The page runs the exact modules behind `./run`
with Pyodide: no server, no keys, and the file never leaves the computer. A test fails if the
app's copy drifts from the repo.

**Recordings stay in the repo, screenshots go to Base44.** The JSON snapshots are next week's
"before" and the data the repo replays with no keys, so they're committed. Screenshots are large
and public anyway, so they're uploaded to Base44 instead.

**Safe by default.** The app only reads; the Python job writes with a token scoped to this one
app, and publishing the same run twice updates rather than duplicates. Run now is open to anyone
(Maya won't log in) but refuses while a run is going and for 10 minutes after the last one. A
broken input, a duplicate id or even a bug in the code still produces a valid result file, with
every input id placed and the problem listed in `run.errors`.

**One extractor for every site.** It finds plan cards by plan names and prices, not by a site's
HTML, so a redesign is less likely to break it and a new competitor is one line of config. To
avoid false flags it compares the same billing view every week, treats more than half the plans
vanishing as a broken read rather than removals, and ignores buttons, badges and dropdown values.

**Tested on cases I hadn't seen.** Before submitting I wrote new inputs against the rules rather
than the code: other units, other word orders, a new plan, URLs that only look like a pricing
page, plain-text injections. Each one that came out wrong was fixed and kept as a test. A later
review found three more ways of writing a credit cut that were missed ("80 monthly credits (was
100)", "100 monthly credits → 80 monthly credits", "monthly credits 100→80"), which would have
broken "the whole plan, not just the headline price". Fixed and kept as tests; without "from", only
an arrow counts, so a range like "5 to 50 seats" is never read as a change.

**The app's code is copied into `app/`.** The brief wants all the code in the repo, and Base44's
GitHub sync can only create a new repository. A script exports the app's source into `app/`.

## What I chose not to build

- **The brief's nice-to-haves** (multi-language, SSO, dark mode, an analytics dashboard, A/B
  auto-winner, a mobile app). Maya won't open another tool: "New login, new tab, it's dead."
- **Merging duplicate launches.** I built it for Noa's problem, then removed it: for Maya every
  launch is skipped anyway. Two reports of the same pricing change are still merged into one item.
- **Replit's bigger credit packs** ($225, $440… in a dropdown). Maya: "I'd probably miss it—I
  screenshot the main pricing page, not every dropdown." She didn't ask for it; it's easy to add.
- **Side programs** (Lovable for students, campus and kids). They aren't steps on the price ladder
  she tracks.
- **Homepage change tracking.** The homepage is on the slide as context only.

## Disclosure

I work at Base44. The app is built in my personal workspace on the company's Enterprise plan, on
my work laptop, with AI coding tools (Claude Code). No Base44 code, data, prompts or customer
material is used, and no inside knowledge beyond public docs. The interview chat was done with my
work email because the brief asks to keep the same sign-in throughout.
