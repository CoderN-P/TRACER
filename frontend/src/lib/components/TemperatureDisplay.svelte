<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { ThermometerSnowflake, ThermometerSun } from "lucide-svelte";
  let {
    temperature,
    class: className = "",
  }: { temperature: number | null; class?: string } = $props();

  let tempF = $derived(((temperature ?? 0) * 9) / 5 + 32);
</script>

<Card.Root class="w-full h-full {className}">
  <Card.Header class="flex flex-row items-center gap-2">
    {#if temperature !== null && tempF < 60}
      <ThermometerSnowflake class="text-blue-500" />
    {:else}
      <ThermometerSun class="text-red-500" />
    {/if}
    <Card.Title>Temperature</Card.Title>
  </Card.Header>
  <Card.Content class="flex flex-col justify-start gap-2">
    <div class="text-4xl font-bold font-mono">
      {temperature === null ? "--" : `${tempF.toFixed(2)}°F`}
    </div>
    <p class="text-sm text-gray-500 font-mono">
      {temperature === null ? "No data" : `${temperature.toFixed(2)}°C`}
    </p>
  </Card.Content>
</Card.Root>
