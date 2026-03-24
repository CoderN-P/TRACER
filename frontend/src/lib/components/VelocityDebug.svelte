<script lang="ts">
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { Activity } from 'lucide-svelte';
  import type { RobotState } from '$lib/types';

  let { robotState, lastSensorUpdateTime }: { robotState: RobotState | null; lastSensorUpdateTime: number } = $props();
  
  let linearVelocityMps = $derived(robotState ? robotState.linear_velocity : 0);
  
  // Convert rad/s to deg/s for display
  let angularVelocityDps = $derived(robotState ? (robotState.angular_velocity * 180) / Math.PI : 0);

  // Create visual indicators
  let linearSpeedPercent = $derived(robotState ? Math.min(Math.abs(linearVelocityMps) / 0.25, 1) * 100 : 0); // Assume max speed = 0.25 m/s
  let angularSpeedPercent = $derived(robotState ? Math.min(Math.abs(angularVelocityDps) / 180, 1) * 100 : 0); // Assume max angular speed is 180 deg/s

  let linearDirection = $derived(robotState && robotState.linear_velocity < 0 ? 'Backward' : 'Forward');
  let angularDirection = $derived(robotState && robotState.angular_velocity > 0 ? 'CCW' : 'CW');
</script>

{#if lastSensorUpdateTime === 0}
  <Skeleton class="w-full h-48 rounded-sm" />
{:else}
  <div class="w-full bg-white border border-gray-100 rounded-lg p-4 space-y-4">
    <div class="flex flex-row items-center gap-2 mb-3">
      <Activity class="text-black w-5 h-5" />
      <h3 class="font-semibold text-lg">Velocity Debug</h3>
    </div>

    <!-- Linear Velocity Section -->
    <div class="space-y-2">
      <div class="flex justify-between items-center">
        <label class="text-sm font-semibold text-gray-700">Linear Velocity</label>
        <span class="text-sm font-mono text-gray-600">{linearVelocityMps.toFixed(2)} m/s</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="relative flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            class="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-400 to-blue-600 transition-all duration-200"
            style="width: {linearSpeedPercent}%"
          />
        </div>
        <span class="text-xs font-mono text-gray-500 w-10 text-right">{linearDirection}</span>
      </div>
      <div class="text-xs text-gray-500">
        {Math.abs(linearVelocityMps).toFixed(2)} m/s
      </div>
    </div>

    <!-- Angular Velocity Section -->
    <div class="space-y-2">
      <div class="flex justify-between items-center">
        <label class="text-sm font-semibold text-gray-700">Angular Velocity</label>
        <span class="text-sm font-mono text-gray-600">{angularVelocityDps.toFixed(1)}°/s</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="relative flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            class="absolute top-0 left-0 h-full bg-gradient-to-r from-purple-400 to-purple-600 transition-all duration-200"
            style="width: {angularSpeedPercent}%"
          />
        </div>
        <span class="text-xs font-mono text-gray-500 w-10 text-right">{angularDirection}</span>
      </div>
      <div class="text-xs text-gray-500">
        {Math.abs(robotState?.angular_velocity ?? 0).toFixed(3)} rad/s
      </div>
    </div>

    <!-- Combined Speed Indicator -->
    <div class="mt-4 pt-4 border-t border-gray-200">
      <div class="flex justify-between items-center mb-2">
        <label class="text-sm font-semibold text-gray-700">Combined Speed</label>
        <span class="text-sm font-mono text-gray-600">
          {Math.sqrt(
            Math.pow(linearVelocityMps, 2) + Math.pow(angularVelocityDps * Math.PI / 180, 2)
          ).toFixed(2)}
        </span>
      </div>
      <div class="relative flex-1 h-4 bg-gray-200 rounded-full overflow-hidden">
        <div
          class="absolute top-0 left-0 h-full bg-gradient-to-r from-green-400 via-green-500 to-green-600 transition-all duration-200"
          style="width: {Math.min((linearSpeedPercent + angularSpeedPercent) / 2, 100)}%"
        />
      </div>
    </div>

    <!-- Vector Visualization -->
    <div class="mt-4 pt-4 border-t border-gray-200">
      <div class="text-xs font-semibold text-gray-700 mb-2">Vector Visualization</div>
      <svg class="w-full h-24 bg-gray-50 rounded border border-gray-200" viewBox="0 0 200 120">
        <!-- Grid -->
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#e5e7eb" stroke-width="0.5" />
          </pattern>
        </defs>
        <rect width="200" height="120" fill="url(#grid)" />

        <!-- Center point -->
        <circle cx="100" cy="60" r="3" fill="#999" />

        <!-- Linear velocity vector (blue)
             Scale: 1 unit = 30px -->
        {#if robotState}
          <line
            x1="100"
            y1="60"
            x2={100 + (linearVelocityMps / 2) * 30}
            y2={60 - (angularVelocityDps / 360) * 30}
            stroke="#3b82f6"
            stroke-width="2"
            marker-end="url(#arrowblue)"
          />
        {/if}

        <!-- Arrow markers -->
        <defs>
          <marker id="arrowblue" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L9,3 z" fill="#3b82f6" />
          </marker>
        </defs>

        <!-- Labels -->
        <text x="5" y="15" class="text-xs fill-gray-600" font-size="10">Linear (blue)</text>
        <text x="5" y="110" class="text-xs fill-gray-600" font-size="10">Angular Rotation</text>
      </svg>
    </div>
  </div>
{/if}

<style>
  :global(.velocity-debug-container) {
    width: 100%;
  }
</style>
