<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { Car } from "lucide-svelte";
  import type { SensorData } from "$lib/types";
  import { fly } from "svelte/transition";

  type BeamSeverity = "critical" | "warning" | "caution" | "safe";
  type BeamKey = "left" | "front" | "right";

  type Point = {
    x: number;
    y: number;
  };

  type Rgb = [number, number, number];

  type SensorBeam = {
    key: BeamKey;
    label: string;
    shortLabel: string;
    angle: number;
    spread: number;
    origin: Point;
    fallbackDistance: number;
    readDistance: (data: SensorData) => number;
  };

  type BeamReading = SensorBeam & {
    distance: number;
    radius: number;
    path: string;
    endpoint: Point;
    labelPoint: Point;
    severity: BeamSeverity;
    color: string;
    softColor: string;
  };

  type RadarState = {
    beams: BeamReading[];
    closest: BeamReading;
    live: boolean;
  };

  const VIEWBOX_WIDTH = 360;
  const VIEWBOX_HEIGHT = 260;
  const MAX_DISTANCE_CM = 100;
  const MAX_RADIUS = 174;
  const CRITICAL_DISTANCE = 10;
  const WARNING_DISTANCE = 20;
  const CAUTION_DISTANCE = 35;

  const DISTANCE_COLOR_STOPS: { distance: number; color: Rgb }[] = [
    { distance: 0, color: [220, 38, 38] },
    { distance: CRITICAL_DISTANCE, color: [220, 38, 38] },
    { distance: WARNING_DISTANCE, color: [234, 88, 12] },
    { distance: CAUTION_DISTANCE, color: [202, 138, 4] },
    { distance: 60, color: [101, 163, 13] },
    { distance: MAX_DISTANCE_CM, color: [22, 163, 74] },
  ];

  const ROBOT = {
    cx: 180,
    cy: 214,
    width: 58,
    noseY: 172,
    leftSensor: { x: 148, y: 186 },
    frontSensor: { x: 180, y: 172 },
    rightSensor: { x: 212, y: 186 },
  };

  const SENSOR_BEAMS: SensorBeam[] = [
    {
      key: "left",
      label: "Left ultrasonic",
      shortLabel: "L US",
      angle: -45,
      spread: 30,
      origin: ROBOT.leftSensor,
      fallbackDistance: 20,
      readDistance: (data) => data.ultrasonic.distance_left,
    },
    {
      key: "front",
      label: "Front ToF",
      shortLabel: "ToF",
      angle: 0,
      spread: 16,
      origin: ROBOT.frontSensor,
      fallbackDistance: 18,
      readDistance: (data) => data.tof.distance_front,
    },
    {
      key: "right",
      label: "Right ultrasonic",
      shortLabel: "R US",
      angle: 45,
      spread: 30,
      origin: ROBOT.rightSensor,
      fallbackDistance: 32,
      readDistance: (data) => data.ultrasonic.distance_right,
    },
  ];

  let {
    sensorData,
    lastSensorUpdate,
    class: className = "",
  }: {
    sensorData: SensorData | null;
    lastSensorUpdate: number;
    class?: string;
  } = $props();

  function clamp(value: number, min: number, max: number) {
    return Math.min(max, Math.max(min, value));
  }

  function formatDistance(distance: number) {
    return `${Math.round(distance)} cm`;
  }

  function getSeverity(distance: number): BeamSeverity {
    if (distance < CRITICAL_DISTANCE) return "critical";
    if (distance < WARNING_DISTANCE) return "warning";
    if (distance < CAUTION_DISTANCE) return "caution";
    return "safe";
  }

  function mixColor(start: Rgb, end: Rgb, amount: number): Rgb {
    return start.map((channel, index) =>
      Math.round(channel + (end[index] - channel) * amount),
    ) as Rgb;
  }

  function getDistanceColor(distance: number, alpha = 1) {
    const value = clamp(distance, 0, MAX_DISTANCE_CM);
    const upperStop =
      DISTANCE_COLOR_STOPS.find((stop) => value <= stop.distance) ??
      DISTANCE_COLOR_STOPS[DISTANCE_COLOR_STOPS.length - 1];
    const upperIndex = DISTANCE_COLOR_STOPS.indexOf(upperStop);
    const lowerStop = DISTANCE_COLOR_STOPS[Math.max(0, upperIndex - 1)];
    const span = Math.max(1, upperStop.distance - lowerStop.distance);
    const amount = clamp((value - lowerStop.distance) / span, 0, 1);
    const [red, green, blue] = mixColor(
      lowerStop.color,
      upperStop.color,
      amount,
    );

    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
  }

  function polarToCartesian(
    origin: Point,
    angle: number,
    radius: number,
  ): Point {
    const radians = ((angle - 90) * Math.PI) / 180;

    return {
      x: origin.x + radius * Math.cos(radians),
      y: origin.y + radius * Math.sin(radians),
    };
  }

  function beamPath(
    origin: Point,
    angle: number,
    spread: number,
    radius: number,
  ) {
    const visibleRadius = Math.max(radius, 3);
    const start = polarToCartesian(origin, angle - spread / 2, visibleRadius);
    const end = polarToCartesian(origin, angle + spread / 2, visibleRadius);

    return [
      `M ${origin.x} ${origin.y}`,
      `L ${start.x} ${start.y}`,
      `A ${visibleRadius} ${visibleRadius} 0 0 1 ${end.x} ${end.y}`,
      "Z",
    ].join(" ");
  }

  function buildRadarState(data: SensorData | null): RadarState {
    const beams = SENSOR_BEAMS.map((beam) => {
      const rawDistance = data
        ? beam.readDistance(data)
        : beam.fallbackDistance;
      const distance = Math.max(
        0,
        Number.isFinite(rawDistance) ? rawDistance : 0,
      );
      const radius =
        (clamp(distance, 0, MAX_DISTANCE_CM) / MAX_DISTANCE_CM) * MAX_RADIUS;
      const severity = getSeverity(distance);
      const endpoint = polarToCartesian(beam.origin, beam.angle, radius);
      const rawLabelPoint = polarToCartesian(
        beam.origin,
        beam.angle,
        clamp(radius + 18, 34, MAX_RADIUS + 4),
      );
      const labelPoint = {
        x: clamp(rawLabelPoint.x, 28, VIEWBOX_WIDTH - 28),
        y: clamp(rawLabelPoint.y, 20, VIEWBOX_HEIGHT - 18),
      };
      const color = getDistanceColor(distance);
      const softColor = getDistanceColor(distance, 0.22);

      return {
        ...beam,
        distance,
        radius,
        path: beamPath(beam.origin, beam.angle, beam.spread, radius),
        endpoint,
        labelPoint,
        severity,
        color,
        softColor,
      } satisfies BeamReading;
    });

    const closest = beams.reduce((current, candidate) =>
      candidate.distance < current.distance ? candidate : current,
    );

    return {
      beams,
      closest,
      live: data !== null && lastSensorUpdate !== 0,
    };
  }

  let radarState = $derived.by(() => buildRadarState(sensorData));
  let beamOpacity = $derived.by(() => (radarState.live ? 1 : 0.78));
</script>

<Card.Root
  class="w-full h-full min-h-0 overflow-hidden border p-1! border-gray-100 bg-white shadow-sm flex flex-col {className}"
>
  <Card.Content class="min-h-0 flex-1 p-2 sm:p-3">
    <div
      class="relative h-full min-h-[240px] w-full overflow-hidden p-0"
      in:fly={{ y: 8, duration: 220 }}
    >
      <svg
        viewBox="0 0 {VIEWBOX_WIDTH} {VIEWBOX_HEIGHT}"
        class="absolute inset-0 h-full w-full"
        role="img"
        aria-label="Radar beam visualization of ultrasonic and time-of-flight distances"
      >
        <rect width={VIEWBOX_WIDTH} height={VIEWBOX_HEIGHT} fill="#ffffff" />

        <g>
          {#each [25, 50, 75, 100] as distance}
            {@const radius = (distance / MAX_DISTANCE_CM) * MAX_RADIUS}
            <path
              d={`M ${ROBOT.cx - radius} ${ROBOT.noseY} A ${radius} ${radius} 0 0 1 ${ROBOT.cx + radius} ${ROBOT.noseY}`}
              fill="none"
              stroke="rgba(100, 116, 139, 0.16)"
              stroke-width="1"
            />
            <text
              x={ROBOT.cx + radius - 18}
              y={ROBOT.noseY - 3}
              text-anchor="end"
              class="fill-slate-400 text-[9px] font-medium"
            >
              {distance}
            </text>
          {/each}

          {#each [-60, -45, -20, 0, 20, 45, 60] as angle}
            {@const endpoint = polarToCartesian(
              ROBOT.frontSensor,
              angle,
              MAX_RADIUS,
            )}
            <line
              x1={ROBOT.frontSensor.x}
              y1={ROBOT.frontSensor.y}
              x2={endpoint.x}
              y2={endpoint.y}
              stroke="rgba(100, 116, 139, 0.13)"
              stroke-width="1"
              stroke-dasharray="4 6"
            />
          {/each}
        </g>

        <g opacity={beamOpacity}>
          {#each radarState.beams as beam (beam.key)}
            <path
              d={beam.path}
              fill={beam.softColor}
              stroke={beam.color}
              stroke-width="2"
              stroke-linejoin="round"
            />
            <line
              x1={beam.origin.x}
              y1={beam.origin.y}
              x2={beam.endpoint.x}
              y2={beam.endpoint.y}
              stroke={beam.color}
              stroke-width="2.5"
              stroke-linecap="round"
            />
            <circle
              cx={beam.endpoint.x}
              cy={beam.endpoint.y}
              r="4.5"
              fill={beam.color}
              stroke="#ffffff"
              stroke-width="2"
            />
          {/each}
        </g>

        <g>
          <path
            d={`M ${ROBOT.cx} ${ROBOT.noseY - 12} L ${ROBOT.cx - ROBOT.width / 2} ${ROBOT.cy - 8} Q ${ROBOT.cx - ROBOT.width / 2} ${ROBOT.cy + 18} ${ROBOT.cx - 16} ${ROBOT.cy + 22} L ${ROBOT.cx + 16} ${ROBOT.cy + 22} Q ${ROBOT.cx + ROBOT.width / 2} ${ROBOT.cy + 18} ${ROBOT.cx + ROBOT.width / 2} ${ROBOT.cy - 8} Z`}
            fill="#ffffff"
            stroke="#334155"
            stroke-width="2"
          />
          <line
            x1={ROBOT.cx}
            y1={ROBOT.cy + 15}
            x2={ROBOT.cx}
            y2={ROBOT.noseY + 6}
            stroke="#cbd5e1"
            stroke-width="1.5"
          />
          <circle
            cx={ROBOT.leftSensor.x}
            cy={ROBOT.leftSensor.y}
            r="4"
            fill="#2563eb"
          />
          <circle
            cx={ROBOT.frontSensor.x}
            cy={ROBOT.frontSensor.y}
            r="4"
            fill="#7c3aed"
          />
          <circle
            cx={ROBOT.rightSensor.x}
            cy={ROBOT.rightSensor.y}
            r="4"
            fill="#2563eb"
          />
        </g>

        {#each radarState.beams as beam (beam.key)}
          <g>
            <text
              x={beam.labelPoint.x}
              y={beam.labelPoint.y - 5}
              text-anchor="middle"
              class="fill-slate-700 text-[10px] font-semibold"
            >
              {beam.shortLabel}
            </text>
            <text
              x={beam.labelPoint.x}
              y={beam.labelPoint.y + 8}
              text-anchor="middle"
              class="fill-slate-500 text-[10px] font-medium"
            >
              {formatDistance(beam.distance)}
            </text>
          </g>
        {/each}
      </svg>

      <div class="pointer-events-none absolute left-3 top-3">
        <div
          class="rounded-md border border-slate-200 bg-white/90 px-2 py-1 shadow-sm"
        >
          <div
            class="text-[10px] font-semibold uppercase tracking-wide text-slate-500"
          >
            Closest
          </div>
          <div
            class="flex items-center gap-1.5 text-xs font-semibold text-slate-800"
          >
            <span
              class="h-2 w-2 rounded-full"
              style:background-color={radarState.closest.color}
            ></span>
            {radarState.closest.label}
            {formatDistance(radarState.closest.distance)}
          </div>
        </div>
      </div>

      <div
        class="pointer-events-none absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-md border border-slate-200 bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-slate-800 shadow-sm"
      >
        <Car class="h-4 w-4" />
        <span>{radarState.live ? "Live radar" : "Preview radar"}</span>
      </div>
    </div>
  </Card.Content>
</Card.Root>
