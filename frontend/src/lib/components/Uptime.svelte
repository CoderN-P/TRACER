<script lang="ts">
    import { onMount } from 'svelte';
    import { Skeleton } from '$lib/components/ui/skeleton';
    import {Clock} from "lucide-svelte";
    
    let { lastSensorUpdate } : { lastSensorUpdate: number } = $props();
    
    let time: number = $state(0);
    let status: 'Online' | 'Stale' | 'Offline' = $state('Offline');
    
    onMount(() => {
        
        const updateTime = () => {
            if (lastSensorUpdate === 0) {
                status = 'Offline';
                time = 0;
                return;
            }
            // Calculate the time since the last sensor update in seconds
            
            const now = Date.now();
            console.log(now-lastSensorUpdate);
            if (now - lastSensorUpdate < 5000) {
                if (now - lastSensorUpdate < 1000) {
                    status = 'Online';
                } else {
                    status = 'Stale';
                }
                time++; // Less than 5 seconds since last update - still online
            } else {
                time = 0;
            }
        };
        
        updateTime();
        const interval = setInterval(updateTime, 1000);
        
        return () => clearInterval(interval);
    });
    
    function formatTime() {
        // Format: 2 num for all
        
        return {
            seconds: String((time % 60)).padStart(2, '0') ,
            minutes: String(Math.floor(time / 60) % 60).padStart(2, '0'),
            hours: String(Math.floor(time / 3600)).padStart(2, '0')
        }
    }
    
    let formattedTime = $derived.by(formatTime)
</script>

{#if lastSensorUpdate === 0}
    <Skeleton class="h-10 w-full rounded-sm" />
{:else}
    <div class="flex flex-row w-full items-center bg-white border border-gray-100 rounded-lg p-2 px-4 gap-4">
        <Clock class="text-black w-5 h-5" />
        <p class="font-semibold font-mono text-lg">
            {formattedTime.hours}:{formattedTime.minutes}:{formattedTime.seconds}
        </p>
    </div>
{/if}

