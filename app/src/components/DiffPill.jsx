import { ArrowRight } from "lucide-react";

const AFTER = { up: "text-[#E11D48]", down: "text-[#059669]", none: "text-[#0F172A]" };

export default function DiffPill({ before, after, direction, compact }) {
  const size = compact ? "text-xl md:text-2xl" : "";
  return (
    <div className={`flex flex-wrap items-center gap-x-3 gap-y-1 font-display font-extrabold tracking-tight ${size}`}
      style={compact ? undefined : { fontSize: "clamp(2rem, 4vw, 3.25rem)", lineHeight: 1.1 }}>
      <span className="text-[#64748B] line-through decoration-2">{before || "—"}</span>
      <ArrowRight className="h-[0.7em] w-[0.7em] shrink-0 text-[#64748B]" />
      <span className={AFTER[direction] || AFTER.none}>{after || "—"}</span>
    </div>
  );
}