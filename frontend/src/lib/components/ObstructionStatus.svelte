<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import {
    Construction,
    Check,
    AlertTriangle,
    Car,
    Gauge,
  } from "lucide-svelte";
  import type { SensorData } from "$lib/types";
  import { fade, fly, scale } from "svelte/transition";
  import { quintOut, elasticOut } from "svelte/easing";

  type ObstacleIcon = typeof Check;

  type ObstacleStatus = {
    text: string;
    color: string;
    bgColor: string;
    icon: ObstacleIcon | null;
    distance: number;
    severity: "critical" | "warning" | "caution" | "safe";
  };

  type ObstructionStatus = {
    obstacle: ObstacleStatus;
  };

  const DEFAULT_STATUS: ObstructionStatus = {
    obstacle: {
      text: "No obstacle data yet",
      color: "text-gray-500",
      bgColor: "bg-gray-50",
      icon: Gauge,
      distance: 0,
      severity: "safe",
    },
  };

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
  const CRITICAL_DISTANCE = 10;
  const WARNING_DISTANCE = 20;
  const SAFE_DISTANCE = 30;

  function getObstructionStatus(data: SensorData): ObstructionStatus {
    let status: ObstructionStatus = {
      obstacle: {
        text: "",
        color: "",
        bgColor: "",
        icon: null,
        distance: data.ultrasonic.distance,
        severity: "safe",
      },
    };

    // Obstacle detection logic with severity levels
    if (data.ultrasonic.distance < CRITICAL_DISTANCE) {
      status.obstacle.text = "Critical! Obstacle very close";
      status.obstacle.color = "text-red-600";
      status.obstacle.bgColor = "bg-red-100";
      status.obstacle.icon = AlertTriangle;
      status.obstacle.severity = "critical";
    } else if (data.ultrasonic.distance < WARNING_DISTANCE) {
      status.obstacle.text = "Warning! Obstacle detected";
      status.obstacle.color = "text-orange-500";
      status.obstacle.bgColor = "bg-orange-100";
      status.obstacle.icon = Construction;
      status.obstacle.severity = "warning";
    } else if (data.ultrasonic.distance < SAFE_DISTANCE) {
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
  let status = $derived.by(() =>
    sensorData ? getObstructionStatus(sensorData) : DEFAULT_STATUS,
  );

  let ObstacleIcon = $derived.by(() => status.obstacle.icon);
  let progressPercentage = $derived.by(() => getProgressPercentage());
</script>

<Card.Root class="w-full h-full min-h-0 {className} flex flex-col">
  <Card.Header>
    <Card.Title class="flex items-center gap-2">
      <Car class="w-5 h-5" />
      <span>Obstruction Status</span>
    </Card.Title>
    <Card.Description>
      {lastSensorUpdate === 0
        ? "No live obstacle data yet"
        : "Real-time obstacle distance detection"}
    </Card.Description>
  </Card.Header>
  <Card.Content class="px-3 sm:px-6 pb-4 min-h-0 flex-1">
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

    <div class="grid grid-cols-1 gap-3">
      <!-- Obstacle Status Card -->
      <div
        class="rounded-lg {status.obstacle
          .bgColor} p-3 border border-gray-100 transition-all duration-300"
        in:fly={{ y: 10, duration: 300, easing: quintOut }}
      >
        <div class="flex items-center gap-2 mb-1">
          <div class="p-1.5 bg-white bg-opacity-60 rounded-full">
            {#key status.obstacle.severity}
              <div in:scale={{ start: 0.8, duration: 300, easing: elasticOut }}>
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
    </div>
  </Card.Content>
</Card.Root>
