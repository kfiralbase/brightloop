import { useState } from "react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { ImageOff } from "lucide-react";

export default function ScreenshotTile({ url, alt }) {
  const [open, setOpen] = useState(false);
  if (!url) {
    return (
      <div className="flex h-24 items-center justify-center gap-2 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] text-xs text-[#64748B]">
        <ImageOff className="h-4 w-4" /> No screenshot
      </div>
    );
  }
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} aria-label={`Enlarge ${alt}`}
        className="block w-full cursor-zoom-in overflow-hidden rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] transition hover:border-[#4F46E5]">
        <img src={url} alt={alt} loading="lazy" className="block h-auto w-full object-contain" />
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[92vh] w-[96vw] max-w-6xl overflow-auto p-3">
          <DialogTitle className="pr-8 text-sm font-semibold">{alt}</DialogTitle>
          <img src={url} alt={alt} className="h-auto w-full rounded-md border border-[#E2E8F0] object-contain" />
        </DialogContent>
      </Dialog>
    </>
  );
}