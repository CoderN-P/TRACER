<script lang="ts">
  import { OctagonX, Hand } from "lucide-svelte";
  import { io as socket } from "$lib/api/socket";

  let { lastSensorUpdateTime }: { lastSensorUpdateTime: number } = $props();

  let connected = $derived(
    lastSensorUpdateTime > 0 && Date.now() - lastSensorUpdateTime < 5000,
  );

  function emergencyStop() {
    socket.emit("stop", {});
  }

  function returnToManual() {
    socket.emit("set_state", { state: "MANUAL" });
  }
</script>

<div
  class="rounded-lg border border-gray-100 px-4 py-1.5 flex flex-row shrink-0 grow w-full sm:w-min bg-white items-center gap-3 "
>
  <!-- Emergency Stop -->
  <button
    onclick={emergencyStop}
    disabled={!connected}
    class="flex items-center gap-1.5 px-2 py-1 rounded-sm font-semibold text-sm transition-colors
      bg-red-200 hover:bg-red-300 active:bg-red-400 text-red-600
      disabled:opacity-40 disabled:cursor-not-allowed border border-red-200"
    title="Emergency stop — immediately halts all motors"
  >
    <OctagonX class="w-4 h-4" />
    Stop
  </button>

  <!-- Return to Manual -->
  <button
    onclick={returnToManual}
    disabled={!connected}
    class="flex items-center gap-1.5 px-2 py-1 rounded-sm font-semibold text-sm transition-colors
      bg-amber-200 hover:bg-amber-300 active:bg-amber-400
      disabled:opacity-40 text-amber-600 border border-amber-200 disabled:cursor-not-allowed"
    title="Return to manual control mode"
  >
    <Hand class="w-4 h-4" />
    Manual
  </button>
</div>
