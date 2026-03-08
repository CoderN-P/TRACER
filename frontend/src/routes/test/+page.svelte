<script lang="ts">
  import PathDrawer from "$lib/components/PathDrawer.svelte";

  let robotPos = $state<{ x: number; y: number; theta: number } | null>({
    x: 3,
    y: 0,
    theta: Math.PI / 2,
  });
  let freehandPath = $state<{ x: number; y: number }[]>([]);
  let pathComplete = $state(false);

  function handleRunPath(pts: { x: number; y: number }[]) {
    console.log("Run path:", pts);
    pathComplete = false;
    // TODO: socket.emit('run_path', pts);
    // Simulate completion after 5s for testing
    setTimeout(() => {
      pathComplete = true;
    }, 5000);
  }
</script>

<div class="p-4">
  <h1 class="text-2xl font-bold mb-4">Test Page</h1>
  
    <PathDrawer
      {robotPos}
      {pathComplete}
      onRunPath={handleRunPath}
      bind:freehandPath
    />
  {#if freehandPath.length > 0}
    <p class="mt-2 text-xs text-gray-500">
      Freehand path: {freehandPath.length} points &nbsp;·&nbsp; first ({freehandPath[0].x.toFixed(
        3,
      )}, {freehandPath[0].y.toFixed(3)}) m &nbsp;·&nbsp; last ({freehandPath[
        freehandPath.length - 1
      ].x.toFixed(3)}, {freehandPath[freehandPath.length - 1].y.toFixed(3)}) m
    </p>
  {/if}
</div>
