<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import {
    Radar,
    RotateCcw,
    Signal,
    Zap,
    ZoomIn,
    ZoomOut,
  } from "lucide-svelte";
  import type { RobotState, SensorData } from "$lib/types";
  import { fly } from "svelte/transition";

  export type LidarPoint = {
    x: number;
    y: number;
    quality: number;
  };

  export type LidarPointCloud = {
    timestamp: number;
    points: LidarPoint[];
  };

  type Point = {
    x: number;
    y: number;
  };

  type RenderedPoint = Point & {
    distance: number;
    quality: number;
    radius: number;
    color: string;
  };

  const VIEWBOX_WIDTH = 360;
  const VIEWBOX_HEIGHT = 300;
  const RADAR_CENTER = { x: 180, y: 142 };
  const MAX_RANGE_M = 12;
  const MIN_VISIBLE_RANGE_M = 1.5;
  const RADAR_RADIUS = 118;
  const QUALITY_MAX = 63;
  const ROBOT_WIDTH = 0.2;
  const ROBOT_HEIGHT = 0.3;
  const ZOOM_STEP = 1.25;

  let {
    sensorData,
    latestLidarScan = null,
    robotState = null,
    lastSensorUpdate,
    class: className = "",
  }: {
    sensorData: SensorData | null;
    latestLidarScan?: LidarPointCloud | null;
    robotState?: RobotState | null;
    lastSensorUpdate: number;
    class?: string;
  } = $props();

  let lidarZoom = $state(1);
  let visibleRangeM = $derived(MAX_RANGE_M / lidarZoom);
  let pixelsPerMeter = $derived(RADAR_RADIUS / visibleRangeM);
  let robotWidthPx = $derived(ROBOT_WIDTH * pixelsPerMeter);
  let robotHeightPx = $derived(ROBOT_HEIGHT * pixelsPerMeter);
  let robotHalfWidthPx = $derived(robotWidthPx / 2);
  let robotHalfHeightPx = $derived(robotHeightPx / 2);
  let rangeRings = $derived(
    [0.25, 0.5, 0.75, 1].map((amount) => visibleRangeM * amount),
  );

  function setLidarZoom(nextZoom: number) {
    lidarZoom = clamp(nextZoom, 1, MAX_RANGE_M / MIN_VISIBLE_RANGE_M);
  }

  function zoomLidarIn() {
    setLidarZoom(lidarZoom * ZOOM_STEP);
  }

  function zoomLidarOut() {
    setLidarZoom(lidarZoom / ZOOM_STEP);
  }

  function resetLidarZoom() {
    lidarZoom = 1;
  }

  function handleLidarWheel(event: WheelEvent) {
    event.preventDefault();
    if (event.deltaY < 0) {
      zoomLidarIn();
    } else {
      zoomLidarOut();
    }
  }

  function clamp(value: number, min: number, max: number) {
    return Math.min(max, Math.max(min, value));
  }

  function formatMeters(value: number | null) {
    return value === null ? "--" : `${value.toFixed(2)} m`;
  }

  function formatCm(value: number | null | undefined) {
    return typeof value === "number" && Number.isFinite(value)
      ? `${Math.round(value)} cm`
      : "--";
  }

  function pointQuality(point: LidarPoint) {
    return clamp(
      Number.isFinite(point.quality) ? point.quality : 0,
      0,
      QUALITY_MAX,
    );
  }

  function pointToRobotFrame(point: LidarPoint): Point {
    if (!robotState) {
      return { x: point.x, y: point.y };
    }

    const dx = point.x - robotState.x;
    const dy = point.y - robotState.y;
    const cos = Math.cos(robotState.yaw);
    const sin = Math.sin(robotState.yaw);

    return {
      x: dx * cos + dy * sin,
      y: -dx * sin + dy * cos,
    };
  }

  function pointColor(distance: number, quality: number) {
    const qualityAmount = quality / QUALITY_MAX;
    const rangeAmount = clamp(distance / MAX_RANGE_M, 0, 1);
    const alpha = 0.35 + qualityAmount * 0.55;

    if (rangeAmount < 0.18) return `rgba(220, 38, 38, ${alpha})`;
    if (rangeAmount < 0.34) return `rgba(234, 88, 12, ${alpha})`;
    if (rangeAmount < 0.58) return `rgba(202, 138, 4, ${alpha})`;
    return `rgba(14, 165, 233, ${alpha})`;
  }

  function buildRenderedPoints(scan: LidarPointCloud | null): RenderedPoint[] {
    if (!scan?.points) return [];

    return scan.points.flatMap((point) => {
      if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) return [];

      const local = pointToRobotFrame(point);
      const distance = Math.hypot(local.x, local.y);
      if (distance <= 0 || distance > visibleRangeM) return [];

      const quality = pointQuality(point);
      return [
        {
          x: RADAR_CENTER.x - local.y * pixelsPerMeter,
          y: RADAR_CENTER.y - local.x * pixelsPerMeter,
          distance,
          quality,
          radius: 1.5 + (quality / QUALITY_MAX) * 2.3,
          color: pointColor(distance, quality),
        },
      ];
    });
  }

  function closestDistance(points: RenderedPoint[]) {
    if (points.length === 0) return null;
    return points.reduce(
      (closest, point) => (point.distance < closest ? point.distance : closest),
      points[0].distance,
    );
  }

  let renderedPoints = $derived(buildRenderedPoints(latestLidarScan));
  let closestPointDistance = $derived(closestDistance(renderedPoints));
  let live = $derived(lastSensorUpdate !== 0 && renderedPoints.length > 0);
  let scanAgeMs = $derived(
    lastSensorUpdate === 0 ? null : Math.max(0, Date.now() - lastSensorUpdate),
  );
</script>

<Card.Root
  class="flex h-full min-h-0 w-full flex-col overflow-hidden border border-gray-100 bg-white p-1! shadow-sm {className}"
>
  <Card.Content class="min-h-0 flex-1 p-2 sm:p-3">
    <div
      class="relative h-full min-h-[240px] w-full overflow-hidden p-0"
      in:fly={{ y: 8, duration: 220 }}
      onwheel={handleLidarWheel}
    >
      <svg
        viewBox="0 0 {VIEWBOX_WIDTH} {VIEWBOX_HEIGHT}"
        class="absolute inset-0 h-full w-full"
        role="img"
        aria-label="Lidar point cloud radar"
      >
        <rect width={VIEWBOX_WIDTH} height={VIEWBOX_HEIGHT} fill="#ffffff" />

        <g>
          {#each rangeRings as range}
            {@const radius = range * pixelsPerMeter}
            <circle
              cx={RADAR_CENTER.x}
              cy={RADAR_CENTER.y}
              r={radius}
              fill="none"
              stroke="rgba(100, 116, 139, 0.18)"
              stroke-width="1"
            />
            <text
              x={RADAR_CENTER.x + radius - 5}
              y={RADAR_CENTER.y - 4}
              text-anchor="end"
              class="fill-slate-400 text-[9px] font-medium"
            >
              {range < 10 ? range.toFixed(1) : range.toFixed(0)}m
            </text>
          {/each}

          {#each [0, 30, 60, 90, 120, 150] as angle}
            {@const radians = (angle * Math.PI) / 180}
            {@const dx = Math.cos(radians) * RADAR_RADIUS}
            {@const dy = Math.sin(radians) * RADAR_RADIUS}
            <line
              x1={RADAR_CENTER.x - dx}
              y1={RADAR_CENTER.y - dy}
              x2={RADAR_CENTER.x + dx}
              y2={RADAR_CENTER.y + dy}
              stroke="rgba(100, 116, 139, 0.12)"
              stroke-width="1"
              stroke-dasharray="4 6"
            />
          {/each}
        </g>

        <g opacity={live ? 1 : 0.55}>
          {#each renderedPoints as point}
            <circle
              cx={point.x}
              cy={point.y}
              r={point.radius}
              fill={point.color}
            />
          {/each}
        </g>

        <g>
          <path
            d={`M ${RADAR_CENTER.x} ${RADAR_CENTER.y - robotHalfHeightPx - 6} L ${RADAR_CENTER.x - robotHalfWidthPx} ${RADAR_CENTER.y - robotHalfHeightPx} Q ${RADAR_CENTER.x - robotHalfWidthPx - Math.max(3, robotWidthPx * 0.3)} ${RADAR_CENTER.y + robotHalfHeightPx} ${RADAR_CENTER.x} ${RADAR_CENTER.y + robotHalfHeightPx + Math.max(2, robotHeightPx * 0.12)} Q ${RADAR_CENTER.x + robotHalfWidthPx + Math.max(3, robotWidthPx * 0.3)} ${RADAR_CENTER.y + robotHalfHeightPx} ${RADAR_CENTER.x + robotHalfWidthPx} ${RADAR_CENTER.y - robotHalfHeightPx} Z`}
            fill="#ffffff"
            stroke="#334155"
            stroke-width="2"
          />
          <line
            x1={RADAR_CENTER.x}
            y1={RADAR_CENTER.y + robotHalfHeightPx}
            x2={RADAR_CENTER.x}
            y2={RADAR_CENTER.y - robotHalfHeightPx - 5}
            stroke="#94a3b8"
            stroke-width="1.5"
            stroke-linecap="round"
          />
          <circle
            cx={RADAR_CENTER.x}
            cy={RADAR_CENTER.y}
            r={Math.max(2, Math.min(robotWidthPx, robotHeightPx) * 0.1)}
            fill="#0f172a"
          />
        </g>
      </svg>

      <div class="pointer-events-none absolute left-3 top-3">
        <div
          class="rounded-md border border-slate-200 bg-white/90 px-2 py-1 shadow-sm"
        >
          <div
            class="text-[10px] font-semibold uppercase tracking-wide text-slate-500"
          >
            Lidar
          </div>
          <div
            class="flex items-center gap-1.5 text-xs font-semibold text-slate-800"
          >
            <span
              class="h-2 w-2 rounded-full {live
                ? 'bg-sky-500'
                : 'bg-slate-300'}"
            ></span>
            {renderedPoints.length} pts
            <span class="text-slate-400">/</span>
            {formatMeters(closestPointDistance)}
          </div>
        </div>
      </div>

      <div class="pointer-events-none absolute right-3 top-3">
        <div
          class="rounded-md border border-slate-200 bg-white/90 px-2 py-1 text-right shadow-sm"
        >
          <div
            class="text-[10px] font-semibold uppercase tracking-wide text-slate-500"
          >
            Range
          </div>
          <div class="text-xs font-semibold text-slate-800">
            {visibleRangeM.toFixed(1)} m max
          </div>
        </div>
      </div>

      <div
        class="absolute right-3 top-16 flex overflow-hidden rounded-md border border-slate-200 bg-white/95 shadow-sm"
      >
        <button
          type="button"
          class="flex h-7 w-7 items-center justify-center border-r border-slate-200 text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          onclick={zoomLidarOut}
          disabled={lidarZoom <= 1}
          title="Zoom out"
        >
          <ZoomOut class="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          class="flex h-7 w-7 items-center justify-center border-r border-slate-200 text-slate-700 transition-colors hover:bg-slate-100"
          onclick={resetLidarZoom}
          title="Reset zoom"
        >
          <RotateCcw class="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          class="flex h-7 w-7 items-center justify-center text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          onclick={zoomLidarIn}
          disabled={visibleRangeM <= MIN_VISIBLE_RANGE_M}
          title="Zoom in"
        >
          <ZoomIn class="h-3.5 w-3.5" />
        </button>
      </div>

      <div
        class="pointer-events-none absolute bottom-3 left-1/2 grid w-[calc(100%-1.5rem)] -translate-x-1/2 grid-cols-2 gap-1.5 sm:grid-cols-4"
      >
        <div
          class="flex min-w-0 items-center justify-center gap-1 rounded-md border border-slate-200 bg-white/95 px-2 py-1.5 text-[11px] font-semibold text-slate-800 shadow-sm"
        >
          <Radar class="h-3.5 w-3.5 text-sky-600" />
          {live ? "Live" : "No scan"}
        </div>
        <div
          class="flex min-w-0 items-center justify-center gap-1 rounded-md border border-slate-200 bg-white/95 px-2 py-1.5 text-[11px] font-semibold text-slate-800 shadow-sm"
        >
          <Signal class="h-3.5 w-3.5 text-slate-500" />
          {scanAgeMs === null ? "--" : `${scanAgeMs} ms`}
        </div>
        <div
          class="flex min-w-0 items-center justify-center gap-1 rounded-md border border-slate-200 bg-white/95 px-2 py-1.5 text-[11px] font-semibold text-slate-800 shadow-sm"
        >
          <Zap class="h-3.5 w-3.5 text-amber-600" />
          F {formatCm(sensorData?.tof.distance_front)}
        </div>
        <div
          class="flex min-w-0 flex-col items-center justify-center rounded-md border border-slate-200 bg-white/95 px-2 py-1 text-[10px] font-semibold leading-tight text-slate-800 shadow-sm"
        >
          <span>L {formatCm(sensorData?.ultrasonic.distance_left)}</span>
          <span>R {formatCm(sensorData?.ultrasonic.distance_right)}</span>
        </div>
      </div>
    </div>
  </Card.Content>
</Card.Root>
