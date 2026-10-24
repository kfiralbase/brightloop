import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useRuns, useChangeCounts } from "@/lib/queries";
import { formatTime, STATUS_DOT } from "@/lib/format";
import EmptyState from "@/components/EmptyState";
import Loading from "@/components/Loading";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const STATUS_LABEL = { running: "Running…", ok: "Ok", partial: "Partial", failed: "Failed" };

export const Route = createFileRoute("/runs/")({
  head: () => ({ meta: [{ title: "Runs · Brightloop Pricing Watch" }] }),
  component: RunsPage,
});

function RunsPage() {
  const navigate = useNavigate();
  const q = useRuns();
  const { data: counts = {} } = useChangeCounts();
  const runs = q.data?.pages.flatMap((p) => p.items) || [];

  return (
    <TooltipProvider>
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-[#0F172A] md:text-4xl">Runs</h1>
        <p className="mt-1 text-[#64748B]">Every collection run, newest first. Open a run to see errors and skipped signals.</p>
      </div>
      {q.isLoading ? <Loading /> : runs.length === 0 ? (
        <EmptyState title="No runs yet" text="No runs have been recorded yet." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[#E2E8F0]">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-[#F8FAFC] font-mono text-xs uppercase text-[#64748B]">
              <tr>{["Time", "Mode", "Week", "Status", "Changes", "Skipped", "Baselines"].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} onClick={() => navigate({ to: "/runs/$runKey", params: { runKey: r.run_key } })}
                  className="cursor-pointer border-t border-[#E2E8F0] hover:bg-[#F8FAFC]">
                  <td className="px-4 py-3 font-medium text-[#0F172A]">{formatTime(r.started_at)}</td>
                  <td className="px-4 py-3 capitalize">{r.mode || "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs">{r.week || "—"}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1.5 capitalize">
                      <span className={`h-2 w-2 rounded-full ${STATUS_DOT[r.status] || "bg-slate-400"}`} />{STATUS_LABEL[r.status] || r.status || "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">{counts[r.run_key] ?? 0}</td>
                  <td className="px-4 py-3">{r.skipped_count ?? 0}</td>
                  <td className="px-4 py-3">
                    {r.baselines?.length ? (
                      <Tooltip>
                        <TooltipTrigger asChild><span className="cursor-help underline decoration-dotted">{r.baselines.join(", ")}</span></TooltipTrigger>
                        <TooltipContent>First capture for these competitors; nothing to compare yet.</TooltipContent>
                      </Tooltip>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {q.hasNextPage && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => q.fetchNextPage()} disabled={q.isFetchingNextPage}>Load more</Button>
        </div>
      )}
    </div>
    </TooltipProvider>
  );
}