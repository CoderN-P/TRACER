<script lang="ts">
    import * as Card from "$lib/components/ui/card";
    import { Skeleton } from "$lib/components/ui/skeleton";
    import * as Chart from "$lib/components/ui/chart/index.js";
    import { scaleUtc } from "d3-scale";
    import { curveNatural } from "d3-shape";
    import { AreaChart, Area, LinearGradient, Highlight } from "layerchart";
    import TrendingUpIcon from "@lucide/svelte/icons/trending-up";
    import type {DistanceEntry} from "$lib/types";

    let { distanceHistory }: { distanceHistory: DistanceEntry[] } = $props();

    const chartConfig = {
        desktop: { label: "Distance", color: "var(--chart-1)" },
    } satisfies Chart.ChartConfig;
</script>
{#if distanceHistory.length === 0 }
    <Skeleton class="w-full h-[400px] rounded-sm" />
{:else}
    <Card.Root class="w-full h-full ">
        <Card.Header>
            <Card.Title>Ultrasonic Sensor</Card.Title>
            <Card.Description>Showing distance to walls/obstacles</Card.Description>
        </Card.Header>
        <Card.Content class="pl-12">
            <Chart.Container config={chartConfig}>
                <AreaChart
                        data={distanceHistory.map((entry) => ({
                            date: new Date(entry.timestamp),
                            value: Math.min(entry.distance, 50),
                        }))}
                        x="date"
                        y="value"
                        annotations={[
                          {
                            type: "line",
                            y: 20,
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
                                format: (v: number) => v === 50 ? "50+ cm" : `${v} cm`,
                            },
                        }}
                >
                    {#snippet marks({ context, series })}
                        {@const thresholdValue = 20}
                        {@const thresholdOffset = context.yScale(thresholdValue)/ (context.height + context.padding.bottom)}
                        {#each series as s, i (s.key)}
                            <LinearGradient
                                id="gradient"
                                stops ={[
                                    [thresholdOffset, "var(--chart-2)"],
                                    [thresholdOffset, "var(--chart-1)"],
                                ]}
                                units="userSpaceOnUse"
                                vertical
                            >
                            {#snippet children( { gradient } )}
                                
                                <Area 
                                    y0={(d) => thresholdValue}
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
                        {@const value = context.tooltip?.data && context.y(context.tooltip?.data)}
                        <Highlight
                                lines
                                points={{ fill: value <= 20 ? "var(--chart-1)" : "var(--chart-2)" }}
                        />
                    {/snippet}
                    {#snippet tooltip()}
                        <Chart.Tooltip
                                indicator="dot"
                                labelFormatter={(v: Date) => {
                                return v.toLocaleTimeString();
                            }}
                        />
                    {/snippet}
                </AreaChart>
            </Chart.Container>
        </Card.Content>
    </Card.Root>
{/if}