import { useQuery, useInfiniteQuery } from "@tanstack/react-query";
import { base44 } from "@/api/base44Client";

// The newest run that produced results. A run that is still going, or one that failed before
// capturing anything, doesn't replace what the page shows.
export function useLatestRun() {
  return useQuery({
    queryKey: ["latestRun"],
    queryFn: async () =>
      (await base44.entities.Run.filter({ status: { $in: ["ok", "partial"] } }, { sort: "-started_at", limit: 1 })).items[0] || null,
  });
}

// The newest run of any status, polled, so the page can say "running" or "last run failed".
export function useNewestRun() {
  return useQuery({
    queryKey: ["newestRun"],
    queryFn: async () => (await base44.entities.Run.filter({}, { sort: "-started_at", limit: 1 })).items[0] || null,
    refetchInterval: 15000,
  });
}

export function useRunChanges(runKey) {
  return useQuery({
    queryKey: ["changes", runKey],
    enabled: !!runKey,
    queryFn: async () => (await base44.entities.Change.filter({ run_key: runKey }, { sort: "-detected_at", limit: 100 })).items,
  });
}

export function useRunSnapshots(runKey) {
  return useQuery({
    queryKey: ["snapshots", runKey],
    enabled: !!runKey,
    queryFn: async () => (await base44.entities.Snapshot.filter({ run_key: runKey }, { sort: "competitor", limit: 20 })).items,
  });
}

export function useCompetitors() {
  return useQuery({
    queryKey: ["competitors"],
    queryFn: async () => (await base44.entities.Change.list({ distinct: "competitor" })).items.filter(Boolean),
  });
}

export function useChangeHistory(competitor) {
  return useInfiniteQuery({
    queryKey: ["history", competitor || "all"],
    initialPageParam: undefined,
    queryFn: ({ pageParam }) =>
      base44.entities.Change.filter(competitor ? { competitor } : {}, { sort: "-detected_at", limit: 30, cursor: pageParam }),
    getNextPageParam: (last) => (last.has_more ? last.next_cursor : undefined),
  });
}

export function useRuns() {
  return useInfiniteQuery({
    queryKey: ["runs"],
    initialPageParam: undefined,
    queryFn: ({ pageParam }) => base44.entities.Run.filter({}, { sort: "-started_at", limit: 50, cursor: pageParam }),
    getNextPageParam: (last) => (last.has_more ? last.next_cursor : undefined),
    refetchInterval: 15000, // a running run turns into ok/failed without a reload
  });
}

export function useChangeCounts() {
  return useQuery({
    queryKey: ["changeCounts"],
    queryFn: async () => {
      const { rows } = await base44.entities.Change.aggregate({ query: {}, groupBy: "run_key" });
      return Object.fromEntries(rows.map((r) => [r.run_key, r.count]));
    },
  });
}

export function useRun(runKey) {
  return useQuery({
    queryKey: ["run", runKey],
    queryFn: async () => (await base44.entities.Run.filter({ run_key: runKey }, { limit: 1 })).items[0] || null,
  });
}

export function useSkipped(runKey) {
  return useQuery({
    queryKey: ["skipped", runKey],
    queryFn: async () => (await base44.entities.Skipped.filter({ run_key: runKey }, { limit: 200 })).items,
  });
}