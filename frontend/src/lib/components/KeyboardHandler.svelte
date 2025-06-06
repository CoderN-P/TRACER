<script lang="ts">
    import { type Joystick } from '$lib/types';
    import { onMount } from 'svelte';
    
    let { joystick = $bindable(), inputFocus } : { joystick: Joystick, inputFocus: boolean } = $props();
    
    onMount(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (inputFocus) {
                return; // Ignore key events if input is focused
            }
            if (event.key === 'ArrowUp') {
                event.preventDefault();
                joystick.left_y = -1;
            } else if (event.key === 'ArrowDown') {
                event.preventDefault();
                joystick.left_y = 1;
            } else if (event.key === 'ArrowLeft') {
                event.preventDefault();
                joystick.right_x = -1;
            } else if (event.key === 'ArrowRight') {
                event.preventDefault();
                joystick.right_x = 1;
            }
        };

        const handleKeyUp = (event: KeyboardEvent) => {
            event.preventDefault();
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