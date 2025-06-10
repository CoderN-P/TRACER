<script lang="ts">
    import type { Joystick } from '$lib/types';
    import { Skeleton } from '$lib/components/ui/skeleton';
    import { Button } from '$lib/components/ui/button';
    import * as Card from '$lib/components/ui/card';
    import {ChevronLeft, ChevronUp, Circle, ChevronDown, ChevronRight} from "lucide-svelte";


    let { joystick = $bindable(), lastUpdateTime }: { joystick: Joystick, lastUpdateTime: number } = $props();

    function updateJoystick(direction: 'up' | 'down' | 'left' | 'right' | 'stop') {
        switch (direction) {
            case 'up':
                joystick.left_y = -1;
                console.log(`Joystick updated: left_y=${joystick.left_y}, right_x=${joystick.right_x}`);
                break;
            case 'down':
                joystick.left_y = 1;
                break;
            case 'left':
                joystick.right_x = -1;
                break;
            case 'stop':
                joystick.left_y = 0;
                joystick.right_x = 0;
                break;
            case 'right':
                joystick.right_x = 1;
                break;
        }
    }

    // Reset joystick values on mouse up
    function resetJoystick(direction: 'up' | 'down' | 'left' | 'right' | 'stop') {
        switch (direction) {
            case 'up':
            case 'down':
                joystick.left_y = 0;
                break;
            case 'left':
            case 'right':
                joystick.right_x = 0;
                break;
            case 'stop':
                joystick.left_y = 0;
                joystick.right_x = 0;
                break;
        }
    }
</script>

{#if lastUpdateTime === 0}
    <Skeleton class="w-full h-48 rounded-sm" />
{:else}
    <Card.Root class="w-full h-full">
        <Card.Header class="flex flex-row items-center gap-2">
            <Card.Title>Joystick Status</Card.Title>
        </Card.Header>
        <Card.Content>
            <!-- Display D pad buttons in D pad formation -->
            <div class="grid grid-cols-3 gap-2 w-fit mx-auto">
                <div></div>
                <div tabindex={1} role="button" onmousedown={() => updateJoystick('up')} onmouseup={() => resetJoystick('up')}>
                    <Button variant="outline" class={joystick.left_y === -1 ? 'bg-emerald-100 text-emerald-500 hover:bg-emerald-100' : ''}>
                        <ChevronUp class="w-6 h-6" />
                    </Button>
                </div>
                <div></div>
                <div tabindex={1} role="button" onmousedown={() => updateJoystick('left')} onmouseup={() => resetJoystick('left')}>
                    <Button variant="outline" class={joystick.right_x === -1 ? 'bg-emerald-100 text-emerald-500 hover:bg-emerald-100' : ''}>
                        <ChevronLeft class="w-6 h-6" />
                    </Button>
                </div>
                <div tabindex={1} role="button" onmousedown={() => updateJoystick('stop')} onmouseup={() => resetJoystick('stop')}>
                    <Button variant="outline" class={joystick.left_y === 0 && joystick.right_x === 0 ? 'bg-emerald-100 text-emerald-500 hover:bg-emerald-100' : ''}>
                        <Circle class="w-6 h-6" />
                    </Button>
                </div>
                <div tabindex={1} role="button" onmousedown={() => updateJoystick('right')} onmouseup={() => resetJoystick('right')}>
                    <Button  variant="outline" class={joystick.right_x === 1 ? 'bg-emerald-100 text-emerald-500 hover:bg-emerald-100' : ''}>
                        <ChevronRight class="w-6 h-6" />
                    </Button>
                </div>
                <div></div>
                <div tabindex={1} role="button" onmousedown={() => updateJoystick('down')} onmouseup={() => resetJoystick('down')}>
                    <Button variant="outline" class={joystick.left_y === 1 ? 'bg-emerald-100 text-emerald-500 hover:bg-emerald-100' : ''}>
                        <ChevronDown class="w-6 h-6" />
                    </Button>
                </div>
            </div>
        </Card.Content>
    </Card.Root>
{/if}