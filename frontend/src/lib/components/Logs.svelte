<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { Skeleton } from "$lib/components/ui/skeleton";
  import { type LogEntry } from "$lib/types";
  import LogEntryDisplay from "./LogEntryDisplay.svelte";
  import {
    List,
    Filter,
    CheckCircle2,
    AlertTriangle,
    Info,
    XCircle,
    ArrowDownToLine,
    Search,
  } from "lucide-svelte";
  import { scale, fly, fade } from "svelte/transition";
  import { quintOut } from "svelte/easing";

  let { logs, class: className = "" }: { logs: LogEntry[]; class?: string } =
    $props();
  let logElement: HTMLElement | null = null;
  let searchTerm = $state("");
  let activeFilter = $state<string | null>(null);

  // Compute filtered logs based on search term and active filter
  const filteredLogs = $derived.by(() => {
    return logs.filter((log) => {
      // Apply search filter if search term exists
      const matchesSearch =
        searchTerm === "" ||
        log.message.toLowerCase().includes(searchTerm.toLowerCase());

      // Apply type filter if active
      const matchesFilter = !activeFilter || log.icon === activeFilter;

      return matchesSearch && matchesFilter;
    });
  });

  // Calculate counts for each log type
  const logCounts = $derived(() => {
    const counts = {
      warning: logs.filter((log) => log.icon === "warning").length,
      check: logs.filter((log) => log.icon === "check").length,
      info: logs.filter((log) => log.icon === "info").length,
      error: logs.filter((log) => log.icon === "error").length,
    };
    return counts;
  });

  // Toggle filter function
  function toggleFilter(filter: string) {
    if (activeFilter === filter) {
      activeFilter = null; // Deactivate filter if already active
    } else {
      activeFilter = filter; // Activate this filter
    }
  }

  // Clear search and filters
  function clearFilters() {
    searchTerm = "";
    activeFilter = null;
  }

  $effect(() => {
    // Scroll to the latest log entry when logs change
    if (logElement && !searchTerm && !activeFilter) {
      // Use a small timeout to ensure DOM is updated before scrolling
      setTimeout(() => {
        logElement.scrollTop = logElement.scrollHeight;
      }, 50);
    }
  });
</script>

{#if !logs || logs.length === 0}
  <Skeleton class="w-full h-50 rounded-sm" />
{:else}
  <Card.Root class="w-full h-full md:w-1/2 " style="height: 435px;">
    <Card.Header>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <List class="w-5 h-5 text-gray-600" />
          <Card.Title>System Logs</Card.Title>
        </div>

        <div class="text-xs text-gray-500">
          {logs.length} entries
        </div>
      </div>

      <div class="mt-2 flex flex-col sm:flex-row gap-2 sm:items-center">
        <!-- Search input -->
        <div class="relative flex-grow">
          <div
            class="absolute inset-y-0 left-0 pl-2 flex items-center pointer-events-none"
          >
            <Search class="h-4 w-4 text-gray-400" />
          </div>
          <input
            type="text"
            placeholder="Search logs..."
            class="pl-8 pr-4 py-1 h-8 w-full text-sm rounded-md border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            bind:value={searchTerm}
          />
          {#if searchTerm}
            <button
              class="absolute inset-y-0 right-0 pr-2 flex items-center text-gray-400 hover:text-gray-600"
              onclick={() => (searchTerm = "")}
            >
              <XCircle class="h-4 w-4" />
            </button>
          {/if}
        </div>

        <!-- Filter buttons -->
        <div class="flex items-center gap-1 flex-shrink-0">
          <button
            class="flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors
                                   {activeFilter === null
              ? 'bg-gray-200 text-gray-700'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}"
            onclick={clearFilters}
          >
            <Filter class="h-3 w-3" />
            <span>All</span>
          </button>

          <button
            class="flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors
                                   {activeFilter === 'warning'
              ? 'bg-yellow-100 text-yellow-700'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}"
            onclick={() => toggleFilter("warning")}
          >
            <AlertTriangle class="h-3 w-3" />
            <span>{logCounts.warning}</span>
          </button>

          <button
            class="flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors
                                   {activeFilter === 'check'
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}"
            onclick={() => toggleFilter("check")}
          >
            <CheckCircle2 class="h-3 w-3" />
            <span>{logCounts.check}</span>
          </button>

          <button
            class="flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors
                                   {activeFilter === 'info'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}"
            onclick={() => toggleFilter("info")}
          >
            <Info class="h-3 w-3" />
            <span>{logCounts.info}</span>
          </button>

          <button
            class="flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors
                                   {activeFilter === 'error'
              ? 'bg-red-100 text-red-700'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'}"
            onclick={() => toggleFilter("error")}
          >
            <XCircle class="h-3 w-3" />
            <span>{logCounts.error}</span>
          </button>
        </div>
      </div>
    </Card.Header>

    <div class="relative">
      {#if searchTerm || activeFilter}
        <button
          class="absolute top-0 right-4 mt-2 z-10 flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 text-blue-600 rounded-md hover:bg-blue-200 transition-colors"
          onclick={clearFilters}
          transition:scale={{ duration: 150 }}
        >
          <span>Clear filters</span>
          <XCircle class="h-3 w-3" />
        </button>
      {/if}

      <Card.Content
        bind:this={logElement}
        class="flex flex-col-reverse overflow-y-auto overflow-x-hidden w-full gap-0.5 px-3 sm:px-4 py-2 pb-4 max-h-[300px] md:max-h-[250px]"
      >
        {#if filteredLogs.length === 0}
          <div
            class="flex flex-col items-center justify-center py-8 text-gray-400"
            in:fade
          >
            <Search class="h-8 w-8 mb-2 opacity-50" />
            <p class="text-sm">No matching logs found</p>
            {#if searchTerm || activeFilter}
              <button
                class="mt-2 text-xs text-blue-500 hover:underline"
                onclick={clearFilters}
              >
                Clear filters
              </button>
            {/if}
          </div>
        {:else}
          {#each filteredLogs as log, i (log.timestamp)}
            <div in:fly={{ y: 5, duration: 150, delay: i < 5 ? i * 50 : 0 }}>
              <LogEntryDisplay {log} />
            </div>
          {/each}
        {/if}

        {#if logs.length > 10 && !searchTerm && !activeFilter}
          <div
            class="sticky top-0 w-full flex justify-center py-1 z-10"
            in:fade={{ duration: 200 }}
          >
            <div
              class="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 text-gray-500 rounded-full"
            >
              <ArrowDownToLine class="h-3 w-3" />
              <span>Newest logs at bottom</span>
            </div>
          </div>
        {/if}
      </Card.Content>
    </div>
  </Card.Root>
{/if}

<style>
  .container {
    -ms-overflow-style: none; /* Internet Explorer 10+ */
    scrollbar-width: none; /* Firefox */
  }
  .container::-webkit-scrollbar {
    display: none; /* Safari and Chrome */
  }

  /* Customized scrollbar for logs */
  :global(.card-content::-webkit-scrollbar) {
    width: 6px;
  }

  :global(.card-content::-webkit-scrollbar-track) {
    background: #f1f1f1;
    border-radius: 10px;
  }

  :global(.card-content::-webkit-scrollbar-thumb) {
    background: #d1d1d1;
    border-radius: 10px;
  }

  :global(.card-content::-webkit-scrollbar-thumb:hover) {
    background: #b1b1b1;
  }
</style>
