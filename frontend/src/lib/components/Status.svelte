<script lang="ts">
    import { Skeleton } from '$lib/components/ui/skeleton';
    import { onMount } from 'svelte';
    import { UserRound, Spline, Brain, OctagonX } from 'lucide-svelte';
    import { type LogEntry, Mode } from '$lib/types';
    
    let { lastSensorUpdate, mode, logs = $bindable() } : { lastSensorUpdate: number, mode: Mode, logs: LogEntry[] } = $props();
    
    let status: 'Online' | 'Stale' | 'Offline' = $state('Online');
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
            
            updateLogsWithStatus();
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
                        icon: 'check',
                        message: 'Back online!',
                    } as LogEntry
                )
            } 
        } else if (status === 'Stale') {
            logs.push(
                {
                    timestamp: new Date().toISOString(),
                    icon: 'warning',
                    message: 'Going stale...',
                } as LogEntry
            );
        } else {
            logs.push(
                {
                    timestamp: new Date().toISOString(),
                    icon: 'error',
                    message: 'Robot disconnected!',
                } as LogEntry
            );
        }
    }
</script>

{#if lastSensorUpdate === 0}
    <Skeleton class="h-10 w-full rounded-sm" />
{:else}
    <div class="flex w-full flex-row items-center bg-white border border-gray-100 rounded-lg py-1.5 pl-4 pr-2 gap-2">
        {#if status === 'Online'}
            <div class="flex flex-row justify-between gap-2 w-full">
                <div class="flex flex-row items-center gap-2">
                    <div class="h-2 w-2 bg-green-500 rounded-full"></div>
                    <span class="text-green-500">Online</span>
                </div>
                <div class="flex flex-row items-center gap-1 rounded-md border border-gray-100 px-2 py-0.5 bg-gray-50 text-gray-900">
                    {#if mode === Mode.MANUAL}
                        <UserRound class="w-4 h-4" />
                    {:else if mode === Mode.AUTONOMOUS}
                        <Brain class="w-4 h-4" />
                    {:else if mode === Mode.PATH_FOLLOWING}
                        <Spline class="w-4 h-4" />
                    {:else if mode === Mode.STOPPED}
                        <OctagonX class="w-4 h-4" />
                    {/if}
                    <span class="">{mode.charAt(0) + mode.toLowerCase().slice(1)}</span>
                </div>
            </div>
        {:else if status === 'Stale'}
            <div class="h-2 w-2 bg-yellow-500 rounded-full"></div>
            <span class="text-yellow-500">Stale</span>
        {:else}
            <div class="h-2 w-2 bg-red-500 rounded-full"></div>
            <span class="text-red-500">Offline</span>
        {/if}
    </div>
{/if}