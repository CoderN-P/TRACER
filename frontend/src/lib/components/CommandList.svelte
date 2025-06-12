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
    
    let commandContainer: HTMLElement | null = null;
    
    $effect(() => {
        if (commands && commandContainer) {
            // Scroll to bottom when new commands are added
            commandContainer.scrollTop = commandContainer.scrollHeight;
        }
    });
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
        <Card.Content class="px-3 sm:px-6 h-full">
            <!-- Command history with dynamic height based on screen size -->
            <div bind:this={commandContainer} style="height: calc(100% - 70px); max-height: 230px;" class="flex container flex-col gap-2 mb-3 sm:mb-4 
                        flex-grow h-[calc(100% - 36px)]
                        overflow-y-scroll overscroll-contain 
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