<script lang="ts">
  import { Activity } from "lucide-svelte";
  import type { RobotState } from "$lib/types";

  let {
    robotState,
    lastSensorUpdateTime,
    class: className = "",
  }: {
    robotState: RobotState | null;
    lastSensorUpdateTime: number;
    class?: string;
  } = $props();

  type MotionView = "linear" | "wheel";
  type VelocitySample = {
    timestamp: number;
    vLin: number;
    omega: number;
    vLeft: number;
    vRight: number;
  };
  type ChartSeries = {
    key: string;
    title: string;
    value: number;
    unit: string;
    min: number;
    max: number;
    color: string;
    fill: string;
    data: { timestamp: number; value: number }[];
  };

  const HISTORY_WINDOW_MS = 20000;
  const MAX_HISTORY_SAMPLES = 240;
  const GRAPH_WIDTH = 900;
  const GRAPH_HEIGHT = 260;
  const PADDING = { top: 12, right: 16, bottom: 22, left: 48 };
  const VELOCITY_MIN = -0.4;
  const VELOCITY_MAX = 0.4;
  const OMEGA_MIN = -Math.PI;
  const OMEGA_MAX = Math.PI;

  let motionView = $state<MotionView>("linear");
  let history = $state<VelocitySample[]>([]);
  let lastRecordedSensorUpdate = $state(0);

  const plotWidth = GRAPH_WIDTH - PADDING.left - PADDING.right;
  const plotHeight = GRAPH_HEIGHT - PADDING.top - PADDING.bottom;

  let vLin = $derived(robotState ? robotState.linear_velocity : 0);
  let omega = $derived(robotState ? robotState.angular_velocity : 0);
  let vLeft = $derived(robotState ? robotState.v_left : 0);
  let vRight = $derived(robotState ? robotState.v_right : 0);

  let latestValues = $derived([
    {
      label: "v_lin",
      value: vLin,
      unit: "m/s",
      color: "#2563eb",
    },
    {
      label: "omega",
      value: omega,
      unit: "rad/s",
      color: "#dc2626",
    },
    {
      label: "v_left",
      value: vLeft,
      unit: "m/s",
      color: "#16a34a",
    },
    {
      label: "v_right",
      value: vRight,
      unit: "m/s",
      color: "#7c3aed",
    },
  ]);

  $effect(() => {
    if (
      !robotState ||
      lastSensorUpdateTime === 0 ||
      lastSensorUpdateTime === lastRecordedSensorUpdate
    ) {
      return;
    }

    lastRecordedSensorUpdate = lastSensorUpdateTime;

    const nextOmega = robotState.angular_velocity;
    const nextLin = robotState.linear_velocity;
    const nextVLeft = robotState.v_left;
    const nextVRight = robotState.v_right;
    const sample: VelocitySample = {
      timestamp: lastSensorUpdateTime,
      vLin: nextLin,
      omega: nextOmega,
      vLeft: nextVLeft,
      vRight: nextVRight,
    };

    history = [...history, sample]
      .filter((entry) => sample.timestamp - entry.timestamp <= HISTORY_WINDOW_MS)
      .slice(-MAX_HISTORY_SAMPLES);
  });

  let visibleSeries = $derived.by<ChartSeries[]>(() => {
    if (motionView === "wheel") {
      return [
        {
          key: "v-left",
          title: "Left wheel",
          value: vLeft,
          unit: "m/s",
          min: VELOCITY_MIN,
          max: VELOCITY_MAX,
          color: "#16a34a",
          fill: "rgba(22, 163, 74, 0.08)",
          data: history.map((entry) => ({
            timestamp: entry.timestamp,
            value: entry.vLeft,
          })),
        },
        {
          key: "v-right",
          title: "Right wheel",
          value: vRight,
          unit: "m/s",
          min: VELOCITY_MIN,
          max: VELOCITY_MAX,
          color: "#7c3aed",
          fill: "rgba(124, 58, 237, 0.08)",
          data: history.map((entry) => ({
            timestamp: entry.timestamp,
            value: entry.vRight,
          })),
        },
      ];
    }

    return [
      {
        key: "v-lin",
        title: "Linear velocity",
        value: vLin,
        unit: "m/s",
        min: VELOCITY_MIN,
        max: VELOCITY_MAX,
        color: "#2563eb",
        fill: "rgba(37, 99, 235, 0.08)",
        data: history.map((entry) => ({
          timestamp: entry.timestamp,
          value: entry.vLin,
        })),
      },
      {
        key: "omega",
        title: "Angular velocity",
        value: omega,
        unit: "rad/s",
        min: OMEGA_MIN,
        max: OMEGA_MAX,
        color: "#dc2626",
        fill: "rgba(220, 38, 38, 0.08)",
        data: history.map((entry) => ({
          timestamp: entry.timestamp,
          value: entry.omega,
        })),
      },
    ];
  });

  function clamp(value: number, min: number, max: number) {
    return Math.min(Math.max(value, min), max);
  }

  function formatValue(value: number, unit: string) {
    const prefix = value > 0 ? "+" : "";
    const digits = unit === "rad/s" ? 3 : 3;
    return `${prefix}${value.toFixed(digits)} ${unit}`;
  }

  function formatTick(value: number, unit: string) {
    if (unit === "rad/s") return value.toFixed(1);
    return value.toFixed(2);
  }

  function formatTime(timestamp: number) {
    return new Date(timestamp).toLocaleTimeString([], {
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function xForTime(timestamp: number, points: { timestamp: number }[]) {
    if (points.length <= 1) return PADDING.left + plotWidth / 2;

    const start = points[0].timestamp;
    const end = points[points.length - 1].timestamp;
    const span = Math.max(end - start, 1);
    return PADDING.left + ((timestamp - start) / span) * plotWidth;
  }

  function yForValue(value: number, min: number, max: number) {
    const ratio = (max - clamp(value, min, max)) / (max - min);
    return PADDING.top + ratio * plotHeight;
  }

  function buildPath(series: ChartSeries) {
    return series.data
      .map((point, index) => {
        const x = xForTime(point.timestamp, series.data);
        const y = yForValue(point.value, series.min, series.max);
        return `${index === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");
  }

  function buildAreaPath(series: ChartSeries) {
    if (series.data.length === 0) return "";

    const zeroY = yForValue(0, series.min, series.max);
    const first = series.data[0];
    const last = series.data[series.data.length - 1];

    return [
      `M ${xForTime(first.timestamp, series.data)} ${zeroY}`,
      buildPath(series),
      `L ${xForTime(last.timestamp, series.data)} ${zeroY}`,
      "Z",
    ].join(" ");
  }

  function chartDots(series: ChartSeries) {
    const stride = Math.max(Math.floor(series.data.length / 28), 1);
    return series.data
      .filter((_, index) => index % stride === 0 || index === series.data.length - 1)
      .map((point) => ({
        timestamp: point.timestamp,
        x: xForTime(point.timestamp, series.data),
        y: yForValue(point.value, series.min, series.max),
      }));
  }
</script>

<div
  class="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg border border-gray-100 bg-white shadow-sm {className}"
>
  <div
    class="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-gray-100 px-3 py-2"
  >
    <div class="flex min-w-0 items-center gap-2">
      <Activity class="h-4 w-4 text-gray-950" />
      <h3 class="text-sm font-semibold leading-none text-gray-950">
        Velocity Debug
      </h3>
      <span class="text-[11px] font-mono text-gray-400">
        {history.length} samples
      </span>
    </div>

    <div class="inline-flex rounded-md border border-gray-200 bg-gray-50 p-0.5">
      {#each ["linear", "wheel"] as option}
        <button
          type="button"
          onclick={() => (motionView = option as MotionView)}
          class="rounded px-3 py-1 text-xs font-semibold transition {motionView ===
          option
            ? 'bg-white text-gray-950 shadow-sm'
            : 'text-gray-500 hover:text-gray-800'}"
          aria-pressed={motionView === option}
        >
          {option === "linear" ? "Linear" : "Wheel"}
        </button>
      {/each}
    </div>
  </div>

  <div class="grid shrink-0 grid-cols-2 gap-px border-b border-gray-100 bg-gray-100 sm:grid-cols-4">
    {#each latestValues as item}
      <div class="bg-white px-3 py-1.5">
        <div class="flex items-center gap-1.5 text-[11px] font-medium text-gray-500">
          <span class="h-2 w-2 rounded-full" style:background={item.color}></span>
          {item.label}
        </div>
        <div class="mt-0.5 font-mono text-xs font-semibold text-gray-900">
          {formatValue(item.value, item.unit)}
        </div>
      </div>
    {/each}
  </div>

  <div class="grid min-h-0 flex-1 gap-2 p-2 md:grid-cols-2">
    {#each visibleSeries as series (series.key)}
      <section class="flex min-h-0 flex-col overflow-hidden rounded-lg border border-gray-100 bg-white">
        <div class="flex shrink-0 items-center justify-between gap-2 border-b border-gray-100 px-2.5 py-1.5">
          <div class="flex items-center gap-2">
            <span class="h-2.5 w-2.5 rounded-full" style:background={series.color}></span>
            <div class="text-xs font-semibold text-gray-900">{series.title}</div>
          </div>
          <div class="font-mono text-xs font-semibold text-gray-600">
            {formatValue(series.value, series.unit)}
          </div>
        </div>

        <div class="min-h-0 flex-1">
          <svg
            class="block h-full min-h-[180px] w-full"
            viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`}
            preserveAspectRatio="none"
            role="img"
            aria-label={series.title}
          >
            <rect
              x={PADDING.left}
              y={PADDING.top}
              width={plotWidth}
              height={plotHeight}
              rx="8"
              class="fill-white stroke-gray-200"
            />

            {#each [series.max, (series.max + series.min) / 2, series.min] as tick}
              {@const y = yForValue(tick, series.min, series.max)}
              <line
                x1={PADDING.left}
                x2={GRAPH_WIDTH - PADDING.right}
                y1={y}
                y2={y}
                class="stroke-gray-100"
              />
              <text
                x={PADDING.left - 8}
                y={y + 4}
                text-anchor="end"
                class="fill-gray-500 text-[11px]"
              >
                {formatTick(tick, series.unit)}
              </text>
            {/each}

            {#each [0, 0.25, 0.5, 0.75, 1] as ratio}
              {@const x = PADDING.left + ratio * plotWidth}
              <line
                x1={x}
                x2={x}
                y1={PADDING.top}
                y2={GRAPH_HEIGHT - PADDING.bottom}
                class="stroke-gray-100"
              />
            {/each}

            <line
              x1={PADDING.left}
              x2={GRAPH_WIDTH - PADDING.right}
              y1={yForValue(0, series.min, series.max)}
              y2={yForValue(0, series.min, series.max)}
              class="stroke-gray-300 [stroke-dasharray:4,4]"
            />

            {#if series.data.length > 0}
              <path d={buildAreaPath(series)} fill={series.fill} />
              <path
                d={buildPath(series)}
                fill="none"
                stroke={series.color}
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
              />

              {#each chartDots(series) as dot (dot.timestamp)}
                <circle
                  cx={dot.x}
                  cy={dot.y}
                  r="3"
                  fill="white"
                  stroke={series.color}
                  stroke-width="2"
                />
              {/each}

              <text
                x={GRAPH_WIDTH - PADDING.right}
                y={GRAPH_HEIGHT - 6}
                text-anchor="end"
                class="fill-gray-500 text-[11px]"
              >
                {formatTime(series.data[0].timestamp)} - {formatTime(
                  series.data[series.data.length - 1].timestamp,
                )}
              </text>
            {:else}
              <text
                x={GRAPH_WIDTH / 2}
                y={GRAPH_HEIGHT / 2}
                text-anchor="middle"
                class="fill-gray-400 text-[13px] font-medium"
              >
                Waiting for velocity samples
              </text>
            {/if}
          </svg>
        </div>
      </section>
    {/each}
  </div>
</div>
