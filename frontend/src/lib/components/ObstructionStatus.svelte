<script lang="ts">
  import { Skeleton } from "$lib/components/ui/skeleton";
  import * as Card from "$lib/components/ui/card";
  import {
    MountainSnow,
    Construction,
    Check,
    AlertTriangle,
    Car,
    Gauge,
  } from "lucide-svelte";
  import type { SensorData } from "$lib/types";
  import { fade, fly, scale } from "svelte/transition";
  import { quintOut, elasticOut } from "svelte/easing";

  let {
    sensorData,
    lastSensorUpdate,
    class: className = "",
  }: {
    sensorData: SensorData | null;
    lastSensorUpdate: number;
    class?: string;
  } = $props();

  // Distance thresholds
  const CRITICAL_DISTANCE = 5;
  const WARNING_DISTANCE = 10;
  const SAFE_DISTANCE = 20;

  function getObstructionStatus() {
    if (!sensorData) return null;

    let status = {
      obstacle: {
        text: "",
        color: "",
        bgColor: "",
        icon: null,
        distance: sensorData.ultrasonic.distance,
        severity: "safe",
      },
      cliff: {
        text: "",
        color: "",
        bgColor: "",
        icon: null,
        front: sensorData.ir_front,
        back: sensorData.ir_back,
        severity: "safe",
      },
    };

    // Obstacle detection logic with severity levels
    if (sensorData.ultrasonic.distance < CRITICAL_DISTANCE) {
      status.obstacle.text = "Critical! Obstacle very close";
      status.obstacle.color = "text-red-600";
      status.obstacle.bgColor = "bg-red-100";
      status.obstacle.icon = AlertTriangle;
      status.obstacle.severity = "critical";
    } else if (sensorData.ultrasonic.distance < WARNING_DISTANCE) {
      status.obstacle.text = "Warning! Obstacle detected";
      status.obstacle.color = "text-orange-500";
      status.obstacle.bgColor = "bg-orange-100";
      status.obstacle.icon = Construction;
      status.obstacle.severity = "warning";
    } else if (sensorData.ultrasonic.distance < SAFE_DISTANCE) {
      status.obstacle.text = "Caution: Object ahead";
      status.obstacle.color = "text-amber-500";
      status.obstacle.bgColor = "bg-amber-50";
      status.obstacle.icon = Gauge;
      status.obstacle.severity = "caution";
    } else {
      status.obstacle.text = "Path clear";
      status.obstacle.color = "text-green-500";
      status.obstacle.bgColor = "bg-green-50";
      status.obstacle.icon = Check;
      status.obstacle.severity = "safe";
    }

    // Cliff detection logic with severity levels
    if (!sensorData.ir_front && !sensorData.ir_back) {
      status.cliff.text = "Critical! Cliff on both sides";
      status.cliff.color = "text-red-600";
      status.cliff.bgColor = "bg-red-100";
      status.cliff.icon = MountainSnow;
      status.cliff.severity = "critical";
    } else if (!sensorData.ir_front) {
      status.cliff.text = "Warning! Cliff ahead";
      status.cliff.color = "text-orange-500";
      status.cliff.bgColor = "bg-orange-100";
      status.cliff.icon = MountainSnow;
      status.cliff.severity = "warning";
    } else if (!sensorData.ir_back) {
      status.cliff.text = "Warning! Cliff behind";
      status.cliff.color = "text-orange-500";
      status.cliff.bgColor = "bg-orange-100";
      status.cliff.icon = MountainSnow;
      status.cliff.severity = "warning";
    } else {
      status.cliff.text = "No cliff detected";
      status.cliff.color = "text-green-500";
      status.cliff.bgColor = "bg-green-50";
      status.cliff.icon = Check;
      status.cliff.severity = "safe";
    }

    return status;
  }

  // Calculate progress percentage for visual bar based on distance
  function getProgressPercentage() {
    if (!sensorData) return 100;
    const distance = sensorData.ultrasonic.distance;

    if (distance >= SAFE_DISTANCE) return 100;
    if (distance <= 0) return 0;

    return (distance / SAFE_DISTANCE) * 100;
  }

  // Keep track of previous status for animations
  let status = $derived.by(() => {
    return getObstructionStatus();
  });

  let CliffIcon = $derived.by(() => (status ? status.cliff.icon : null));
  let ObstacleIcon = $derived.by(() => (status ? status.obstacle.icon : null));
  let progressPercentage = $derived.by(() => getProgressPercentage());
</script>

{#if lastSensorUpdate === 0}
  <Skeleton class="w-full h-48 rounded-sm" />
{:else}
  <Card.Root class="w-full h-full {className}">
    <Card.Header>
      <Card.Title class="flex items-center gap-2">
        <Car class="w-5 h-5" />
        <span>Obstruction Status</span>
      </Card.Title>
      <Card.Description>Real-time obstacle & cliff detection</Card.Description>
    </Card.Header>
    <Card.Content class="px-3 sm:px-6 pb-4">
      <!-- Progress bar indicating distance to obstacle -->
      <div class="mb-3 bg-gray-100 rounded-full h-2 overflow-hidden">
        <div
          class="h-full rounded-full transition-all duration-500 ease-out"
          class:bg-red-500={status.obstacle.severity === "critical"}
          class:bg-orange-400={status.obstacle.severity === "warning"}
          class:bg-amber-300={status.obstacle.severity === "caution"}
          class:bg-green-500={status.obstacle.severity === "safe"}
          style="width: {progressPercentage}%"
        ></div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <!-- Obstacle Status Card -->
        <div
          class="rounded-lg {status.obstacle
            .bgColor} p-3 border border-gray-100 transition-all duration-300"
          in:fly={{ y: 10, duration: 300, easing: quintOut }}
        >
          <div class="flex items-center gap-2 mb-1">
            <div class="p-1.5 bg-white bg-opacity-60 rounded-full">
              {#key status.obstacle.severity}
                <div
                  in:scale={{ start: 0.8, duration: 300, easing: elasticOut }}
                >
                  <ObstacleIcon
                    class="w-5 h-5 sm:w-6 sm:h-6 {status.obstacle.color}"
                  />
                </div>
              {/key}
            </div>
            <div class="flex-grow">
              <h3
                class="font-medium text-sm sm:text-base {status.obstacle.color}"
              >
                {status.obstacle.text}
              </h3>
              <p class="text-xs sm:text-sm text-gray-600">
                Distance: <span class="font-semibold"
                  >{status.obstacle.distance.toFixed(1)}cm</span
                >
              </p>
            </div>
          </div>
        </div>

        <!-- Cliff Status Card -->
        <div
          class="rounded-lg {status.cliff
            .bgColor} p-3 border border-gray-100 transition-all duration-300"
          in:fly={{ y: 10, duration: 300, delay: 150, easing: quintOut }}
        >
          <div class="flex items-center gap-2 mb-1">
            <div class="p-1.5 bg-white bg-opacity-60 rounded-full">
              {#key status.cliff.severity}
                <div
                  in:scale={{ start: 0.8, duration: 300, easing: elasticOut }}
                >
                  <CliffIcon
                    class="w-5 h-5 sm:w-6 sm:h-6 {status.cliff.color}"
                  />
                </div>
              {/key}
            </div>
            <div class="flex-grow">
              <h3 class="font-medium text-sm sm:text-base {status.cliff.color}">
                {status.cliff.text}
              </h3>
              <div class="flex gap-2 text-xs sm:text-sm text-gray-600">
                <span
                  >Front: <span
                    class={status.cliff.front
                      ? "text-green-500"
                      : "text-red-500"}
                  >
                    {status.cliff.front ? "✓" : "✗"}</span
                  >
                </span>
                <span
                  >Back: <span
                    class={status.cliff.back
                      ? "text-green-500"
                      : "text-red-500"}
                  >
                    {status.cliff.back ? "✓" : "✗"}</span
                  >
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card.Content>
  </Card.Root>
{/if}
