<script lang="ts">
    import { Skeleton } from '$lib/components/ui/skeleton';
    import { onMount } from 'svelte';
    import type { LogEntry } from '$lib/types';
    
    let { lastSensorUpdate, logs } : { lastSensorUpdate: number, logs: LogEntry[] } = $props();
    
    let status: 'Online' | 'Stale' | 'Offline' = $state('Offline');
    let prevStatus: 'Online' | 'Stale' | 'Offline' = $state('Offline');
    
    onMount(() => {
        setInterval(() => {
            prevStatus = status;
            if (lastSensorUpdate === 0) {
                status = 'Offline';
                return;
            }
            const now = Date.now();
            if (now - lastSensorUpdate < 1000) { // Last update within 1 minute
                status = 'Online';
            } else if (now - lastSensorUpdate < 5000) { // Last update within 5 minutes
                status = 'Stale';
            } else {
                status = 'Offline';
            }
        }, 1000); // Check every second
    });
    
    function updateLogsWithStatus() {
        if (prevStatus === status) {
            return; // No change in status
        }
        if (status === 'Online' ) {
            if (logs.find(log => log.message === 'Going stale...' || log.message === 'Robot disconnected!')) {
                logs.push(
                    {
                        timestamp: new Date().toISOString(),
                        type: 'success',
                        message: 'Back online!',
                    } as LogEntry
                )
            } 
        } else if (status === 'Stale') {
            logs.push(
                {
                    timestamp: new Date().toISOString(),
                    type: 'warning',
                    message: 'Going stale...',
                } as LogEntry
            );
        } else {
            logs.push(
                {
                    timestamp: new Date().toISOString(),
                    type: 'error',
                    message: 'Robot disconnected!',
                } as LogEntry
            );
        }
    }
</script>

{#if lastSensorUpdate === 0}
    <Skeleton class="h-10 w-full rounded-sm" />
{:else}
    <div class="flex w-full flex-row items-center bg-white border border-gray-100 rounded-xl p-4 gap-2">
        {#if status === 'Online'}
            <div class="h-2 w-2 bg-green-500 rounded-full"></div>
            <span class="text-green-500">Online</span>
        {:else if status === 'Stale'}
            <div class="h-2 w-2 bg-yellow-500 rounded-full"></div>
            <span class="text-yellow-500">Stale</span>
        {:else}
            <div class="h-2 w-2 bg-red-500 rounded-full"></div>
            <span class="text-red-500">Offline</span>
        {/if}
    </div>
{/if}