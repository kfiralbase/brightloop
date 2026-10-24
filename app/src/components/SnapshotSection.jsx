import { ExternalLink } from "lucide-react";
import PlanCard from "@/components/PlanCard";
import { formatTime } from "@/lib/format";

export default function SnapshotSection({ snapshot: s, narrow }) {
  const shots = s.plan_screenshots || [];
  const plans = s.plans || [];
  return (
    <section className="rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 className="font-display text-lg font-bold text-[#0F172A]">{s.competitor}</h3>
        {s.not_checked ? (
          <span className="rounded bg-[#FEF3C7] px-1.5 py-0.5 text-xs font-medium text-[#92400E]">
            Not checked this run (site didn't load) · showing {formatTime(s.fetched_at)}
          </span>
        ) : (
          <span className="text-xs text-[#64748B]">Checked {formatTime(s.fetched_at)}{s.billing_view ? ` · ${s.billing_view}` : ""}</span>
        )}
        {s.url && (
          <a href={s.url} target="_blank" rel="noreferrer" className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-[#4F46E5]">
            Pricing page <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>
      {plans.length === 0 ? (
        <p className="mt-3 text-[#64748B]">No plans were read from this page.</p>
      ) : (
        <div className={`mt-3 flex snap-x items-start gap-3 overflow-x-auto pb-1 ${narrow ? "flex-col" : "md:grid md:grid-cols-2 xl:grid-cols-3"}`}>
          {plans.map((p, i) => (
            <PlanCard key={`${p.name}-${i}`} plan={p} competitor={s.competitor}
              screenshot={shots.find((x) => x.name === p.name)?.url}
              className={narrow ? "w-full" : "w-[78%] shrink-0 snap-start md:w-auto"} />
          ))}
        </div>
      )}
    </section>
  );
}