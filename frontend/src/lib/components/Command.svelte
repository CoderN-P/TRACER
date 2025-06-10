<script lang="ts">
    import { Car, Monitor, StopCircle, LoaderCircle } from "lucide-svelte";
    import { type Command, CommandType } from '$lib/types';
    

    let { command, active } : { command: Command, active: boolean } = $props();
    
    
</script>

<div class="rounded-lg hover:bg-gray-50 {active ? 'border-2 border-green-500' : 'border border-gray-100' } flex flex-row gap-2 p-2">
    {#if active}
        <LoaderCircle class="w-6 h-6 text-green-500 animate-spin" />
    {:else}
        {#if command.command_type === CommandType.MOTOR}
            <Car class="w-6 h-6 text-purple-500" />
        {:else if command.command_type === CommandType.LCD}
            <Monitor class="w-6 h-6 text-blue-500" />
        {:else if command.command_type === CommandType.STOP}
            <StopCircle class="w-6 h-6 text-red-500" />
        {/if}
    {/if}

    {#if command.command_type === CommandType.MOTOR}
        <p class="text-lg font-semibold">
            Moving motors
        </p>
        <p class="text-xs text-gray-500">
            Left motor at {command.command.left_motor}, Right motor at {command.command.right_motor}
        </p>
    {:else if command.command_type === CommandType.LCD}
        <p class="text-lg font-semibold">
            Displaying on LCD
        </p>
        <p class="text-xs text-gray-500">
            Line 1: "{command.command.line_1}", Line 2: "{command.command.line_2}"
        </p>
    {:else if command.command_type === CommandType.STOP}
        <p class="text-lg font-semibold">
            Stopping motors
        </p>
    {/if}
</div>