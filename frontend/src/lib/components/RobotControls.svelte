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
  class="rounded-lg border border-gray-200 p-3 flex flex-row items-center gap-3 flex-wrap"
>
  <span class="text-xs font-medium text-gray-500 mr-1">Robot Controls</span>

  <!-- Emergency Stop -->
  <button
    onclick={emergencyStop}
    disabled={!connected}
    class="flex items-center gap-1.5 px-4 py-2 rounded-md font-semibold text-sm transition-colors
      bg-red-600 hover:bg-red-700 active:bg-red-800 text-white
      disabled:opacity-40 disabled:cursor-not-allowed
      shadow-sm"
    title="Emergency stop — immediately halts all motors"
  >
    <OctagonX class="w-4 h-4" />
    E-Stop
  </button>

  <!-- Return to Manual -->
  <button
    onclick={returnToManual}
    disabled={!connected}
    class="flex items-center gap-1.5 px-4 py-2 rounded-md font-semibold text-sm transition-colors
      bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-white
      disabled:opacity-40 disabled:cursor-not-allowed
      shadow-sm"
    title="Return to manual control mode"
  >
    <Hand class="w-4 h-4" />
    Manual
  </button>
</div>
