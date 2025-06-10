<script lang="ts">
    import * as Card from '$lib/components/ui/card';
    import { Skeleton } from '$lib/components/ui/skeleton';
    import QueryInput from "$lib/components/QueryInput.svelte";
    import Command from './Command.svelte';
    import { type Command as TypedCommand } from '$lib/types';
    
    let { commands, activeCommand, lastSensorUpdateTime, loading, query = $bindable(), onSubmit, inputFocus = $bindable() } : { 
        commands: TypedCommand[], 
        activeCommand: string | null, 
        lastSensorUpdateTime: number
        loading: boolean,
        query: string,
        onSubmit: (e: Event) => void,
        inputFocus: boolean
    } = $props();
</script>

{#if lastSensorUpdateTime !== 0}
    <Skeleton class="h-48 w-full" />
{:else}
    <Card.Root class="h-full w-full">
        <Card.Header>
            <Card.Title>AI Control</Card.Title>
            <Card.Description>
                Control TRACER with natural language
            </Card.Description>
        </Card.Header>
        <Card.Content>
            <div class="flex flex-col gap-2">
                {#each commands as command (command.ID)}
                    <Command {command} active={!!activeCommand && (command.ID === activeCommand)} />
                {/each}
            </div>
            <QueryInput {loading}
                bind:query={query}
                onSubmit={onSubmit}
                bind:inputFocus={inputFocus}
            />
        </Card.Content>
    </Card.Root>
{/if}