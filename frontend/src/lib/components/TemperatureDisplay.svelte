<script lang="ts">
    import { Skeleton } from '$lib/components/ui/skeleton';
    import * as Card from '$lib/components/ui/card';
    import { ThermometerSnowflake, ThermometerSun } from 'lucide-svelte';
    let { temperature }: { temperature: number | null } = $props();
    
    let tempF = $derived(((temperature ?? 0 ) * 9/5 + 32));
</script>

{#if temperature === null}
    <Skeleton class="w-full h-48 rounded-sm" />
{:else}
    <Card.Root class="w-full h-full">
        <Card.Header class="flex flex-row items-center gap-2">
            {#if tempF < 60}
                <ThermometerSnowflake class="text-blue-500" />
            {:else}
                <ThermometerSun class="text-red-500" />
            {/if}
            <Card.Title>Temperature</Card.Title>
        </Card.Header>
        <Card.Content class="flex flex-col justify-start gap-2">
            <div class="text-4xl font-bold font-mono">
                {tempF.toFixed(2)}°F
            </div>
            <p class="text-sm text-gray-500 font-mono">
                {temperature.toFixed(2)}°C
            </p>
        </Card.Content>
    </Card.Root>
{/if}

