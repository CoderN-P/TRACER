<script lang="ts">
    import * as Card from '$lib/components/ui/card';
    import { type Command } from '$lib/types';
    

    let { command, active } : { command: Command, active: boolean } = $props();
</script>