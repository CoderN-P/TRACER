<script lang="ts">
    import { Send, LoaderCircle } from 'lucide-svelte';
    
    let { query = $bindable(), onSubmit, inputFocus = $bindable(), loading }: { query: string, onSubmit: (e) => void, inputFocus: boolean, loading: boolean } = $props();
    
</script>


<div class="w-full rounded-lg bg-white flex flex-row border border-gray-100 p-2 pl-4">
    <input 
        type="text"
        class="w-full bg-transparent outline-none text-gray-800 placeholder:text-gray-400"
        placeholder="Enter command..."
        bind:value={query}
        bind:focused={inputFocus}
        onkeydown={(e) => {
            if (e.key === 'Enter') {
                onSubmit(e);
            }
        }}
    />
    <button 
        class="ml-2 p-2 rounded-md  text-gray-500 hover:bg-gray-100 transition-colors"
        onclick={(e) => onSubmit(e)}
        disabled={loading || query.trim() === ''}
    >
        {#if loading}
            <LoaderCircle class="w-5 h-5 animate-spin" />
        {:else}
            <Send class="w-5 h-5" />
        {/if}
    </button>
</div>