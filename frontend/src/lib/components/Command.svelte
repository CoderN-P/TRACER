<script lang="ts">
  import {
    Car,
    Monitor,
    StopCircle,
    LoaderCircle,
    Hourglass,
    ArrowRight,
    ArrowLeft,
    RotateCw,
    RotateCcw,
    ArrowDown,
    PauseCircle,
  } from "lucide-svelte";
  import { type Command, CommandType } from "$lib/types";
  import { slide } from "svelte/transition";
  import { quintOut } from "svelte/easing";

  let { command, active }: { command: Command; active: boolean } = $props();

  // Helper to determine motor action type
  function getMotorActionType(left: number, right: number) {
    if (left > 0 && right > 0 && Math.abs(left - right) < 50) return "forward";
    if (left < 0 && right < 0 && Math.abs(left - right) < 50) return "backward";
    if (left > 0 && right < 0) return "spin-right";
    if (left < 0 && right > 0) return "spin-left";
    if (left > 0 && right > 0 && left > right) return "turn-left";
    if (left > 0 && right > 0 && left < right) return "turn-right";
    return "custom";
  }

  // Format duration for display
  function formatDuration(seconds: number): string {
    if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
    return `${seconds}s`;
  }

  // Calculate progress percentage for active commands
  $effect(() => {
    if (active) {
      const interval = setInterval(() => {
        progress = Math.min(100, progress + 1);
      }, command.duration * 10);

      return () => clearInterval(interval);
    } else {
      progress = 0;
    }
  });

  let progress = $state(0);

  // Get action type for motor commands
  const motorAction =
    command.command_type === CommandType.MOTOR && command.command
      ? getMotorActionType(
          command.command.left_motor,
          command.command.right_motor
        )
      : null;
</script>

<div
  class="rounded-lg shrink-0 hover:bg-slate-50 {active
    ? 'bg-slate-50 shadow border-l-4 border-l-green-500'
    : 'border border-slate-200'} transition-all duration-200 overflow-hidden
    touch-manipulation"
  transition:slide={{ duration: 400, easing: quintOut }}
>
  <!-- Command header -->
  <div class="flex items-center p-2.5 sm:p-3 gap-2 sm:gap-3">
    <!-- Icon with activity indicator -->
    <div class="relative">
      {#if active}
        <div
          class="absolute inset-0 bg-green-100 rounded-full animate-ping opacity-50"
        ></div>
        <LoaderCircle
          class="w-7 h-7 text-green-500 animate-spin relative z-10"
        />
      {:else}
        <div
          class="p-1.5 rounded-full {command.command_type === CommandType.MOTOR
            ? 'bg-purple-100'
            : command.command_type === CommandType.LCD
              ? 'bg-blue-100'
              : 'bg-red-100'}"
        >
          {#if command.command_type === CommandType.MOTOR}
            {#if motorAction === "forward"}
              <Car class="w-5 h-5 text-purple-600" />
            {:else if motorAction === "backward"}
              <ArrowDown class="w-5 h-5 text-purple-600" />
            {:else if motorAction === "spin-left"}
              <RotateCcw class="w-5 h-5 text-purple-600" />
            {:else if motorAction === "spin-right"}
              <RotateCw class="w-5 h-5 text-purple-600" />
            {:else if motorAction === "turn-left"}
              <ArrowLeft class="w-5 h-5 text-purple-600" />
            {:else if motorAction === "turn-right"}
              <ArrowRight class="w-5 h-5 text-purple-600" />
            {:else}
              <Car class="w-5 h-5 text-purple-600" />
            {/if}
          {:else if command.command_type === CommandType.LCD}
            <Monitor class="w-5 h-5 text-blue-600" />
          {:else if command.command_type === CommandType.STOP}
            <StopCircle class="w-5 h-5 text-red-600" />
          {/if}
        </div>
      {/if}
    </div>

    <!-- Command details -->
    <div class="flex-grow">
      {#if command.command_type === CommandType.MOTOR}
        <h3 class="text-base font-medium text-slate-800">
          {#if motorAction === "forward"}
            Moving Forward
          {:else if motorAction === "backward"}
            Moving Backward
          {:else if motorAction === "spin-left"}
            Spinning Left
          {:else if motorAction === "spin-right"}
            Spinning Right
          {:else if motorAction === "turn-left"}
            Turning Left
          {:else if motorAction === "turn-right"}
            Turning Right
          {:else}
            Moving Motors
          {/if}
        </h3>
        <div class="flex flex-col sm:flex-row gap-1 sm:gap-3 mt-1">
          <p class="text-xs text-slate-500 flex items-center gap-1">
            <span class="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-green-400"></span>
            Left: {command.command?.left_motor}
          </p>
          <p class="text-xs text-slate-500 flex items-center gap-1">
            <span class="w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full bg-blue-400"></span>
            Right: {command.command?.right_motor}
          </p>
        </div>
      {:else if command.command_type === CommandType.LCD}
        <h3 class="text-base font-medium text-slate-800">Displaying Message</h3>
        <div class="mt-1 text-xs px-2 py-1 bg-slate-100 rounded-md font-mono">
          <p class="truncate">&quot;{command.command?.line_1 || ""}&quot;</p>
          {#if command.command?.line_2}
            <p class="truncate">&quot;{command.command.line_2}&quot;</p>
          {/if}
        </div>
      {:else if command.command_type === CommandType.STOP}
        <h3 class="text-base font-medium text-slate-800">
          Stopping All Motors
        </h3>
        <div class="mt-1 text-xs text-slate-500 flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-red-400"></span>
          <span>Emergency stop signal sent to robot</span>
        </div>
      {/if}
    </div>

    <!-- Duration badge -->
    <div
      class="flex items-center gap-1 text-xs bg-slate-100 px-2 py-1 rounded-full"
    >
      <Hourglass class="w-3 h-3 text-slate-500" />
      <span>{formatDuration(command.duration)}</span>
    </div>
  </div>

  <!-- Progress bar for active commands -->
  {#if active}
    <div class="h-1 bg-slate-100 w-full">
      <div
        class="bg-green-500 h-full transition-all duration-100"
        style="width: {progress}%;"
      ></div>
    </div>
  {/if}

  <!-- Pause indicator if there's a pause duration -->
  {#if command.pause_duration > 0 && !active}
    <div
      class="flex items-center gap-2 bg-slate-50 px-3 py-1.5 text-xs text-slate-500 border-t border-slate-200"
    >
      <PauseCircle class="w-3 h-3" />
      <span
        >Pause for {formatDuration(command.pause_duration)} after execution</span
      >
    </div>
  {/if}
</div>
