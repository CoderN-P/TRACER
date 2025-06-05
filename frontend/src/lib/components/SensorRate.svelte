<script lang="ts">
import { Skeleton } from '$lib/components/ui/skeleton';
    let { rate }: { rate: number } = $props();
</script>

{#if rate === -1}
    <Skeleton class="w-full h-10 rounded-sm" />
{:else}
    <div class="flex flex-row w-full items-center bg-white border border-gray-100 rounded-xl p-4 gap-2">
        <p class="font-semibold font-mono text-lg">
            {rate} Hz
        </p>
    </div>
{/if}