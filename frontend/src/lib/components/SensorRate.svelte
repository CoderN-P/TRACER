<script lang="ts">
    import { Skeleton } from '$lib/components/ui/skeleton';
    import { AudioWaveform } from "lucide-svelte";

    let { rate }: { rate: number } = $props();
</script>

{#if rate === -1}
    <Skeleton class="w-full h-10 rounded-sm" />
{:else}
    <div class="flex flex-row w-full items-center bg-white border border-gray-100 rounded-lg p-2 px-4 gap-4">
        <AudioWaveform class="text-black w-5 h-5" />
        <p class="font-semibold font-mono text-lg">
            {rate} Hz
        </p>
    </div>
{/if}