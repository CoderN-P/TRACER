<script lang="ts">
    import { Skeleton } from '$lib/components/ui/skeleton';
    import * as Card from '$lib/components/ui/card';
    import { MountainSnow, Construction, Check } from '@lucide/svelte';
    import type { SensorData } from '$lib/types';
    
    
    let { sensorData, lastSensorUpdate } : { sensorData : SensorData | null, lastSensorUpdate: number } = $props();
    
    
    
    function getObstructionStatus() {
        if (!sensorData) return null;
        
        let status = {
            obstacle: {
                text: '',
                color: '',
                icon: null
            },
            cliff: {
                text: '',
                color: '',
                icon: null
            }
        }
        
        
        if (sensorData.ultrasonic.distance < 10){
            status.obstacle.text = 'Obstacle detected!';
            status.obstacle.color = 'text-red-500';
            status.obstacle.icon = Construction;
        } else {
            status.obstacle.text = 'No obstacle';
            status.obstacle.color = 'text-green-500';
            status.obstacle.icon = Check;
        }
        if (!sensorData.ir_front && !sensorData.ir_back){ // No cliff detected
            status.cliff.text = 'Cliff detected on both sides!';
            status.cliff.color = 'text-red-500';
            status.cliff.icon = MountainSnow;
        } else if (!sensorData.ir_front){ // Cliff on front
            status.cliff.text = 'Cliff detected on front!';
            status.cliff.color = 'text-orange-500';
            status.cliff.icon = MountainSnow;
        } else if (!sensorData.ir_back){ // Cliff on back
            status.cliff.text = 'Cliff detected on back!';
            status.cliff.color = 'text-orange-500';
            status.cliff.icon = MountainSnow;
        } else {
            status.cliff.text = 'No cliff detected';
            status.cliff.color = 'text-green-500';
            status.cliff.icon = Check;
        }
        
        return status;
    }
    
    let status = $derived.by(() => getObstructionStatus());
    let CliffIcon = $derived.by(() =>  status ? status.cliff.icon : null);
    let ObstacleIcon = $derived.by(() => status ? status.obstacle.icon : null);
    
    
</script>

{#if lastSensorUpdate === 0 || !status}
    <Skeleton class="w-full h-48 rounded-sm" />
{:else}
    <Card.Root class="w-full h-full">
        <Card.Header>
            <Card.Title>Obstruction Status</Card.Title>
            <Card.Description>Showing current obstruction status</Card.Description>
        </Card.Header>
        <Card.Content class="flex flex-col items-start  h-full">
            <div class="flex flex-col items-start gap-4">
                <div class="flex items-center gap-2">
                    <ObstacleIcon class="w-6 h-6 {status.obstacle.color}" />
                    <p class="text-lg {status.obstacle.color}">{status.obstacle.text}</p>
                </div>
                <div class="flex items-center gap-2">
                    <CliffIcon class="w-6 h-6 {status.cliff.color}" />
                    <p class="text-lg {status.cliff.color}">{status.cliff.text}</p>
                </div>
            </div>
        </Card.Content>
    </Card.Root>
{/if}