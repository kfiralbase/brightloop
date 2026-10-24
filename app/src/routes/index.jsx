import { createFileRoute } from "@tanstack/react-router";
import { useLatestRun, useRunChanges, useRunSnapshots } from "@/lib/queries";
import RunBanner from "@/components/RunBanner";
import ChangeCard from "@/components/ChangeCard";
import SnapshotSection from "@/components/SnapshotSection";
import EmptyState from "@/components/EmptyState";
import Loading from "@/components/Loading";
import RunNowButton from "@/components/RunNowButton";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [{ title: "This week · Brightloop Pricing Watch" }] }),
  component: Home,
});

function Home() {
  const run = useLatestRun();
  const changes = useRunChanges(run.data?.run_key);
  const snaps = useRunSnapshots(run.data?.run_key);

  if (run.isLoading) return <Loading />;
  if (!run.data) return (
    <div className="space-y-4">
      <EmptyState title="No runs yet" text="Nothing has been collected yet. This page fills in after the first weekly run." />
      <div className="flex justify-center"><RunNowButton /></div>
    </div>
  );
  if (changes.isLoading || snaps.isLoading) return <Loading />;

  const list = changes.data || [];
  const snapshots = snaps.data || [];
  const snapsBlock = snapshots.length === 0
    ? <EmptyState title="No snapshots in this run" text="The latest run did not record any pricing pages." />
    : null;

  return (
    <div className="space-y-6 md:space-y-8">
      <RunBanner run={run.data} changeCount={list.length} snapshotCount={snapshots.length} action={<RunNowButton />} />
      {list.length > 0 ? (
        <div className="grid gap-6 lg:grid-cols-[65fr_35fr]">
          <div className="space-y-5">{list.map((c) => <ChangeCard key={c.id} change={c} />)}</div>
          <aside className="space-y-4">
            <h2 className="font-display text-xl font-bold text-[#0F172A]">Current pricing</h2>
            {snapsBlock || snapshots.map((s) => <SnapshotSection key={s.id} snapshot={s} narrow />)}
          </aside>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="font-display text-xl font-bold text-[#0F172A]">Current plans, as checked</h2>
          {snapsBlock || snapshots.map((s) => <SnapshotSection key={s.id} snapshot={s} />)}
        </div>
      )}
    </div>
  );
}