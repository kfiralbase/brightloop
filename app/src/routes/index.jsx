import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useLatestRun, useNewestRun, useRunChanges, useRunSnapshots } from "@/lib/queries";
import { formatTime } from "@/lib/format";
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

// What the newest run is doing, when it isn't the run on screen: still going, or failed.
function RunNotice({ newest, shown }) {
  if (!newest || newest.run_key === shown?.run_key) return null;
  const stale = Date.now() - Date.parse(newest.started_at || 0) > 30 * 60_000;
  if (newest.status === "running" && !stale) {
    return (
      <p className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        A new run started at {formatTime(newest.started_at)} and is still running. This page updates when it finishes.
      </p>
    );
  }
  if (newest.status === "failed" || (newest.status === "running" && stale)) {
    return (
      <p className="rounded-lg border border-[#E11D48]/30 bg-rose-50 px-4 py-3 text-sm text-[#9F1239]">
        The run that started at {formatTime(newest.started_at)} didn't finish.{" "}
        <Link to="/runs/$runKey" params={{ runKey: newest.run_key }} className="underline">See what happened</Link>.
        Below is the last run that did.
      </p>
    );
  }
  return null;
}

function Home() {
  const run = useLatestRun();
  const newest = useNewestRun();
  const queryClient = useQueryClient();
  const lastKey = useRef(null);
  // When the newest run finishes, refresh everything so its results appear without a reload.
  useEffect(() => {
    const n = newest.data;
    const key = n ? `${n.run_key}:${n.status}` : null;
    if (lastKey.current && key !== lastKey.current) queryClient.invalidateQueries();
    lastKey.current = key;
  }, [newest.data, queryClient]);
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
      <RunNotice newest={newest.data} shown={run.data} />
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