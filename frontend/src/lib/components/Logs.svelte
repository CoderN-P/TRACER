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
    <Card.Root class="w-full h-full">
        <Card.Header>
            <Card.Title>Logs</Card.Title>
        </Card.Header>
        <Card.Content class="flex flex-col-reverse w-full gap-2">
            {#each logs as log (log.timestamp)}
                <LogEntryDisplay {log} />
            {/each}
        </Card.Content>
    </Card.Root>
{/if}