<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { Skeleton } from "$lib/components/ui/skeleton";
  import * as Chart from "$lib/components/ui/chart/index.js";
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

  const leftData = $derived(
    distanceHistory.map((entry) => ({
      date: new Date(entry.timestamp),
      value: Math.min(entry.distance_left, MAX_DISTANCE),
    })),
  );

  const rightData = $derived(
    distanceHistory.map((entry) => ({
      date: new Date(entry.timestamp),
      value: Math.min(entry.distance_right, MAX_DISTANCE),
    })),
  );

  const frontData = $derived(
    distanceHistory.map((entry) => ({
      date: new Date(entry.timestamp),
      value: Math.min(entry.distance_front, MAX_DISTANCE),
    })),
  );

  const chartSections = $derived([
    {
      key: "left",
      title: "Left Ultrasonic",
      data: leftData,
      gradientId: "gradient-left",
    },
    {
      key: "right",
      title: "Right Ultrasonic",
      data: rightData,
      gradientId: "gradient-right",
    },
    {
      key: "front",
      title: "Front ToF",
      data: frontData,
      gradientId: "gradient-front",
    },
  ]);
</script>

{#if distanceHistory.length === 0}
  <Skeleton class="w-full h-[400px] rounded-sm" />
{:else}
  <Card.Root class="w-full h-full">
    <Card.Header>
      <Card.Title>Distance Sensors</Card.Title>
      <Card.Description>
        Showing left ultrasonic, right ultrasonic, and front ToF
      </Card.Description>
    </Card.Header>
    <Card.Content class="space-y-4">
      {#each chartSections as section (section.key)}
        <div class="space-y-2">
          <div class="text-sm font-medium text-muted-foreground">
            {section.title}
          </div>
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
                      [thresholdOffset, "var(--chart-2)"],
                      [thresholdOffset, "var(--chart-1)"],
                    ]}
                    units="userSpaceOnUse"
                    vertical
                  >
                    {#snippet children({ gradient })}
                      <Area
                        y0={() => OBSTACLE_THRESHOLD}
                        line={{ stroke: gradient }}
                        fill={gradient}
                        fillOpacity={0.4}
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
        </div>
      {/each}
    </Card.Content>
  </Card.Root>
{/if}
