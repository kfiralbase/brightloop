import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-[#64748B]">
      <Loader2 className="h-4 w-4 animate-spin" /> Loading…
    </div>
  );
}