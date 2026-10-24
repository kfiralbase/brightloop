import { useLatestRun } from "@/lib/queries";
import { formatTime, STATUS_DOT } from "@/lib/format";

export default function HeaderStatus() {
  const { data: run } = useLatestRun();
  if (!run) return null;
  return (
    <div className="flex items-center gap-2 text-xs">
      {run.week && (
        <span className="rounded-md border border-[#E2E8F0] px-2 py-1 font-mono text-[#4F46E5]">{run.week}</span>
      )}
      <span className="flex items-center gap-1.5 text-[#64748B]">
        <span className={`h-2 w-2 rounded-full ${STATUS_DOT[run.status] || "bg-slate-400"}`} />
        <span className="hidden sm:inline">{formatTime(run.started_at)}</span>
      </span>
    </div>
  );
}