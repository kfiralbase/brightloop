export default function ConfidenceBadge({ value }) {
  if (value == null) return null;
  const pct = Math.round(value * 100);
  const tone = value >= 0.8 ? "border-[#059669]/30 bg-emerald-50 text-[#047857]"
    : value >= 0.5 ? "border-amber-300 bg-amber-50 text-amber-800"
    : "border-[#E2E8F0] bg-[#F8FAFC] text-[#64748B]";
  return (
    <span className={`rounded-md border px-2 py-0.5 font-mono text-xs ${tone}`}>{pct}% confidence</span>
  );
}