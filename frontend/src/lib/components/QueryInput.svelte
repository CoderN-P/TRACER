<script lang="ts">
    import { Send, LoaderCircle } from 'lucide-svelte';
    
    let { 
        query = $bindable(), 
        onSubmit, 
        inputFocus = $bindable(), 
        loading, 
        class: className = '' 
    }: { 
        query: string, 
        onSubmit: (e) => void, 
        inputFocus: boolean, 
        loading: boolean,
        class?: string
    } = $props();
    
</script>


<div class="w-full rounded-lg bg-white flex flex-row border border-gray-100 p-2 pl-4 {className}">
    <input 
        type="text"
        class="w-full bg-transparent outline-none text-gray-800 placeholder:text-gray-400
               text-base sm:text-base min-h-[40px]"
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
        class="ml-2 p-2 sm:p-2.5 rounded-md text-gray-500 hover:bg-gray-100 
               transition-colors min-w-[40px] min-h-[40px]
               active:bg-gray-200 touch-manipulation"
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