<script lang="ts">
    import { type Joystick } from '$lib/types';
    import { onMount } from 'svelte';
    
    let { joystick } : { joystick: Joystick } = $props();
    
    onMount(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'ArrowUp') {
                joystick.left_y = -1;
            } else if (event.key === 'ArrowDown') {
                joystick.left_y = 1;
            } else if (event.key === 'ArrowLeft') {
                joystick.right_x = -1;
            } else if (event.key === 'ArrowRight') {
                joystick.right_x = 1;
            }
        };

        const handleKeyUp = (event: KeyboardEvent) => {
            if (
                event.key === 'ArrowUp' ||
                event.key === 'ArrowDown' ||
                event.key === 'ArrowLeft' ||
                event.key === 'ArrowRight'
            ) {
                joystick.right_x = 0;
                joystick.left_y = 0;
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    })
</script>