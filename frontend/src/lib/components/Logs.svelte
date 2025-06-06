<script lang="ts">
    import * as Card from '$lib/components/ui/card';
    import { Skeleton } from '$lib/components/ui/skeleton';
    import { type LogEntry } from '$lib/types';
    import LogEntryDisplay from './LogEntryDisplay.svelte';
    
    
    let { logs }: { logs: LogEntry[] } = $props();
</script>

{#if !logs || logs.length === 0}
    <Skeleton class="w-full h-48 rounded-sm" />
{:else}
    <Card.Root class="w-full container h-full overflow-y-scroll pb-1 gap-2">
        <Card.Header class="h-min">
            <Card.Title>Logs</Card.Title>
        </Card.Header>
        <Card.Content class=" flex last:pb-6 flex-col-reverse overflow-y-scroll overflow-x-hidden w-full gap-2">
            {#each logs as log (log.timestamp)}
                <LogEntryDisplay {log} />
            {/each}
        </Card.Content>
    </Card.Root>
{/if}

<style>
    .container {
        -ms-overflow-style: none;  /* Internet Explorer 10+ */
        scrollbar-width: none;  /* Firefox */
    }
    .container::-webkit-scrollbar {
        display: none;  /* Safari and Chrome */
    }
</style>