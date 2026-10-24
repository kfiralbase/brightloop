import { createServerFn } from "@tanstack/react-start";
import { secrets } from "base44:runtime";

// "Run now" starts the repo's weekly workflow on GitHub Actions (capture → decide → publish).
// Anyone can press it, so the server refuses while a run is going and for COOLDOWN_MINUTES
// after the last one started. The GitHub token stays here: it's an app secret, never sent to
// the browser. It needs Actions read/write on this one repository only.
const REPO = "kfiralbase/brightloop";
const WORKFLOW = "weekly.yml";
const COOLDOWN_MINUTES = 10; // a run takes about 2 minutes; this only stops back-to-back presses

async function github(path, init = {}) {
  const token = await secrets.get("GITHUB_TOKEN");
  if (!token) return { configured: false };
  const res = await fetch(`https://api.github.com/repos/${REPO}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "brightloop-pricing-watch",
      ...(init.headers || {}),
    },
  });
  return { configured: true, res };
}

async function latestRun() {
  const { configured, res } = await github(`/actions/workflows/${WORKFLOW}/runs?per_page=1`);
  if (!configured) return { configured: false };
  if (!res.ok) return { configured: true, error: `GitHub answered ${res.status}.` };
  const run = (await res.json()).workflow_runs?.[0];
  // Only what the page needs: no links into the private repo.
  return {
    configured: true,
    run: run ? { status: run.status, conclusion: run.conclusion, startedAt: run.created_at, trigger: run.event } : null,
  };
}

export const getRunNowStatus = createServerFn({ method: "GET" }).handler(async () => latestRun());

export const startRunNow = createServerFn({ method: "POST" }).handler(async () => {
  const state = await latestRun();
  if (!state.configured) return { ok: false, reason: "Run now isn't set up yet: the app has no GitHub token." };
  if (state.error) return { ok: false, reason: state.error };
  const last = state.run;
  if (last && last.status !== "completed") return { ok: false, reason: "A run is already in progress.", run: last };
  if (last) {
    const nextAt = Date.parse(last.startedAt) + COOLDOWN_MINUTES * 60_000;
    if (Date.now() < nextAt) {
      return { ok: false, reason: `The last run started less than ${COOLDOWN_MINUTES} minutes ago.`, nextAt, run: last };
    }
  }
  const { res } = await github(`/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ref: "main" }),
  });
  if (res.status !== 204) return { ok: false, reason: `GitHub refused to start the run (${res.status}).` };
  return { ok: true };
});
