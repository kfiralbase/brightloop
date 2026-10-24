import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useChangeHistory, useCompetitors } from "@/lib/queries";
import ChangeCard from "@/components/ChangeCard";
import EmptyState from "@/components/EmptyState";
import Loading from "@/components/Loading";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/history")({
  validateSearch: (s) => ({ competitor: typeof s.competitor === "string" ? s.competitor : undefined }),
  head: () => ({ meta: [{ title: "History · Brightloop Pricing Watch" }] }),
  component: HistoryPage,
});

function HistoryPage() {
  const { competitor } = Route.useSearch();
  const navigate = useNavigate();
  const { data: competitors = [] } = useCompetitors();
  const q = useChangeHistory(competitor);
  const items = q.data?.pages.flatMap((p) => p.items) || [];
  const chips = [undefined, ...competitors];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-[#0F172A] md:text-4xl">History</h1>
        <p className="mt-1 text-[#64748B]">Every verified change, newest first.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {chips.map((c) => (
          <button key={c || "all"} type="button" onClick={() => navigate({ to: "/history", search: { competitor: c } })}
            className={`min-h-[40px] rounded-lg border px-4 text-sm font-medium ${competitor === c ? "border-[#0F172A] bg-[#0F172A] text-white" : "border-[#E2E8F0] text-[#64748B] hover:text-[#0F172A]"}`}>
            {c || "All"}
          </button>
        ))}
      </div>
      {q.isLoading ? <Loading /> : items.length === 0 ? (
        <EmptyState title="No changes recorded" text={competitor ? `No changes have been recorded for ${competitor}.` : "No pricing changes have been recorded yet."} />
      ) : (
        <div className="space-y-4">
          {items.map((c) => <ChangeCard key={c.id} change={c} compact />)}
          {q.hasNextPage && (
            <div className="flex justify-center">
              <Button variant="outline" onClick={() => q.fetchNextPage()} disabled={q.isFetchingNextPage}>
                {q.isFetchingNextPage ? "Loading…" : "Load more"}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}