<script lang="ts">
    import * as Card from '$lib/components/ui/card';
    import { Skeleton } from '$lib/components/ui/skeleton';
    import QueryInput from "$lib/components/QueryInput.svelte";
    import Command from './Command.svelte';
    import { type Command as TypedCommand } from '$lib/types';
    
    let { commands, activeCommand, lastSensorUpdateTime, loading, query = $bindable(), onSubmit, inputFocus = $bindable(), class: className = '' } : { 
        commands: TypedCommand[], 
        activeCommand: string | null, 
        lastSensorUpdateTime: number
        loading: boolean,
        query: string,
        onSubmit: (e: Event) => void,
        inputFocus: boolean,
        class?: string
    } = $props();
</script>

{#if lastSensorUpdateTime === 0}
    <Skeleton class="h-48 w-full" />
{:else}
    <Card.Root class="h-full w-full {className}">
        <Card.Header class="">
            <Card.Title>AI Control</Card.Title>
            <Card.Description>
                Control TRACER with natural language
            </Card.Description>
        </Card.Header>
        <Card.Content class="px-3 sm:px-6">
            <!-- Command history with dynamic height based on screen size -->
            <div class="flex flex-col gap-2 mb-3 sm:mb-4 
                        max-h-[35vh] sm:max-h-[40vh] md:max-h-[45vh] 
                        overflow-y-auto overscroll-contain 
                        rounded-md p-1">
                {#if commands.length === 0}
                    <div class="text-center py-6 text-gray-400 text-sm italic">
                        No commands yet. Type a command below.
                    </div>
                {:else}
                    {#each commands as command (command.ID)}
                        <Command {command} active={!!activeCommand && (command.ID === activeCommand)} />
                    {/each}
                {/if}
            </div>
            <!-- Input area with better mobile spacing -->
            <div class="mt-1 sm:mt-2">
                <QueryInput {loading}
                    bind:query={query}
                    onSubmit={onSubmit}
                    bind:inputFocus={inputFocus}
                    class="w-full"
                />
            </div>
        </Card.Content>
    </Card.Root>
{/if}