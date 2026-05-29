<script lang="ts">
  import { AudioWaveform } from "lucide-svelte";

  let { rate }: { rate: number } = $props();
</script>

<div
  class="flex flex-row w-full items-center bg-white border border-gray-100 rounded-lg p-2 px-4 gap-4"
>
  <AudioWaveform class="text-black w-5 h-5" />
  <p class="font-semibold font-mono text-lg">
    {rate === -1 ? "-- Hz" : `${rate} Hz`}
  </p>
</div>
