export function formatTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-GB", {
    timeZone: "Asia/Jerusalem",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const STATUS_DOT = {
  ok: "bg-[#059669]",
  partial: "bg-amber-500",
  failed: "bg-[#E11D48]",
};