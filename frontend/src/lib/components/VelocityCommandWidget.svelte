<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { io as socket } from "$lib/api/socket";
  import {
    Activity,
    CircleStop,
    Magnet,
    MousePointer2,
    Play,
    Plus,
    RotateCcw,
  } from "lucide-svelte";
  import type { RobotState } from "$lib/types";

  let {
    class: className = "",
    robotState = null,
    lastSensorUpdateTime = 0,
    velocityProfileT = null,
  }: {
    class?: string;
    robotState?: RobotState | null;
    lastSensorUpdateTime?: number;
    velocityProfileT?: number | null;
  } = $props();

  type CommandMode = "wheel" | "twist" | "PWM";
  type CurveKey = "a" | "b";
  type ProfilePoint = {
    id: number;
    t: number;
    a: number;
    b: number;
  };
  type MeasuredSample = {
    timestamp: number;
    t: number;
    a: number;
    b: number;
  };

  type CurveMeta = {
    key: CurveKey;
    label: string;
    payloadKey: string;
    unit: string;
    min: number;
    max: number;
    color: string;
    fill: string;
  };

  const GRAPH_HEIGHT = 420;
  const PADDING = { top: 10, right: 52, bottom: 20, left: 52 };
  const TICK_COUNT = 5;
  const MIN_POINT_SPACING = 0.02;
  const DEFAULT_POINTS: ProfilePoint[] = [
    { id: 1, t: 0, a: 0, b: 0 },
    { id: 2, t: 0.25, a: 0.18, b: 0.18 },
    { id: 3, t: 0.55, a: 0.24, b: -0.1 },
    { id: 4, t: 0.82, a: -0.12, b: 0.14 },
    { id: 5, t: 1, a: 0, b: 0 },
  ];

  const MODE_META: Record<CommandMode, CurveMeta[]> = {
    wheel: [
      {
        key: "a",
        label: "Left",
        payloadKey: "v_left",
        unit: "m/s",
        min: -0.4,
        max: 0.4,
        color: "#2563eb",
        fill: "rgba(37, 99, 235, 0.08)",
      },
      {
        key: "b",
        label: "Right",
        payloadKey: "v_right",
        unit: "m/s",
        min: -0.4,
        max: 0.4,
        color: "#16a34a",
        fill: "rgba(22, 163, 74, 0.08)",
      },
    ],
    twist: [
      {
        key: "a",
        label: "Linear",
        payloadKey: "v_lin",
        unit: "m/s",
        min: -0.4,
        max: 0.4,
        color: "#2563eb",
        fill: "rgba(37, 99, 235, 0.08)",
      },
      {
        key: "b",
        label: "Angular",
        payloadKey: "omega",
        unit: "rad/s",
        min: -Math.PI,
        max: Math.PI,
        color: "#dc2626",
        fill: "rgba(220, 38, 38, 0.08)",
      },
    ],
    PWM: [
      {
        key: "a",
        label: "Left PWM",
        payloadKey: "pwm_left",
        unit: "",
        min: -1,
        max: 1,
        color: "#2563eb",
        fill: "rgba(37, 99, 235, 0.08)",
      },
      {
        key: "b",
        label: "Right PWM",
        payloadKey: "pwm_right",
        unit: "",
        min: -1,
        max: 1,
        color: "#16a34a",
        fill: "rgba(22, 163, 74, 0.08)",
      },
    ],
  };

  let mode = $state<CommandMode>("wheel");
  let durationSeconds = $state(4);
  let points = $state<ProfilePoint[]>(structuredClone(DEFAULT_POINTS));
  let dragTarget = $state<{ id: number; key: CurveKey } | null>(null);
  let hoverTarget = $state<{ id: number; key: CurveKey } | null>(null);
  let graphFrame = $state<HTMLDivElement | null>(null);
  let svgElement = $state<SVGSVGElement | null>(null);
  let graphWidth = $state(1280);
  let snapEnabled = $state(true);
  let isRunning = $state(false);
  let progress = $state(0);
  let startedAt = $state(0);
  let measuredSamples = $state<MeasuredSample[]>([]);
  let lastRecordedSensorUpdate = $state(0);
  let progressFrame = 0;

  const plotHeight = GRAPH_HEIGHT - PADDING.top - PADDING.bottom;

  let curves = $derived(MODE_META[mode]);
  let plotWidth = $derived(graphWidth - PADDING.left - PADDING.right);
  let sortedPoints = $derived(
    [...points].sort((left, right) => left.t - right.t),
  );

  let displayPoints = $derived(
    sortedPoints.map((point) => ({
      ...point,
      a: clamp(point.a, curves[0].min, curves[0].max),
      b: clamp(point.b, curves[1].min, curves[1].max),
    })),
  );

  let chartCurves = $derived(
    curves.map((curve) => {
      const svgPoints = displayPoints.map((point) => ({
        id: point.id,
        t: point.t,
        value: point[curve.key],
        x: xForTime(point.t),
        y: yForValue(point[curve.key], curve),
      }));

      return {
        ...curve,
        svgPoints,
        path: linePath(svgPoints),
        fillPath: areaPath(svgPoints, curve),
      };
    }),
  );

  let measuredCurves = $derived(
    curves.map((curve) => {
      const svgPoints = measuredSamples.map((sample) => ({
        timestamp: sample.timestamp,
        t: sample.t,
        value: sample[curve.key],
        x: xForTime(sample.t),
        y: yForValue(sample[curve.key], curve),
      }));

      return {
        ...curve,
        svgPoints,
        path: linePath(svgPoints),
      };
    }),
  );

  let canShowMeasured = $derived(mode !== "PWM");

  let yTicks = $derived(
    Array.from({ length: TICK_COUNT }, (_, index) => {
      const ratio = index / (TICK_COUNT - 1);
      return {
        ratio,
        y: PADDING.top + ratio * plotHeight,
        leftValue: curves[0].max - ratio * (curves[0].max - curves[0].min),
        rightValue: curves[1].max - ratio * (curves[1].max - curves[1].min),
      };
    }),
  );

  let xTicks = $derived(
    Array.from({ length: 5 }, (_, index) => {
      const t = index / 4;
      return {
        t,
        x: xForTime(t),
        label: `${(t * durationSeconds).toFixed(1)}s`,
      };
    }),
  );

  let previewValues = $derived(sampleProfile(progress));

  let snapGuides = $derived(
    curves.flatMap((curve) =>
      snapValuesForCurve(curve).map((value) => ({
        key: `${curve.key}-${value}`,
        value,
        y: yForValue(value, curve),
        color: curve.color,
      })),
    ),
  );

  function clamp(value: number, min: number, max: number) {
    return Math.min(Math.max(value, min), max);
  }

  function setMode(nextMode: CommandMode) {
    mode = nextMode;
    const nextCurves = MODE_META[nextMode];
    points = points.map((point) => ({
      ...point,
      a: clamp(point.a, nextCurves[0].min, nextCurves[0].max),
      b: clamp(point.b, nextCurves[1].min, nextCurves[1].max),
    }));
  }

  function formatValue(value: number, curve: CurveMeta) {
    const prefix = value > 0 ? "+" : "";
    const digits = curve.unit === "rad/s" ? 2 : 3;
    return `${prefix}${value.toFixed(digits)}${curve.unit ? ` ${curve.unit}` : ""}`;
  }

  function measuredValuesFromRobotState(state: RobotState) {
    if (mode === "wheel") {
      const vLin = state.linear_velocity;
      const omega = state.angular_velocity;
      return {
        a: vLin - (omega * 0.255) / 2,
        b: vLin + (omega * 0.255) / 2,
      };
    }

    if (mode === "twist") {
      return {
        a: state.linear_velocity,
        b: state.angular_velocity,
      };
    }

    return null;
  }

  function xForTime(t: number) {
    return PADDING.left + clamp(t, 0, 1) * plotWidth;
  }

  function yForValue(value: number, curve: CurveMeta) {
    const ratio =
      (curve.max - clamp(value, curve.min, curve.max)) /
      (curve.max - curve.min);
    return PADDING.top + ratio * plotHeight;
  }

  function valueForY(y: number, curve: CurveMeta) {
    const ratio = clamp((y - PADDING.top) / plotHeight, 0, 1);
    return curve.max - ratio * (curve.max - curve.min);
  }

  function snapValuesForCurve(curve: CurveMeta) {
    const halfMax = curve.max / 2;
    const halfMin = curve.min / 2;
    return [curve.min, halfMin, 0, halfMax, curve.max];
  }

  function snapValue(value: number, curve: CurveMeta) {
    if (!snapEnabled) return value;

    const threshold = (curve.max - curve.min) * 0.035;
    const snapTarget = snapValuesForCurve(curve).find(
      (target) => Math.abs(value - target) <= threshold,
    );

    return snapTarget ?? value;
  }

  function linePath(svgPoints: { x: number; y: number }[]) {
    return svgPoints
      .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
      .join(" ");
  }

  function areaPath(svgPoints: { x: number; y: number }[], curve: CurveMeta) {
    if (svgPoints.length === 0) return "";
    const zeroY = yForValue(0, curve);
    const first = svgPoints[0];
    const last = svgPoints.at(-1)!;
    return `M ${first.x} ${zeroY} ${linePath(svgPoints)} L ${last.x} ${zeroY} Z`;
  }

  function getPointerPosition(event: PointerEvent, element: SVGSVGElement) {
    const rect = element.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * graphWidth,
      y: ((event.clientY - rect.top) / rect.height) * GRAPH_HEIGHT,
    };
  }

  function pointBounds(id: number) {
    const ordered = sortedPoints;
    const index = ordered.findIndex((point) => point.id === id);
    return {
      min: index <= 0 ? 0 : ordered[index - 1].t + 0.025,
      max: index >= ordered.length - 1 ? 1 : ordered[index + 1].t - 0.025,
      locked: index === 0 || index === ordered.length - 1,
    };
  }

  function startDrag(event: PointerEvent, id: number, key: CurveKey) {
    event.preventDefault();
    event.stopPropagation();
    dragTarget = { id, key };
    hoverTarget = { id, key };
    window.addEventListener("pointermove", dragPoint);
    window.addEventListener("pointerup", stopDrag, { once: true });
  }

  function dragPoint(event: PointerEvent) {
    if (!dragTarget || !svgElement) return;
    const target = dragTarget;

    const curve = curves.find((entry) => entry.key === target.key);
    if (!curve) return;

    const pointer = getPointerPosition(event, svgElement);
    const bounds = pointBounds(target.id);
    const nextT = bounds.locked
      ? (points.find((point) => point.id === target.id)?.t ?? 0)
      : clamp((pointer.x - PADDING.left) / plotWidth, bounds.min, bounds.max);
    const nextValue = snapValue(valueForY(pointer.y, curve), curve);

    points = points.map((point) =>
      point.id === target.id
        ? { ...point, t: nextT, [target.key]: nextValue }
        : point,
    );
  }

  function stopDrag() {
    window.removeEventListener("pointermove", dragPoint);
    dragTarget = null;
  }

  function nextPointId() {
    return Math.max(...points.map((point) => point.id), 0) + 1;
  }

  function insertPointAt(t: number) {
    const clampedT = clamp(t, MIN_POINT_SPACING, 1 - MIN_POINT_SPACING);
    const values = sampleProfile(clampedT);

    points = [
      ...points,
      {
        id: nextPointId(),
        t: clampedT,
        a: snapValue(values.a, curves[0]),
        b: snapValue(values.b, curves[1]),
      },
    ].sort((left, right) => left.t - right.t);
  }

  function addPoint() {
    const ordered = sortedPoints;
    let bestT = 0.5;
    let bestGap = 0;

    for (let index = 1; index < ordered.length; index += 1) {
      const previous = ordered[index - 1];
      const next = ordered[index];
      const gap = next.t - previous.t;

      if (gap > bestGap) {
        bestGap = gap;
        bestT = previous.t + gap / 2;
      }
    }

    insertPointAt(bestT);
  }

  function addPointFromGraph(event: MouseEvent) {
    if (!svgElement || dragTarget) return;

    const pointer = getPointerPosition(event as PointerEvent, svgElement);
    const t = clamp((pointer.x - PADDING.left) / plotWidth, 0, 1);

    if (t <= MIN_POINT_SPACING || t >= 1 - MIN_POINT_SPACING) return;
    insertPointAt(t);
  }

  function resetProfile() {
    stopRun();
    points = structuredClone(DEFAULT_POINTS);
    progress = 0;
  }

  function sampleProfile(t: number) {
    const clampedT = clamp(t, 0, 1);
    const ordered = displayPoints;

    if (clampedT <= ordered[0].t) {
      return { a: ordered[0].a, b: ordered[0].b };
    }

    for (let index = 1; index < ordered.length; index += 1) {
      const previous = ordered[index - 1];
      const next = ordered[index];
      if (clampedT <= next.t) {
        const span = Math.max(next.t - previous.t, 1e-6);
        const amount = (clampedT - previous.t) / span;
        return {
          a: previous.a + (next.a - previous.a) * amount,
          b: previous.b + (next.b - previous.b) * amount,
        };
      }
    }

    const last = ordered.at(-1)!;
    return { a: last.a, b: last.b };
  }

  function commandPayload() {
    return {
      mode,
      profile: displayPoints.map((point) => ({
        t: point.t * durationSeconds,
        v1: clamp(point.a, curves[0].min, curves[0].max),
        v2: clamp(point.b, curves[1].min, curves[1].max),
      })),
    };
  }

  function neutralPayload() {
    return {
      mode,
      profile: [{ t: 0, v1: 0, v2: 0 }],
    };
  }

  function updateProgress() {
    if (!isRunning) return;

    const nextProgress = clamp(
      (performance.now() - startedAt) / (durationSeconds * 1000),
      0,
      1,
    );

    progress = nextProgress;

    if (nextProgress >= 1) {
      stopRun(true);
      return;
    }

    progressFrame = requestAnimationFrame(updateProgress);
  }

  function startRun() {
    stopRun();
    durationSeconds = clamp(durationSeconds, 0.5, 60);
    startedAt = performance.now();
    progress = 0;
    measuredSamples = [];
    lastRecordedSensorUpdate = 0;
    isRunning = true;
    socket.emit("vel_command", commandPayload());
    progressFrame = requestAnimationFrame(updateProgress);
  }

  function stopRun(finished = false) {
    if (progressFrame) {
      cancelAnimationFrame(progressFrame);
      progressFrame = 0;
    }
    isRunning = false;
    progress = finished ? 1 : progress;
  }

  $effect(() => {
    if (!graphFrame) return;

    function updateGraphSize() {
      if (!graphFrame) return;

      const rect = graphFrame.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;

      const nextWidth = Math.round(
        clamp((rect.width / rect.height) * GRAPH_HEIGHT, 760, 1800),
      );

      if (Math.abs(nextWidth - graphWidth) > 2) {
        graphWidth = nextWidth;
      }
    }

    updateGraphSize();
    const observer = new ResizeObserver(updateGraphSize);
    observer.observe(graphFrame);

    return () => observer.disconnect();
  });

  $effect(() => {
    if (
      !isRunning ||
      !robotState ||
      !canShowMeasured ||
      velocityProfileT === null ||
      lastSensorUpdateTime === 0 ||
      lastSensorUpdateTime === lastRecordedSensorUpdate
    ) {
      return;
    }

    const values = measuredValuesFromRobotState(robotState);
    if (!values) return;

    lastRecordedSensorUpdate = lastSensorUpdateTime;
    const t =
      durationSeconds > 0 ? clamp(velocityProfileT / durationSeconds, 0, 1) : 0;

    measuredSamples = [
      ...measuredSamples,
      {
        timestamp: lastSensorUpdateTime,
        t,
        a: clamp(values.a, curves[0].min, curves[0].max),
        b: clamp(values.b, curves[1].min, curves[1].max),
      },
    ].slice(-260);
  });

  $effect(() => {
    return () => {
      stopDrag();
      stopRun();
    };
  });
</script>

<Card.Root
  class="flex h-full gap-4 min-h-0 w-full flex-col overflow-hidden border border-gray-100 bg-white shadow-sm p-0 {className}"
>
  <div class="h-1 w-full bg-gray-100">
    <div
      class="h-full bg-gray-900 transition-[width] duration-75"
      style:width={`${progress * 100}%`}
    ></div>
  </div>

  <Card.Header class="shrink-0 border-b pb-2! border-gray-100 px-2.5 py-0 pb-0">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="min-w-0">
        <Card.Title class="flex items-center gap-3 text-lg leading-none">
          <Activity class="h-5 w-5" />
          Velocity Profile
        </Card.Title>
      </div>

      <div class="flex items-center gap-2">
        {#each curves as curve}
          <div
            class="flex items-center gap-1.5 text-xs font-medium text-gray-600"
          >
            <span class="h-2 w-2 rounded-full" style:background={curve.color}
            ></span>
            {curve.label}
          </div>
        {/each}
      </div>
    </div>
  </Card.Header>

  <Card.Content class="flex min-h-0 flex-1 flex-col gap-1 p-1.5 pt-0">
    <div
      bind:this={graphFrame}
      class="flex min-h-0 flex-1 items-stretch overflow-hidden"
    >
      <svg
        bind:this={svgElement}
        class="block h-full w-full touch-none select-none"
        viewBox={`0 0 ${graphWidth} ${GRAPH_HEIGHT}`}
        preserveAspectRatio="none"
        role="img"
        aria-label="Editable velocity profile graph"
        ondblclick={addPointFromGraph}
      >
        <rect
          x={PADDING.left}
          y={PADDING.top}
          width={plotWidth}
          height={plotHeight}
          rx="10"
          class="fill-white stroke-gray-200"
        />

        {#each yTicks as tick}
          <line
            x1={PADDING.left}
            x2={graphWidth - PADDING.right}
            y1={tick.y}
            y2={tick.y}
            class="stroke-gray-100"
          />
          <text
            x={PADDING.left - 10}
            y={tick.y + 4}
            text-anchor="end"
            class="fill-gray-500 text-[11px]"
          >
            {tick.leftValue.toFixed(curves[0].unit === "rad/s" ? 1 : 2)}
          </text>
          <text
            x={graphWidth - PADDING.right + 10}
            y={tick.y + 4}
            class="fill-gray-400 text-[11px]"
          >
            {tick.rightValue.toFixed(curves[1].unit === "rad/s" ? 1 : 2)}
          </text>
        {/each}

        {#each xTicks as tick}
          <line
            x1={tick.x}
            x2={tick.x}
            y1={PADDING.top}
            y2={GRAPH_HEIGHT - PADDING.bottom}
            class="stroke-gray-100"
          />
          <text
            x={tick.x}
            y={GRAPH_HEIGHT - 16}
            text-anchor="middle"
            class="fill-gray-500 text-[11px]"
          >
            {tick.label}
          </text>
        {/each}

        <line
          x1={PADDING.left}
          x2={graphWidth - PADDING.right}
          y1={yForValue(0, curves[0])}
          y2={yForValue(0, curves[0])}
          class="stroke-gray-300 [stroke-dasharray:4,4]"
        />

        {#if snapEnabled}
          {#each snapGuides as guide (guide.key)}
            <line
              x1={PADDING.left}
              x2={graphWidth - PADDING.right}
              y1={guide.y}
              y2={guide.y}
              stroke={guide.color}
              stroke-opacity="0.12"
              stroke-width="1"
              class="[stroke-dasharray:2,6]"
            />
          {/each}
        {/if}

        {#each chartCurves as curve}
          <path d={curve.fillPath} fill={curve.fill} />
          <path
            d={curve.path}
            fill="none"
            stroke={curve.color}
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        {/each}

        {#if canShowMeasured && measuredSamples.length > 1}
          {#each measuredCurves as curve}
            <path
              d={curve.path}
              fill="none"
              stroke={curve.color}
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-opacity="0.85"
              class="[stroke-dasharray:7,5]"
            />
            {@const lastPoint = curve.svgPoints.at(-1)}
            {#if lastPoint}
              <circle
                cx={lastPoint.x}
                cy={lastPoint.y}
                r="4"
                fill={curve.color}
                stroke="white"
                stroke-width="2"
              />
            {/if}
          {/each}
        {/if}

        {#if isRunning}
          <line
            x1={xForTime(progress)}
            x2={xForTime(progress)}
            y1={PADDING.top}
            y2={GRAPH_HEIGHT - PADDING.bottom}
            class="stroke-gray-900"
            stroke-width="2"
          />
        {/if}

        {#each chartCurves as curve}
          {#each curve.svgPoints as point}
            <g
              class="cursor-grab active:cursor-grabbing"
              onpointerdown={(event) => startDrag(event, point.id, curve.key)}
              onpointerenter={() =>
                (hoverTarget = { id: point.id, key: curve.key })}
              onpointerleave={() => (hoverTarget = null)}
            >
              <circle
                cx={point.x}
                cy={point.y}
                r={hoverTarget?.id === point.id &&
                hoverTarget?.key === curve.key
                  ? 8
                  : 6}
                fill="white"
                stroke={curve.color}
                stroke-width="3"
              />
              <circle cx={point.x} cy={point.y} r="2.4" fill={curve.color} />
            </g>
          {/each}
        {/each}

        {#if hoverTarget}
          {@const curve = curves.find(
            (entry) => entry.key === hoverTarget?.key,
          )!}
          {@const point = displayPoints.find(
            (entry) => entry.id === hoverTarget?.id,
          )!}
          {@const x = xForTime(point.t)}
          {@const y = yForValue(point[curve.key], curve)}
          <g pointer-events="none">
            <rect
              x={clamp(x + 14, PADDING.left, graphWidth - 182)}
              y={clamp(y - 42, PADDING.top + 4, GRAPH_HEIGHT - 88)}
              width="168"
              height="48"
              rx="8"
              class="fill-white stroke-gray-200 drop-shadow-sm"
            />
            <text
              x={clamp(x + 28, PADDING.left + 14, graphWidth - 168)}
              y={clamp(y - 20, PADDING.top + 26, GRAPH_HEIGHT - 66)}
              class="fill-gray-900 text-[12px] font-semibold"
            >
              {curve.label}
            </text>
            <text
              x={clamp(x + 28, PADDING.left + 14, graphWidth - 168)}
              y={clamp(y - 4, PADDING.top + 42, GRAPH_HEIGHT - 50)}
              class="fill-gray-500 text-[11px]"
            >
              {(point.t * durationSeconds).toFixed(2)}s · {formatValue(
                point[curve.key],
                curve,
              )}
            </text>
          </g>
        {/if}
      </svg>
    </div>

    <div
      class="flex shrink-0 flex-wrap items-center justify-between gap-1.5 border-t border-gray-100 pt-1"
    >
      <div class="flex flex-wrap items-center gap-2">
        <div
          class="inline-flex rounded-md border border-gray-200 bg-gray-50 p-0.5"
        >
          {#each ["wheel", "twist", "PWM"] as option}
            <button
              class="rounded px-3 py-1.5 text-xs font-semibold transition {mode ===
              option
                ? 'bg-white text-gray-950 shadow-sm'
                : 'text-gray-500 hover:text-gray-800'}"
              type="button"
              onclick={() => setMode(option as CommandMode)}
            >
              {option}
            </button>
          {/each}
        </div>

        <label
          class="flex items-center gap-2 text-xs font-medium text-gray-600"
        >
          Duration
          <input
            class="h-7 w-18 rounded-md border border-gray-200 bg-white px-2 text-sm text-gray-900 outline-none focus:border-gray-400"
            type="number"
            min="0.5"
            max="60"
            step="0.5"
            bind:value={durationSeconds}
          />
          s
        </label>

        <button
          class="inline-flex h-7 items-center gap-2 rounded-md border border-gray-200 bg-white px-2.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
          type="button"
          onclick={addPoint}
        >
          <Plus class="h-3.5 w-3.5" />
          Add point
        </button>

        <button
          class="inline-flex h-7 items-center gap-2 rounded-md border px-2.5 text-xs font-semibold transition {snapEnabled
            ? 'border-gray-300 bg-gray-900 text-white'
            : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'}"
          type="button"
          onclick={() => (snapEnabled = !snapEnabled)}
        >
          <Magnet class="h-3.5 w-3.5" />
          Snap
        </button>
      </div>

      <div class="flex items-center gap-2">
        {#if canShowMeasured}
          <div
            class="hidden items-center gap-2 pr-2 text-xs text-gray-500 lg:flex"
          >
            <span class="h-px w-5 bg-gray-900"></span>
            profile
            <span class="h-px w-5 border-t border-dashed border-gray-500"
            ></span>
            measured
          </div>
        {/if}

        <div
          class="hidden items-center gap-2 pr-2 text-xs text-gray-500 sm:flex"
        >
          <MousePointer2 class="h-3.5 w-3.5" />
          {formatValue(previewValues.a, curves[0])} / {formatValue(
            previewValues.b,
            curves[1],
          )}
        </div>

        <button
          class="inline-flex h-7 items-center gap-2 rounded-md border border-gray-200 bg-white px-2.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
          type="button"
          onclick={resetProfile}
        >
          <RotateCcw class="h-3.5 w-3.5" />
          Reset
        </button>

        {#if isRunning}
          <button
            class="inline-flex h-7 items-center gap-2 rounded-md bg-gray-900 px-2.5 text-xs font-semibold text-white hover:bg-gray-800"
            type="button"
            onclick={() => stopRun()}
          >
            <CircleStop class="h-3.5 w-3.5" />
            Stop
          </button>
        {:else}
          <button
            class="inline-flex h-7 items-center gap-2 rounded-md bg-gray-900 px-2.5 text-xs font-semibold text-white hover:bg-gray-800"
            type="button"
            onclick={startRun}
          >
            <Play class="h-3.5 w-3.5" />
            Start
          </button>
        {/if}
      </div>
    </div>
  </Card.Content>
</Card.Root>
