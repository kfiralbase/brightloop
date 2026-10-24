import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { useRun, useSkipped } from "@/lib/queries";
import { formatTime, STATUS_DOT } from "@/lib/format";
import EmptyState from "@/components/EmptyState";
import Loading from "@/components/Loading";

export const Route = createFileRoute("/runs/$runKey")({
  head: ({ params }) => ({ meta: [{ title: `Run ${params.runKey} · Brightloop Pricing Watch` }] }),
  component: RunDetail,
});

function RunDetail() {
  const { runKey } = Route.useParams();
  const run = useRun(runKey);
  const skipped = useSkipped(runKey);

  if (run.isLoading) return <Loading />;
  const r = run.data;

  return (
    <div className="space-y-8">
      <Link to="/runs" className="inline-flex min-h-[40px] items-center gap-1.5 text-sm font-medium text-[#64748B] hover:text-[#0F172A]">
        <ArrowLeft className="h-4 w-4" /> All runs
      </Link>
      {!r ? <EmptyState title="Run not found" text={`No run with key ${runKey}.`} /> : (
        <>
          <div>
            <p className="font-mono text-xs text-[#4F46E5]">{r.run_key}</p>
            <h1 className="mt-1 font-display text-3xl font-extrabold tracking-tight text-[#0F172A] md:text-4xl">{formatTime(r.started_at)}</h1>
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-[#64748B]">
              <span className="inline-flex items-center gap-1.5 capitalize text-[#0F172A]">
                <span className={`h-2 w-2 rounded-full ${STATUS_DOT[r.status] || "bg-slate-400"}`} />{r.status}
              </span>
              <span className="capitalize">Mode: {r.mode || "—"}</span>
              <span>Week: {r.week || "—"}</span>
              {r.cost_usd != null && <span>Cost: ${r.cost_usd.toFixed(2)}</span>}
              {r.deck_url && <a href={r.deck_url} target="_blank" rel="noreferrer" className="text-[#4F46E5] underline">Deck</a>}
              {r.log_url && <a href={r.log_url} target="_blank" rel="noreferrer" className="text-[#4F46E5] underline">Workflow log</a>}
            </div>
          </div>
          <section>
            <h2 className="font-display text-xl font-bold text-[#0F172A]">Errors</h2>
            {r.status === "running" ? <p className="mt-2 text-[#64748B]">Still running. Errors, if any, appear here when it finishes.</p>
              : (r.errors || []).length === 0 ? <p className="mt-2 text-[#64748B]">No errors in this run.</p> : (
              <ul className="mt-3 space-y-2">
                {r.errors.map((e, i) => (
                  <li key={i} className="rounded-lg border border-[#E11D48]/30 bg-rose-50 p-3 font-mono text-xs text-[#9F1239] break-words">{e}</li>
                ))}
              </ul>
            )}
          </section>
          <section>
            <h2 className="font-display text-xl font-bold text-[#0F172A]">Skipped signals</h2>
            {skipped.isLoading ? <Loading /> : (skipped.data || []).length === 0 ? (
              <p className="mt-2 text-[#64748B]">No signals were skipped in this run.</p>
            ) : (
              <ul className="mt-3 divide-y divide-[#E2E8F0] rounded-lg border border-[#E2E8F0]">
                {skipped.data.map((s) => (
                  <li key={s.id} className="p-4">
                    <p className="font-mono text-xs text-[#64748B]">{s.signal_id || "—"}</p>
                    <p className="mt-1 whitespace-pre-line text-[#0F172A]">{s.reason}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}