import { formatTime, STATUS_DOT } from "@/lib/format";

export default function RunBanner({ run, changeCount, snapshotCount, action }) {
  return (
    <section className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-5 md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <p className="font-mono text-xs uppercase text-[#4F46E5]">{run.week || "Week unknown"}</p>
        {action}
      </div>
      <h1 className="mt-2 font-display font-extrabold tracking-tight text-[#0F172A]" style={{ fontSize: "clamp(2rem, 4vw, 3.25rem)", lineHeight: 1.1 }}>
        {changeCount === 0 ? "No pricing changes since last week" : `${changeCount} pricing ${changeCount === 1 ? "change" : "changes"} this week`}
      </h1>
      <dl className="mt-5 flex flex-wrap gap-x-8 gap-y-3 text-sm">
        <Item label="Latest run" value={formatTime(run.started_at)} />
        <Item label="Status" value={
          <span className="inline-flex items-center gap-1.5 capitalize">
            <span className={`h-2 w-2 rounded-full ${STATUS_DOT[run.status] || "bg-slate-400"}`} />{run.status || "—"}
          </span>} />
        <Item label="Pages checked" value={snapshotCount} />
        {run.deck_url && (
          <Item label="Monday deck" value={
            <a href={run.deck_url} target="_blank" rel="noreferrer" className="text-[#4F46E5] underline underline-offset-2 hover:text-[#4338CA]">
              Open in Google Slides
            </a>} />
        )}
        {run.baselines?.length > 0 && <Item label="First capture" value={run.baselines.join(", ")} />}
      </dl>
    </section>
  );
}

function Item({ label, value }) {
  return (
    <div>
      <dt className="font-mono text-xs uppercase text-[#64748B]">{label}</dt>
      <dd className="mt-0.5 font-semibold text-[#0F172A]">{value}</dd>
    </div>
  );
}