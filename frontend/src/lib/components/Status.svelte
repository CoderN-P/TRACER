<script lang="ts">
  import { onMount } from "svelte";
  import { UserRound, Spline, Brain, OctagonX, MapPinned } from "lucide-svelte";
  import { type LogEntry, Mode } from "$lib/types";

  let {
    lastSensorUpdate,
    mode,
    localizationMode = null,
    logs = $bindable(),
  }: {
    lastSensorUpdate: number;
    mode: Mode;
    localizationMode?: string | null;
    logs: LogEntry[];
  } = $props();

  let status: "Online" | "Stale" | "Offline" = $state("Online");
  let prevStatus: "Online" | "Stale" | "Offline" = $state("Offline");

  onMount(() => {
    setInterval(() => {
      prevStatus = status;
      if (lastSensorUpdate === 0) {
        status = "Offline";
        return;
      }
      const now = Date.now();
      if (now - lastSensorUpdate < 1000) {
        // Last update within 1 minute
        status = "Online";
      } else if (now - lastSensorUpdate < 5000) {
        // Last update within 5 minutes
        status = "Stale";
      } else {
        status = "Offline";
      }

      updateLogsWithStatus();
    }, 1000); // Check every second
  });

  function updateLogsWithStatus() {
    if (prevStatus === status) {
      return; // No change in status
    }
    if (status === "Online") {
      if (
        logs.find(
          (log) =>
            log.message === "Going stale..." ||
            log.message === "Robot disconnected!",
        )
      ) {
        logs.push({
          timestamp: new Date().toISOString(),
          icon: "check",
          message: "Back online!",
        } as LogEntry);
      }
    } else if (status === "Stale") {
      logs.push({
        timestamp: new Date().toISOString(),
        icon: "warning",
        message: "Going stale...",
      } as LogEntry);
    } else {
      logs.push({
        timestamp: new Date().toISOString(),
        icon: "error",
        message: "Robot disconnected!",
      } as LogEntry);
    }
  }

  function formatModeName(value: string) {
    return value
      .toLowerCase()
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }
</script>

<div
  class="flex w-full flex-row items-center bg-white border border-gray-100 rounded-lg py-1.5 pl-4 pr-2 gap-2"
>
  {#if status === "Online"}
    <div class="flex flex-row justify-between gap-2 w-full">
      <div class="flex flex-row items-center gap-2">
        <div class="h-2 w-2 bg-green-500 rounded-full"></div>
        <span class="text-green-500">Online</span>
      </div>
      <div class="flex flex-row items-center gap-1.5">
        <div
          class="flex flex-row items-center gap-1 rounded-md border border-gray-100 px-2 py-0.5 bg-gray-50 text-gray-900"
          title="Drive mode"
        >
          {#if mode === Mode.MANUAL}
            <UserRound class="w-4 h-4" />
          {:else if mode === Mode.AUTONOMOUS}
            <Brain class="w-4 h-4" />
          {:else if mode === Mode.PATH_FOLLOWING}
            <Spline class="w-4 h-4" />
          {:else if mode === Mode.STOPPED}
            <OctagonX class="w-4 h-4" />
          {/if}
          <span>{formatModeName(mode)}</span>
        </div>
        {#if localizationMode}
          <div
            class="flex flex-row items-center gap-1 rounded-md border border-blue-100 px-2 py-0.5 bg-blue-50 text-blue-900"
            title="Localization mode"
          >
            <MapPinned class="w-4 h-4" />
            <span>{formatModeName(localizationMode)}</span>
          </div>
        {/if}
      </div>
    </div>
  {:else if status === "Stale"}
    <div class="h-2 w-2 bg-yellow-500 rounded-full"></div>
    <span class="text-yellow-500">Stale</span>
  {:else}
    <div class="h-2 w-2 bg-red-500 rounded-full"></div>
    <span class="text-red-500">Offline</span>
  {/if}
</div>
