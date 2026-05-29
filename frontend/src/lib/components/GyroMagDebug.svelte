<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { Compass, Gauge, Move3d, Radio, Route } from "lucide-svelte";
  import type { SensorData } from "$lib/types";

  let {
    sensorData,
    lastSensorUpdateTime,
    class: className = "",
  }: {
    sensorData: SensorData | null;
    lastSensorUpdateTime: number;
    class?: string;
  } = $props();

  const STALE_MS = 5000;
  let connected = $derived(
    lastSensorUpdateTime > 0 && Date.now() - lastSensorUpdateTime < STALE_MS,
  );

  function fmt(value: number | undefined, digits = 2): string {
    if (value === undefined || Number.isNaN(value)) return "--";
    return value.toFixed(digits);
  }

  function fmtInt(value: number | undefined): string {
    if (value === undefined || Number.isNaN(value)) return "--";
    return Math.round(value).toLocaleString();
  }

  function fmtDistance(value: number | undefined): string {
    if (value === undefined || Number.isNaN(value) || value <= 0) return "--";
    return `${value.toFixed(1)} cm`;
  }

  const axisGroups = $derived([
    {
      title: "Accelerometer",
      unit: "m/s²",
      icon: Move3d,
      accent: "#2563eb",
      values: [
        { axis: "X", value: sensorData?.imu.acceleration_x },
        { axis: "Y", value: sensorData?.imu.acceleration_y },
        { axis: "Z", value: sensorData?.imu.acceleration_z },
      ],
    },
    {
      title: "Gyroscope",
      unit: "°/s",
      icon: Gauge,
      accent: "#16a34a",
      values: [
        { axis: "X", value: sensorData?.imu.gyroscope_x },
        { axis: "Y", value: sensorData?.imu.gyroscope_y },
        { axis: "Z", value: sensorData?.imu.gyroscope_z },
      ],
    },
    {
      title: "Magnetometer",
      unit: "µT",
      icon: Compass,
      accent: "#dc2626",
      values: [
        { axis: "X", value: sensorData?.magnetometer.x },
        { axis: "Y", value: sensorData?.magnetometer.y },
        { axis: "Z", value: sensorData?.magnetometer.z },
      ],
    },
  ]);

  const telemetryGroups = $derived([
    {
      title: "Encoders",
      icon: Route,
      accent: "#7c3aed",
      values: [
        { label: "Left", value: fmtInt(sensorData?.left_encoder) },
        { label: "Right", value: fmtInt(sensorData?.right_encoder) },
      ],
    },
    {
      title: "Range Sensors",
      icon: Radio,
      accent: "#0891b2",
      values: [
        {
          label: "Left US",
          value: fmtDistance(sensorData?.ultrasonic.distance_left),
        },
        {
          label: "Right US",
          value: fmtDistance(sensorData?.ultrasonic.distance_right),
        },
        {
          label: "Front ToF",
          value: fmtDistance(sensorData?.tof.distance_front),
        },
        {
          label: "Nearest",
          value: fmtDistance(sensorData?.ultrasonic.distance),
        },
      ],
    },
  ]);
</script>

<Card.Root class="h-full w-full min-h-0 gap-0 py-1 overflow-hidden {className}">
  <Card.Header class="shrink-0 border-b border-gray-100 px-3 pt-2 pb-1!">
    <div class="flex items-center justify-between gap-2">
      <Card.Title class="flex items-center gap-2 text-base leading-none">
        <Move3d class="h-4.5 w-4.5" />
        IMU Debug
      </Card.Title>
      <span
        class="rounded-full border px-2.5 py-0.5 text-xs font-semibold leading-none {connected
          ? 'bg-green-50 text-green-700 border-green-200'
          : 'bg-gray-50 text-gray-500 border-gray-200'}"
      >
        {connected ? "live" : "stale"}
      </span>
    </div>
  </Card.Header>

  <Card.Content
    class="grid min-h-0 flex-1 grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-2 p-2.5"
  >
    <div class="grid min-h-0 gap-2 xl:grid-cols-3">
      {#each axisGroups as group}
        {@const Icon = group.icon}
        <section
          class="flex min-h-0 flex-col overflow-hidden rounded-lg border border-gray-100 bg-white"
        >
          <div
            class="flex items-center justify-between border-b border-gray-100 px-3 py-2"
          >
            <div
              class="flex items-center gap-2 text-sm font-semibold text-gray-800"
            >
              <Icon class="h-4 w-4" style={`color: ${group.accent}`} />
              {group.title}
            </div>
            <div class="font-mono text-xs font-semibold text-gray-400">
              {group.unit}
            </div>
          </div>

          <div class="grid min-h-0 flex-1 grid-cols-3 divide-x divide-gray-100">
            {#each group.values as item}
              <div class="flex flex-col justify-center px-3 py-3">
                <div class="text-xs font-semibold text-gray-400">
                  {item.axis}
                </div>
                <div
                  class="mt-1.5 font-mono text-lg font-semibold leading-none text-gray-900"
                >
                  {fmt(item.value)}
                </div>
              </div>
            {/each}
          </div>
        </section>
      {/each}
    </div>

    <div class="grid grid-cols-2 gap-2 lg:grid-cols-5">
      <div class="rounded-lg border border-gray-100 px-3 py-2.5">
        <div class="text-xs font-semibold text-gray-400">Heading</div>
        <div
          class="mt-1 font-mono text-lg font-semibold leading-none text-gray-900"
        >
          {fmt(sensorData?.magnetometer.heading, 1)}°
        </div>
      </div>

      <div class="rounded-lg border border-gray-100 px-3 py-2.5">
        <div class="text-xs font-semibold text-gray-400">Temperature</div>
        <div
          class="mt-1 font-mono text-lg font-semibold leading-none text-gray-900"
        >
          {fmt(sensorData?.imu.temperature, 1)}°C
        </div>
      </div>

      <div class="rounded-lg border border-gray-100 px-3 py-2.5">
        <div class="text-xs font-semibold text-gray-400">Packet</div>
        <div
          class="mt-1 font-mono text-lg font-semibold leading-none text-gray-900"
        >
          {sensorData?.packet_num ?? "--"}
        </div>
      </div>

      <div class="rounded-lg border border-gray-100 px-3 py-2.5">
        <div class="text-xs font-semibold text-gray-400">Mag Fresh</div>
        <div
          class="mt-1 font-mono text-lg font-semibold leading-none {sensorData
            ?.magnetometer.new
            ? 'text-green-700'
            : 'text-gray-900'}"
        >
          {sensorData?.magnetometer.new ? "true" : "false"}
        </div>
      </div>

      <div class="rounded-lg border border-gray-100 px-3 py-2.5">
        <div class="text-xs font-semibold text-gray-400">Motors</div>
        <div
          class="mt-1 font-mono text-lg font-semibold leading-none {sensorData?.motors_enabled
            ? 'text-green-700'
            : 'text-red-700'}"
        >
          {sensorData?.motors_enabled ? "enabled" : "disabled"}
        </div>
      </div>
    </div>

    <div class="grid min-h-0 gap-2 lg:grid-cols-2">
      {#each telemetryGroups as group}
        {@const Icon = group.icon}
        <section
          class="flex min-h-0 flex-col overflow-hidden rounded-lg border border-gray-100 bg-white"
        >
          <div
            class="flex items-center justify-between border-b border-gray-100 px-3 py-2"
          >
            <div
              class="flex items-center gap-2 text-sm font-semibold text-gray-800"
            >
              <Icon class="h-4 w-4" style={`color: ${group.accent}`} />
              {group.title}
            </div>
          </div>
          <div
            class="grid min-h-0 flex-1 grid-cols-2 divide-x divide-y divide-gray-100"
          >
            {#each group.values as item}
              <div
                class="flex min-h-[45px] flex-col justify-center px-2 py-0.5"
              >
                <div class="text-xs font-semibold text-gray-400">
                  {item.label}
                </div>
                <div
                  class="mt-1 font-mono text-md font-semibold leading-none text-gray-900"
                >
                  {item.value}
                </div>
              </div>
            {/each}
          </div>
        </section>
      {/each}
    </div>

    <div class="truncate font-mono text-xs text-gray-400">
      timestamp: {sensorData?.timestamp ?? "--"}
    </div>
  </Card.Content>
</Card.Root>
