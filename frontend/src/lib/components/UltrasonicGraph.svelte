<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { Skeleton } from "$lib/components/ui/skeleton";
  import * as Chart from "$lib/components/ui/chart/index.js";
  import { AlertTriangle, Activity, Waves } from "lucide-svelte";
  import { scaleUtc } from "d3-scale";
  import { curveNatural } from "d3-shape";
  import { AreaChart, Area, LinearGradient, Highlight } from "layerchart";
  import type { DistanceEntry } from "$lib/types";

  let { distanceHistory }: { distanceHistory: DistanceEntry[] } = $props();

  const chartConfig = {
    value: { label: "Distance", color: "var(--chart-1)" },
  } satisfies Chart.ChartConfig;

  const MAX_DISTANCE = 50;
  const OBSTACLE_THRESHOLD = 20;

  function isValidDistance(value: number) {
    return Number.isFinite(value) && value > 0;
  }

  function formatDistance(value: number) {
    if (!isValidDistance(value)) return "--";
    return `${Math.min(value, MAX_DISTANCE).toFixed(1)} cm`;
  }

  function createSeries(
    entries: DistanceEntry[],
    key: keyof Pick<
      DistanceEntry,
      "distance_left" | "distance_right" | "distance_front"
    >,
  ) {
    const rawValues = entries.map((entry) => entry[key]);
    const validValues = rawValues.filter(isValidDistance);
    const lastValue = rawValues.at(-1) ?? -1;

    return {
      points: entries
        .filter((entry) => isValidDistance(entry[key]))
        .map((entry) => ({
          date: new Date(entry.timestamp),
          value: Math.min(entry[key], MAX_DISTANCE),
        })),
      validCount: validValues.length,
      latestValue: lastValue,
      isStale: validValues.length === 0,
    };
  }

  const leftSeries = $derived(createSeries(distanceHistory, "distance_left"));
  const rightSeries = $derived(createSeries(distanceHistory, "distance_right"));
  const frontSeries = $derived(createSeries(distanceHistory, "distance_front"));

  const chartSections = $derived([
    {
      key: "left",
      title: "Left Ultrasonic",
      subtitle: "Left wheel-side range sensor",
      data: leftSeries.points,
      validCount: leftSeries.validCount,
      latestValue: leftSeries.latestValue,
      isStale: leftSeries.isStale,
      gradientId: "gradient-left",
    },
    {
      key: "right",
      title: "Right Ultrasonic",
      subtitle: "Right wheel-side range sensor",
      data: rightSeries.points,
      validCount: rightSeries.validCount,
      latestValue: rightSeries.latestValue,
      isStale: rightSeries.isStale,
      gradientId: "gradient-right",
    },
    {
      key: "front",
      title: "Front ToF",
      subtitle: "Forward obstacle distance sensor",
      data: frontSeries.points,
      validCount: frontSeries.validCount,
      latestValue: frontSeries.latestValue,
      isStale: frontSeries.isStale,
      gradientId: "gradient-front",
    },
  ]);

  const hasAnyValidData = $derived(
    chartSections.some((section) => section.validCount > 0),
  );
</script>

{#if distanceHistory.length === 0}
  <Skeleton class="w-full h-[400px] rounded-sm" />
{:else}
  <Card.Root
    class="w-full h-full overflow-hidden border border-gray-100 bg-white shadow-sm"
  >
    <Card.Header
      class="space-y-3 border-b border-gray-100 bg-gradient-to-r from-white to-gray-50/70"
    >
      <div
        class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
      >
        <div class="space-y-1">
          <Card.Title class="flex items-center gap-2">
            <Waves class="h-5 w-5" />
            Distance Sensors
          </Card.Title>
          <Card.Description>
            Left ultrasonic, right ultrasonic, and front ToF readings. Invalid
            samples such as -1 or -2 are treated as no-signal values.
          </Card.Description>
        </div>

        <div
          class="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold {hasAnyValidData
            ? 'border-green-200 bg-green-50 text-green-700'
            : 'border-amber-200 bg-amber-50 text-amber-700'}"
        >
          {#if hasAnyValidData}
            <Activity class="h-3.5 w-3.5" />
            Live data present
          {:else}
            <AlertTriangle class="h-3.5 w-3.5" />
            No valid sensor readings
          {/if}
        </div>
      </div>

      <div class="grid gap-2 sm:grid-cols-3">
        {#each chartSections as section (section.key)}
          <div
            class="rounded-lg border p-3 transition-colors {section.isStale
              ? 'border-amber-200 bg-amber-50/80'
              : 'border-gray-200 bg-white'}"
          >
            <div class="flex items-center justify-between gap-2">
              <div>
                <div class="text-xs font-semibold text-gray-700">
                  {section.title}
                </div>
                <div class="text-[11px] text-gray-500">{section.subtitle}</div>
              </div>
              <div
                class="rounded-full px-2 py-0.5 text-[11px] font-semibold {section.isStale
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-green-100 text-green-700'}"
              >
                {section.isStale ? "stale" : "live"}
              </div>
            </div>
            <div class="mt-2 font-mono text-sm text-gray-900">
              {formatDistance(section.latestValue)}
            </div>
          </div>
        {/each}
      </div>
    </Card.Header>

    <Card.Content class="space-y-4 p-4 sm:p-6">
      {#each chartSections as section (section.key)}
        <div
          class="space-y-2 rounded-xl border border-gray-100 bg-gray-50/60 p-3 sm:p-4"
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="text-sm font-medium text-gray-700">{section.title}</div>
            <div class="text-xs font-mono text-gray-500">
              Latest: {formatDistance(section.latestValue)}
            </div>
          </div>

          {#if section.isStale}
            <div
              class="flex min-h-[180px] flex-col items-center justify-center rounded-lg border border-dashed border-amber-200 bg-amber-50 px-4 py-8 text-center"
            >
              <AlertTriangle class="mb-2 h-8 w-8 text-amber-500" />
              <div class="text-sm font-semibold text-amber-800">
                No valid readings
              </div>
              <p class="mt-1 max-w-md text-xs text-amber-700">
                The sensor is currently returning only sentinel values, so the
                chart is intentionally muted instead of implying open space.
              </p>
            </div>
          {:else}
            <Chart.Container config={chartConfig}>
              <AreaChart
                data={section.data}
                x="date"
                y="value"
                annotations={[
                  {
                    type: "line",
                    y: OBSTACLE_THRESHOLD,
                    label: "Obstacle",
                    labelXOffset: 4,
                    labelYOffset: 2,
                    props: {
                      label: { class: "fill-red-500" },
                      line: { class: "[stroke-dasharray:2,2] stroke-red-500" },
                    },
                  },
                ]}
                xScale={scaleUtc()}
                yPadding={[0, 25]}
                axis="y"
                props={{
                  xAxis: {
                    format: (v: Date) => v.toLocaleTimeString(),
                  },
                  yAxis: {
                    format: (v: number) =>
                      v === MAX_DISTANCE ? `${MAX_DISTANCE}+ cm` : `${v} cm`,
                  },
                }}
              >
                {#snippet marks({ context, series })}
                  {@const thresholdOffset =
                    context.yScale(OBSTACLE_THRESHOLD) /
                    (context.height + context.padding.bottom)}
                  {#each series as s (s.key)}
                    <LinearGradient
                      id={section.gradientId}
                      stops={[
                        [
                          thresholdOffset,
                          section.isStale
                            ? "rgba(245, 158, 11, 0.9)"
                            : "var(--chart-2)",
                        ],
                        [
                          thresholdOffset,
                          section.isStale
                            ? "rgba(100, 116, 139, 0.95)"
                            : "var(--chart-1)",
                        ],
                      ]}
                      units="userSpaceOnUse"
                      vertical
                    >
                      {#snippet children({ gradient })}
                        <Area
                          y0={() => OBSTACLE_THRESHOLD}
                          line={{ stroke: gradient }}
                          fill={gradient}
                          fillOpacity={0.35}
                          curve={curveNatural}
                        />
                      {/snippet}
                    </LinearGradient>
                  {/each}
                {/snippet}

                {#snippet highlight({ context })}
                  {@const value =
                    context.tooltip?.data && context.y(context.tooltip?.data)}
                  <Highlight
                    lines
                    points={{
                      fill:
                        value <= OBSTACLE_THRESHOLD
                          ? "var(--chart-1)"
                          : "var(--chart-2)",
                    }}
                  />
                {/snippet}

                {#snippet tooltip()}
                  <Chart.Tooltip
                    indicator="dot"
                    labelFormatter={(v: Date) => v.toLocaleTimeString()}
                  />
                {/snippet}
              </AreaChart>
            </Chart.Container>
          {/if}
        </div>
      {/each}
    </Card.Content>
  </Card.Root>
{/if}
