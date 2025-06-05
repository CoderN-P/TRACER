<script lang="ts">
    import { cn } from '$lib/utils.js';
    import { type Joystick } from '$lib/types.js';
    import {Skeleton} from "$lib/components/ui/skeleton";

    let { joystick, lastUpdateTime }: { joystick: Joystick, lastUpdateTime: number } = $props();
    
</script>

{#if lastUpdateTime === 0}
    <Skeleton class="w-full h-48 rounded-sm" />
{:else}
{/if}