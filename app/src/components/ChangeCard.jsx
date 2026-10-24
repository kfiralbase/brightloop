import { ExternalLink } from "lucide-react";
import DiffPill from "@/components/DiffPill";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import ScreenshotTile from "@/components/ScreenshotTile";
import { formatTime } from "@/lib/format";

export default function ChangeCard({ change: c, compact }) {
  return (
    <article className={`rounded-lg border border-[#E2E8F0] bg-white ${compact ? "p-4 md:p-5" : "p-5 md:p-7"}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-[#0F172A] px-2 py-0.5 text-xs font-semibold text-white">{c.competitor}</span>
        <span className="font-semibold text-[#0F172A]">{c.plan}</span>
        {c.field && <span className="font-mono text-xs text-[#64748B]">{c.field}</span>}
        <span className="ml-auto"><ConfidenceBadge value={c.confidence} /></span>
      </div>
      <div className={`grid gap-5 ${compact ? "mt-3 md:grid-cols-[1fr_220px]" : "mt-5 lg:grid-cols-[1fr_260px]"}`}>
        <div className="min-w-0">
          <DiffPill before={c.before} after={c.after} direction={c.direction} compact={compact} />
          {c.action && <Block label="Action" text={c.action} />}
          {c.why && <Block label="Why" text={c.why} />}
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-[#64748B]">
            {c.source && (
              <a href={c.source} target="_blank" rel="noreferrer"
                className="inline-flex min-h-[32px] items-center gap-1.5 rounded-md border border-[#E2E8F0] px-3 font-medium text-[#4F46E5] hover:bg-[#F8FAFC]">
                Source <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
            <span>Detected {formatTime(c.detected_at)}</span>
            {compact && c.week && <span className="font-mono">{c.week}</span>}
          </div>
        </div>
        <ScreenshotTile url={c.screenshot_url} alt={`${c.competitor} ${c.plan} screenshot`} />
      </div>
    </article>
  );
}

function Block({ label, text }) {
  return (
    <div className="mt-4">
      <p className="font-mono text-xs uppercase text-[#64748B]">{label}</p>
      <p className="mt-1 whitespace-pre-line leading-relaxed text-[#0F172A]">{text}</p>
    </div>
  );
}