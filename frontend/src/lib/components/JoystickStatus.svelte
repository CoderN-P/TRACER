<script lang="ts">
    import * as Card from '$lib/components/ui/card';
    import { type Joystick } from '$lib/types';
    import {Skeleton} from "$lib/components/ui/skeleton";

    let { joystick, lastUpdateTime, class: className = "" }: 
        { joystick: Joystick, lastUpdateTime: number, class?: string } = $props();
    
</script>

{#if lastUpdateTime === 0 || !joystick}
    <Skeleton class="w-full h-48 rounded-sm " />
{:else}
    <Card.Root class="w-full h-full {className}">
        <Card.Header>
            <Card.Title>Joystick Status</Card.Title>
            <Card.Description>Showing current joystick position</Card.Description>
        </Card.Header>
        <Card.Content class="flex flex-col items-center justify-center p-4">
            <div class="relative w-20 h-20 mx-auto bg-gray-100 rounded-full border border-gray-200">
                <div
                        class="absolute w-6 h-6 bg-blue-500 rounded-full border-2 border-white shadow-lg transition-all duration-200"
                        style="left: calc(50% - 12px + {-30*joystick.right_x}px); top: calc(50% - 12px + {-30*joystick.left_y}px)"
                ></div>
                <div class="absolute inset-0 flex items-center justify-center">
                    <div class="w-2 h-2 bg-gray-300 rounded-full"></div>
                </div>
            </div>
            
            <!-- Display values for better understanding -->
            <div class="flex flex-row gap-4 mt-4 text-xs">
                <div class="flex flex-col items-center">
                    <span class="font-semibold">Left-Y</span>
                    <span>{joystick.left_y.toFixed(2)}</span>
                </div>
                <div class="flex flex-col items-center">
                    <span class="font-semibold">Right-X</span>
                    <span>{joystick.right_x.toFixed(2)}</span>
                </div>
            </div>
        </Card.Content>
    </Card.Root>
    
{/if}