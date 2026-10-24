import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { Loader2, Play } from "lucide-react";
import { getRunNowStatus, startRunNow } from "@/lib/run-now";

const POLL_MS = 15_000;

// Starts a capture on GitHub Actions, then polls until it finishes and refreshes the page data.
export default function RunNowButton() {
  const start = useServerFn(startRunNow);
  const status = useServerFn(getRunNowStatus);
  const queryClient = useQueryClient();
  const [state, setState] = useState({ phase: "idle" });
  const timer = useRef(null);

  // Opening the page while a run is going (from this button, the schedule, or GitHub) shows it.
  useEffect(() => {
    let alive = true;
    status().then((s) => {
      const run = s?.run;
      if (alive && run && run.status !== "completed") {
        setState({ phase: "running", message: "A run is in progress." });
        poll(Date.parse(run.startedAt));
      }
    }).catch(() => {});
    return () => { alive = false; clearTimeout(timer.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function poll(sinceMs) {
    timer.current = setTimeout(async () => {
      try {
        const s = await status();
        const run = s.run;
        const ours = run && Date.parse(run.startedAt) >= sinceMs - 60_000;
        if (ours && run.status === "completed") {
          await queryClient.invalidateQueries();
          setState({ phase: run.conclusion === "success" ? "finished" : "failed",
            message: run.conclusion === "success" ? "Done. The page now shows the new run." : `The run ended: ${run.conclusion}.` });
          return;
        }
      } catch {
        // a missed poll is fine; try again
      }
      if (Date.now() - sinceMs < 15 * 60_000) poll(sinceMs);
      else setState({ phase: "failed", message: "Still not finished after 15 minutes. Check back later." });
    }, POLL_MS);
  }

  async function onClick() {
    setState({ phase: "starting" });
    try {
      const out = await start();
      if (out.ok) {
        setState({ phase: "running" });
        poll(Date.now());
      } else if (out.run && out.run.status !== "completed") {
        setState({ phase: "running", message: "A run is already in progress." });
        poll(Date.parse(out.run.startedAt));
      } else {
        const when = out.nextAt ? ` Try again after ${new Date(out.nextAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Jerusalem" })}.` : "";
        setState({ phase: "refused", message: `${out.reason}${when}` });
      }
    } catch (err) {
      setState({ phase: "failed", message: err?.message || "Couldn't start the run." });
    }
  }

  const busy = state.phase === "starting" || state.phase === "running";
  return (
    <div className="flex flex-col items-start gap-2">
      <button type="button" onClick={onClick} disabled={busy}
        className="inline-flex min-h-[40px] items-center gap-2 rounded-lg bg-[#4F46E5] px-4 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
        {state.phase === "starting" ? "Starting…" : state.phase === "running" ? "Running…" : "Run now"}
      </button>
      {state.phase === "running" && (
        <p className="text-sm text-[#64748B]">{state.message || "Checking the pricing pages."} New results in about 3 minutes.</p>
      )}
      {["refused", "failed", "finished"].includes(state.phase) && (
        <p className={`text-sm ${state.phase === "finished" ? "text-[#047857]" : "text-[#9F1239]"}`}>{state.message}</p>
      )}
    </div>
  );
}
