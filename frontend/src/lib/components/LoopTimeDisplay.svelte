<script lang="ts">
  import { Gauge } from "lucide-svelte";

  let { value }: { value: number | null } = $props();
</script>

<div
  class="flex w-full flex-row items-center gap-4 rounded-lg border border-gray-100 bg-white p-2 px-4"
>
  <Gauge class="h-5 w-5 text-black" />
  <p class="font-mono text-lg font-semibold">
    {value === null ? "-- ms" : `${value.toFixed(0)} ms`}
  </p>
</div>
