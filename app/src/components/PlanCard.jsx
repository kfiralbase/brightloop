import { useState } from "react";
import { Check } from "lucide-react";
import ScreenshotTile from "@/components/ScreenshotTile";

export default function PlanCard({ plan: p, screenshot, competitor, className = "" }) {
  const [all, setAll] = useState(false);
  const lines = p.lines || [];
  const shown = all ? lines : lines.slice(0, 6);
  return (
    <div className={`rounded-lg border border-[#E2E8F0] bg-white p-3 ${className}`}>
      <div className="flex items-baseline justify-between gap-2">
        <p className="font-semibold text-[#0F172A]">{p.name}</p>
        <p className="font-display text-lg font-extrabold text-[#0F172A]">{p.price || "—"}</p>
      </div>
      <div className="mt-3"><ScreenshotTile url={screenshot} alt={`${competitor} ${p.name} plan`} /></div>
      {lines.length > 0 && (
        <div className="mt-3">
          <p className="font-mono text-xs uppercase text-[#64748B]">Includes</p>
          <ul className="mt-1.5 space-y-1">
            {shown.map((l, i) => (
              <li key={i} className="flex gap-2 text-[#0F172A]">
                <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#059669]" />{l}
              </li>
            ))}
          </ul>
          {lines.length > 6 && (
            <button type="button" onClick={() => setAll(!all)} className="mt-2 text-xs font-medium text-[#4F46E5]">
              {all ? "Show less" : `Show all (${lines.length})`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}