<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { Gauge, Compass } from "lucide-svelte";
  import type { SensorData } from "$lib/types";

  let {
    sensorData,
    lastSensorUpdateTime,
  }: {
    sensorData: SensorData | null;
    lastSensorUpdateTime: number;
  } = $props();

  const STALE_MS = 5000;
  let connected = $derived(
    lastSensorUpdateTime > 0 && Date.now() - lastSensorUpdateTime < STALE_MS,
  );

  function fmt(value: number | undefined, digits = 2): string {
    if (value === undefined || Number.isNaN(value)) return "--";
    return value.toFixed(digits);
  }
</script>

<Card.Root class="w-full">
  <Card.Header class="pb-2">
    <div class="flex items-center justify-between gap-2">
      <Card.Title class="flex items-center gap-2 text-sm">
        <Gauge class="h-4 w-4" />
        Gyro + Mag Debug
      </Card.Title>
      <span
        class="text-[11px] px-2 py-0.5 rounded-md border {connected
          ? 'bg-green-50 text-green-700 border-green-200'
          : 'bg-gray-50 text-gray-500 border-gray-200'}"
      >
        {connected ? "live" : "stale"}
      </span>
    </div>
  </Card.Header>

  <Card.Content class="space-y-3">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div class="rounded-md border border-gray-200 p-3">
        <div class="text-xs font-semibold text-gray-600 mb-2">
          Gyroscope (°/s)
        </div>
        <div class="grid grid-cols-3 gap-2 text-xs font-mono">
          <div class="rounded bg-gray-50 p-2">
            <div class="text-gray-500">X</div>
            <div class="text-sm text-gray-900">
              {fmt(sensorData?.imu.gyroscope_x)}
            </div>
          </div>
          <div class="rounded bg-gray-50 p-2">
            <div class="text-gray-500">Y</div>
            <div class="text-sm text-gray-900">
              {fmt(sensorData?.imu.gyroscope_y)}
            </div>
          </div>
          <div class="rounded bg-gray-50 p-2">
            <div class="text-gray-500">Z</div>
            <div class="text-sm text-gray-900">
              {fmt(sensorData?.imu.gyroscope_z)}
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-md border border-gray-200 p-3">
        <div
          class="text-xs font-semibold text-gray-600 mb-2 flex items-center gap-1"
        >
          <Compass class="h-3.5 w-3.5" /> Magnetometer (µT)
        </div>
        <div class="grid grid-cols-3 gap-2 text-xs font-mono mb-2">
          <div class="rounded bg-gray-50 p-2">
            <div class="text-gray-500">X</div>
            <div class="text-sm text-gray-900">
              {fmt(sensorData?.magnetometer.x)}
            </div>
          </div>
          <div class="rounded bg-gray-50 p-2">
            <div class="text-gray-500">Y</div>
            <div class="text-sm text-gray-900">
              {fmt(sensorData?.magnetometer.y)}
            </div>
          </div>
          <div class="rounded bg-gray-50 p-2">
            <div class="text-gray-500">Z</div>
            <div class="text-sm text-gray-900">
              {fmt(sensorData?.magnetometer.z)}
            </div>
          </div>
        </div>

        <div
          class="flex items-center justify-between text-xs font-mono rounded bg-gray-50 p-2"
        >
          <span class="text-gray-600">Heading</span>
          <span class="text-sm text-gray-900"
            >{fmt(sensorData?.magnetometer.heading, 1)}°</span
          >
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
      <div class="rounded border border-gray-200 p-2">
        <div class="text-gray-500">Packet</div>
        <div class="text-gray-900">{sensorData?.packet_num ?? "--"}</div>
      </div>
      <div class="rounded border border-gray-200 p-2">
        <div class="text-gray-500">Timestamp</div>
        <div class="text-gray-900">{sensorData?.timestamp ?? "--"}</div>
      </div>
      <div class="rounded border border-gray-200 p-2">
        <div class="text-gray-500">Mag Fresh</div>
        <div
          class={sensorData?.magnetometer.new
            ? "text-green-700"
            : "text-gray-900"}
        >
          {sensorData?.magnetometer.new ? "true" : "false"}
        </div>
      </div>
      <div class="rounded border border-gray-200 p-2">
        <div class="text-gray-500">Motors</div>
        <div
          class={sensorData?.motors_enabled ? "text-green-700" : "text-red-700"}
        >
          {sensorData?.motors_enabled ? "enabled" : "disabled"}
        </div>
      </div>
    </div>
  </Card.Content>
</Card.Root>
