<script module lang="ts">
  export type RouteStatsSnapshot = {
    currentCrossTrackError: number | null;
    averageCrossTrackError: number | null;
    headingError: number | null;
    maxCrossTrackError: number | null;
    percentile95CrossTrackError: number | null;
    distanceToGoal: number | null;
    lookaheadDistance: number;
    purePursuitActive: boolean;
    sampleCount: number;
  };
</script>

<script lang="ts">
  import { Activity, Gauge, LocateFixed, Route } from "lucide-svelte";

  let {
    stats,
    running = false,
    class: className = "",
  }: {
    stats: RouteStatsSnapshot;
    running?: boolean;
    class?: string;
  } = $props();

  function formatMeters(value: number | null, digits = 3) {
    return value === null || !Number.isFinite(value)
      ? "--"
      : `${value.toFixed(digits)} m`;
  }

  function formatDegrees(value: number | null) {
    return value === null || !Number.isFinite(value)
      ? "--"
      : `${value.toFixed(1)} deg`;
  }

  function formatCurvature(value: number | null) {
    return value === null || !Number.isFinite(value)
      ? "--"
      : `${value.toFixed(3)} 1/m`;
  }
</script>

<div
  class="mt-3 border-t border-gray-100 pt-3 text-xs text-gray-700 {className}"
>
  <div class="mb-2 flex items-center justify-between gap-3">
    <div class="flex items-center gap-2 font-semibold text-gray-900">
      <Route class="h-4 w-4 text-blue-600" />
      Route statistics
    </div>
    <div
      class="rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide {running
        ? 'border-green-200 bg-green-50 text-green-700'
        : 'border-gray-200 bg-gray-50 text-gray-500'}"
    >
      {running ? "Live run" : "Preview"}
    </div>
  </div>

  <div class="grid grid-cols-2 gap-2 xl:grid-cols-3">
    <div class="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
      <div class="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
        <LocateFixed class="h-3.5 w-3.5" />
        Cross track
      </div>
      <div class="font-mono text-sm font-semibold text-gray-950">
        {formatMeters(stats.currentCrossTrackError)}
      </div>
      <div class="mt-1 text-[11px] text-gray-500">
        avg {formatMeters(stats.averageCrossTrackError)} · max {formatMeters(
          stats.maxCrossTrackError,
        )}
      </div>
    </div>

    <div class="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
      <div class="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
        <Activity class="h-3.5 w-3.5" />
        Error spread
      </div>
      <div class="font-mono text-sm font-semibold text-gray-950">
        {formatMeters(stats.percentile95CrossTrackError)}
      </div>
      <div class="mt-1 text-[11px] text-gray-500">
        p95 from {stats.sampleCount} sample{stats.sampleCount === 1 ? "" : "s"}
      </div>
    </div>

    <div class="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
      <div class="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
        <Gauge class="h-3.5 w-3.5" />
        Heading / goal
      </div>
      <div class="font-mono text-sm font-semibold text-gray-950">
        {formatDegrees(stats.headingError)}
      </div>
      <div class="mt-1 text-[11px] text-gray-500">
        goal {formatMeters(stats.distanceToGoal)}
      </div>
    </div>
  </div>
</div>
