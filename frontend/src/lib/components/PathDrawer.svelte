<script lang="ts">
  import { browser } from "$app/environment";
  import {
    PlusIcon,
    Trash,
    PenLine,
    Spline,
    X,
    Play,
    StopCircle,
  } from "lucide-svelte";
  import { Stage, Layer, Line, Circle, Text } from "svelte-konva";
  import {
    QuinticHermiteSplineSvelte,
    SplinePathSvelte,
  } from "$lib/types/index.js";

  export type RunPathPayload =
    | { type: "freehand"; path: { x: number; y: number }[] }
    | {
        type: "spline";
        path: ReturnType<SplinePathSvelte["exportToJSON"]>;
      }
    | { type: "point"; path: { x: number; y: number } };

  /** Robot position in meters, updated at ~10 Hz. Pass null to hide the robot. */
  let {
    robotPos = null,
    freehandPath: freehandPathProp = $bindable([]),
    pathComplete = false,
    onRunPath = (_payload: RunPathPayload) => {},
    onStopRun = () => {},
  }: {
    robotPos?: { x: number; y: number; theta: number } | null;
    freehandPath?: { x: number; y: number }[];
    /** Set to true by the parent when the robot confirms path completion. */
    pathComplete?: boolean;
    /** Called with the typed path payload when the run button is pressed. */
    onRunPath?: (payload: RunPathPayload) => void;
    /** Called when the user presses Stop while a run is active. */
    onStopRun?: () => void;
  } = $props();

  let path = new SplinePathSvelte();

  // Canvas dimensions — WIDTH tracks the container element width reactively.
  let containerEl = $state<HTMLDivElement | null>(null);
  let WIDTH = $state(800);
  const ASPECT = 0.5; // height = WIDTH * ASPECT
  let HEIGHT = $derived(Math.round(WIDTH * ASPECT));
  const GRID_SPACING = 100; // pixels between grid lines (in world pixels at zoom=1)
  const TICK_LENGTH = 10; // length of axis ticks
  const PATH_RENDER_INTERVAL = 0.01; // seconds (dt)
  const SCALE = 100; // pixels per meter

  $effect(() => {
    if (!containerEl) return;
    const ro = new ResizeObserver(([entry]) => {
      const w = Math.floor(entry.contentRect.width);
      if (w > 0 && w !== WIDTH) {
        // Keep the camera origin centred after resize.
        const dx = (w - WIDTH) / 2;
        const dh = (Math.round(w * ASPECT) - HEIGHT) / 2;
        stageX += dx;
        stageY += dh;
        WIDTH = w;
      }
    });
    ro.observe(containerEl);
    return () => ro.disconnect();
  });

  // Pan & zoom state — default to origin at canvas center
  let stageX = $state(WIDTH / 2);
  let stageY = $state(HEIGHT / 2);
  let zoom = $state(1);
  let stageNode = $state(null);

  const MIN_ZOOM = 0.2;
  const MAX_ZOOM = 8;
  const ZOOM_SENSITIVITY = 1.1;

  function handleWheel(e) {
    e.evt.preventDefault();
    const stage = e.target.getStage();
    const oldZoom = zoom;
    const pointer = stage.getPointerPosition();

    // Pointer in world coords before zoom
    const mousePointTo = {
      x: (pointer.x - stageX) / oldZoom,
      y: (pointer.y - stageY) / oldZoom,
    };

    const direction = e.evt.deltaY < 0 ? 1 : -1;
    const newZoom = Math.min(
      MAX_ZOOM,
      Math.max(
        MIN_ZOOM,
        oldZoom * (direction > 0 ? ZOOM_SENSITIVITY : 1 / ZOOM_SENSITIVITY),
      ),
    );
    zoom = newZoom;

    // Adjust pan so zoom focuses on cursor
    stageX = pointer.x - mousePointTo.x * newZoom;
    stageY = pointer.y - mousePointTo.y * newZoom;
  }

  function handleDragEnd(e) {
    if (e.target === e.target.getStage()) {
      stageX = e.target.x();
      stageY = e.target.y();
    }
  }

  // Extended grid that covers a large virtual canvas so it appears infinite while panning
  const VIRTUAL_SIZE = 8000;

  function getGridLines(spacing) {
    let lines = [];
    for (let x = -VIRTUAL_SIZE; x <= VIRTUAL_SIZE; x += spacing) {
      lines.push({ points: [x, -VIRTUAL_SIZE, x, VIRTUAL_SIZE] });
    }
    for (let y = -VIRTUAL_SIZE; y <= VIRTUAL_SIZE; y += spacing) {
      lines.push({ points: [-VIRTUAL_SIZE, y, VIRTUAL_SIZE, y] });
    }
    return lines;
  }

  function getAxisTicks(spacing, tickLength) {
    let ticks = [];
    for (let x = -VIRTUAL_SIZE; x <= VIRTUAL_SIZE; x += spacing) {
      ticks.push({
        x1: x,
        y1: -tickLength / 2,
        x2: x,
        y2: tickLength / 2,
        label: (x / SCALE).toFixed(1),
      });
    }
    for (let y = -VIRTUAL_SIZE; y <= VIRTUAL_SIZE; y += spacing) {
      ticks.push({
        x1: -tickLength / 2,
        y1: y,
        x2: tickLength / 2,
        y2: y,
        label: (-y / SCALE).toFixed(1),
      });
    }
    return ticks;
  }

  let gridLines = $derived(getGridLines(GRID_SPACING));
  let axisTicks = $derived(getAxisTicks(GRID_SPACING, TICK_LENGTH));

  // ── Robot interpolation ──────────────────────────────────────────────────
  // Sensor updates arrive at 10 Hz (every 100 ms). We lerp between the last
  // known position and the newly received one over that same 100 ms window so
  // the dot moves smoothly instead of snapping.
  const LERP_DURATION = 100; // ms — matches the 10 Hz sensor interval

  let displayRobotPos = $state<{ x: number; y: number; theta: number } | null>(
    null,
  );
  let lerpFrom = $state<{ x: number; y: number; theta: number } | null>(null);
  let lerpTo = $state<{ x: number; y: number; theta: number } | null>(null);
  let lerpStart = 0;
  let rafId: number | null = null;

  function lerp(a: number, b: number, t: number) {
    return a + (b - a) * Math.min(t, 1);
  }

  /** Interpolate between two angles using the shortest arc. */
  function lerpAngle(a: number, b: number, t: number) {
    let diff = ((b - a + Math.PI) % (2 * Math.PI)) - Math.PI;
    if (diff < -Math.PI) diff += 2 * Math.PI;
    return a + diff * Math.min(t, 1);
  }

  function tickLerp(timestamp: number) {
    if (!lerpFrom || !lerpTo) return;
    const t = (timestamp - lerpStart) / LERP_DURATION;
    displayRobotPos = {
      x: lerp(lerpFrom.x, lerpTo.x, t),
      y: lerp(lerpFrom.y, lerpTo.y, t),
      theta: lerpAngle(lerpFrom.theta, lerpTo.theta, t),
    };
    if (t < 1) {
      rafId = requestAnimationFrame(tickLerp);
    } else {
      displayRobotPos = { ...lerpTo };
      rafId = null;
    }
  }

  $effect(() => {
    if (robotPos == null) {
      displayRobotPos = null;
      return;
    }
    // Cancel any in-progress lerp and start a new one from the current display pos
    if (rafId !== null) cancelAnimationFrame(rafId);
    lerpFrom = displayRobotPos ?? { ...robotPos };
    lerpTo = { ...robotPos };
    lerpStart = performance.now();
    rafId = requestAnimationFrame(tickLerp);
    return () => {
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  });

  // ── Mode ──────────────────────────────────────────────────────────────────
  type Mode = "spline" | "freehand" | "point";
  let mode = $state<Mode>("spline");

  // ── Point mode ────────────────────────────────────────────────────────────
  let selectedPoint = $state<{ x: number; y: number } | null>(null);

  // ── Freehand drawing ──────────────────────────────────────────────────────
  // Raw canvas-pixel points captured during a stroke (in world pixels).
  let rawStroke = $state<{ x: number; y: number }[]>([]);
  // Finalised resampled path — array of {x,y} in METERS, 1 cm apart.
  let freehandPath = $state<{ x: number; y: number }[]>([]);
  let isDrawing = $state(false);

  // Keep bindable prop in sync
  $effect(() => {
    freehandPathProp = freehandPath;
  });

  /** Convert a stage-pointer position to world-pixel coords. */
  function pointerToWorld(stage): { x: number; y: number } {
    const p = stage.getPointerPosition();
    return {
      x: (p.x - stageX) / zoom,
      y: (p.y - stageY) / zoom,
    };
  }

  /**
   * Resample a polyline so consecutive points are exactly `step` apart.
   * Points are in world pixels; `step` is in world pixels too.
   */
  function resamplePolyline(
    pts: { x: number; y: number }[],
    step: number,
  ): { x: number; y: number }[] {
    if (pts.length < 2) return pts.length === 1 ? [{ ...pts[0] }] : [];
    const result: { x: number; y: number }[] = [{ ...pts[0] }];
    let carry = 0; // leftover distance from previous segment
    for (let i = 1; i < pts.length; i++) {
      const dx = pts[i].x - pts[i - 1].x;
      const dy = pts[i].y - pts[i - 1].y;
      const segLen = Math.sqrt(dx * dx + dy * dy);
      if (segLen === 0) continue;
      let dist = carry + segLen;
      let offset = step - carry; // distance along this segment to the first new point
      while (offset <= segLen) {
        const t = offset / segLen;
        result.push({
          x: pts[i - 1].x + t * dx,
          y: pts[i - 1].y + t * dy,
        });
        offset += step;
      }
      carry = segLen - (offset - step); // remaining distance in this segment
    }
    return result;
  }

  function freehandMouseDown(e) {
    if (mode !== "freehand" || running) return;
    // Only draw on left mouse button
    if (e.evt.button !== 0) return;
    isDrawing = true;
    const world = pointerToWorld(e.target.getStage());
    rawStroke = [world];
  }

  function freehandMouseMove(e) {
    if (mode !== "freehand" || !isDrawing || running) return;
    const world = pointerToWorld(e.target.getStage());
    const last = rawStroke[rawStroke.length - 1];
    const dx = world.x - last.x;
    const dy = world.y - last.y;
    // Only append if moved at least 2px to avoid redundant points
    if (dx * dx + dy * dy > 4) {
      rawStroke = [...rawStroke, world];
    }
  }

  function freehandMouseUp(e) {
    if (mode !== "freehand" || !isDrawing) return;
    isDrawing = false;
    if (rawStroke.length < 2) {
      rawStroke = [];
      return;
    }
    // Resample to 1 cm = 0.01 m = SCALE * 0.01 world pixels
    const stepPx = SCALE * 0.01;
    const resampled = resamplePolyline(rawStroke, stepPx);
    // Convert world pixels → meters and store
    freehandPath = resampled.map((p) => ({ x: p.x / SCALE, y: -p.y / SCALE }));
    rawStroke = [];
  }

  function pointModeClick(e) {
    if (mode !== "point" || running) return;
    // Only select on left mouse button
    if (e.evt.button !== 0) return;
    const world = pointerToWorld(e.target.getStage());
    // Convert world pixels → meters
    selectedPoint = { x: world.x / SCALE, y: -world.y / SCALE };
  }

  /** Flat array of world-pixel coords for rendering the live stroke. */
  let rawStrokePoints = $derived(rawStroke.flatMap((p) => [p.x, p.y]));

  /** Flat array of world-pixel coords for rendering the finalised freehand path. */
  let freehandPathPoints = $derived(
    freehandPath.flatMap((p) => [p.x * SCALE, -p.y * SCALE]),
  );

  // ── Run mode ──────────────────────────────────────────────────────────────
  // When running, we record which type of path is active and a UI offset so
  // the path appears to start at the robot's current position (display only).
  type RunSource = "spline" | "freehand" | "point";
  let running = $state(false);
  let runSource = $state<RunSource>("spline");
  // Offset in meters applied only for rendering while running.
  let runOffsetX = $state(0);
  let runOffsetY = $state(0);

  /** True when the active mode has a drawable path ready. */
  let canRun = $derived(
    mode === "spline"
      ? path.QuinticHermiteSplines.length > 0
      : mode === "freehand"
        ? freehandPath.length > 0
        : mode === "point"
          ? selectedPoint !== null
          : false,
  );

  function startRun() {
    if (!canRun) return;
    runSource = mode;
    // Shift the path so its first point coincides with the robot's current pos.
    if (displayRobotPos !== null) {
      if (runSource === "freehand" && freehandPath.length > 0) {
        runOffsetX = displayRobotPos.x - freehandPath[0].x;
        runOffsetY = displayRobotPos.y - freehandPath[0].y;

        // Set camera to center on robot for freehand mode since the path can start anywhere
        stageX = WIDTH / 2 - displayRobotPos.x * SCALE * zoom;
        stageY = HEIGHT / 2 + displayRobotPos.y * SCALE * zoom;
      } else if (
        runSource === "spline" &&
        path.QuinticHermiteSplines.length > 0
      ) {
        const firstSpline = path.QuinticHermiteSplines[0];
        runOffsetX = displayRobotPos.x - firstSpline.x0;
        runOffsetY = displayRobotPos.y - firstSpline.y0;

        // Center camera on robot for spline mode as well, since the path always starts at the first control point which may be far from the canvas center
        stageX = WIDTH / 2 - displayRobotPos.x * SCALE * zoom;
        stageY = HEIGHT / 2 + displayRobotPos.y * SCALE * zoom;
      } else if (runSource === "point" && selectedPoint !== null) {
        runOffsetX = displayRobotPos.x - selectedPoint.x;
        runOffsetY = displayRobotPos.y - selectedPoint.y;

        // Center camera on robot for point mode
        stageX = WIDTH / 2 - displayRobotPos.x * SCALE * zoom;
        stageY = HEIGHT / 2 + displayRobotPos.y * SCALE * zoom;
      }
    } else {
      runOffsetX = 0;
      runOffsetY = 0;
    }
    running = true;

    // Build a typed payload and hand it off to the parent.
    let payload: RunPathPayload;
    if (runSource === "freehand") {
      payload = {
        type: "freehand",
        path: freehandPath.map((p) => ({
          x: p.x + runOffsetX,
          y: p.y + runOffsetY,
        })),
      };
    } else if (runSource === "spline") {
      // Export the spline definition (control points + derivatives) directly —
      // no need to pre-sample; the RPi can integrate at its own resolution.
      const splineJSON = path.exportToJSON();
      // Apply run offset to every spline's start/end positions.
      payload = {
        type: "spline",
        path: {
          splines: splineJSON.splines.map((s) => ({
            ...s,
            start: [s.start[0] + runOffsetX, s.start[1] + runOffsetY] as [
              number,
              number,
            ],
            end: [s.end[0] + runOffsetX, s.end[1] + runOffsetY] as [
              number,
              number,
            ],
          })),
        },
      };
    } else {
      // Point mode
      payload = {
        type: "point",
        path: {
          x: (selectedPoint?.x ?? 0) + runOffsetX,
          y: (selectedPoint?.y ?? 0) + runOffsetY,
        },
      };
    }
    onRunPath(payload);
  }

  function stopRun(notifyParent = true) {
    running = false;
    runOffsetX = 0;
    runOffsetY = 0;
    if (notifyParent) onStopRun();
  }

  // Exit run mode automatically when parent signals completion.
  $effect(() => {
    if (pathComplete && running) stopRun(false);
  });

  /** Freehand render points shifted by the run offset (world pixels). */
  let runFreehandPoints = $derived(
    running && runSource === "freehand"
      ? freehandPath.flatMap((p) => [
          (p.x + runOffsetX) * SCALE,
          -(p.y + runOffsetY) * SCALE,
        ])
      : freehandPathPoints,
  );
</script>

{#if !browser}
  <p>Loading...</p>
{:else}
  <div
    class="rounded-lg border border-gray-200 p-4 bg-white flex flex-col select-none"
  >
    <!-- Toolbar -->
    <div class="flex flex-row items-center gap-2 mb-4 flex-wrap">
      <!-- Mode toggle -->
      <div class="flex rounded-md overflow-hidden border border-gray-200">
        <button
          onclick={() => {
            mode = "spline";
          }}
          disabled={running}
          class="flex items-center gap-1 px-3 py-2 text-xs transition-colors {mode ===
          'spline'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-50 text-black hover:bg-gray-100'} disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Spline class="w-3.5 h-3.5" /> Spline
        </button>
        <button
          onclick={() => {
            mode = "freehand";
          }}
          disabled={running}
          class="flex items-center gap-1 px-3 py-2 text-xs transition-colors border-l border-gray-200 {mode ===
          'freehand'
            ? 'bg-orange-500 text-white'
            : 'bg-gray-50 text-black hover:bg-gray-100'} disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <PenLine class="w-3.5 h-3.5" /> Freehand
        </button>
        <button
          onclick={() => {
            mode = "point";
          }}
          disabled={running}
          class="flex items-center gap-1 px-3 py-2 text-xs transition-colors border-l border-gray-200 {mode ===
          'point'
            ? 'bg-purple-600 text-white'
            : 'bg-gray-50 text-black hover:bg-gray-100'} disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <PlusIcon class="w-3.5 h-3.5" /> Point
        </button>
      </div>

      <!-- Spline-mode controls -->
      {#if mode === "spline"}
        <button
          onclick={() => path.QuinticHermiteSplines.pop()}
          class="p-2 bg-gray-50 flex items-center text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
          title="Remove last spline"
        >
          <Trash class="w-4 h-4" />
        </button>
        <button
          onclick={() =>
            path.addSpline(
              new QuinticHermiteSplineSvelte(
                path.QuinticHermiteSplines.length > 0
                  ? path.QuinticHermiteSplines[
                      path.QuinticHermiteSplines.length - 1
                    ].x1
                  : 0,
                path.QuinticHermiteSplines.length > 0
                  ? path.QuinticHermiteSplines[
                      path.QuinticHermiteSplines.length - 1
                    ].y1
                  : 0,
                path.QuinticHermiteSplines.length > 0
                  ? path.QuinticHermiteSplines[
                      path.QuinticHermiteSplines.length - 1
                    ].dx1
                  : 1,
                path.QuinticHermiteSplines.length > 0
                  ? path.QuinticHermiteSplines[
                      path.QuinticHermiteSplines.length - 1
                    ].dy1
                  : 0,
                path.QuinticHermiteSplines.length > 0
                  ? path.QuinticHermiteSplines[
                      path.QuinticHermiteSplines.length - 1
                    ].ddx1
                  : 0,
                path.QuinticHermiteSplines.length > 0
                  ? path.QuinticHermiteSplines[
                      path.QuinticHermiteSplines.length - 1
                    ].ddy1
                  : 1,
                (path.QuinticHermiteSplines.length > 0
                  ? path.QuinticHermiteSplines[
                      path.QuinticHermiteSplines.length - 1
                    ].x1
                  : 0) + 1,
                (path.QuinticHermiteSplines.length > 0
                  ? path.QuinticHermiteSplines[
                      path.QuinticHermiteSplines.length - 1
                    ].y1
                  : 0) + 1,
                0.5,
                0,
                0,
                0.5,
              ),
            )}
          class="p-2 bg-gray-50 flex items-center text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
          title="Add spline segment"
        >
          <PlusIcon class="w-4 h-4" />
        </button>
      {/if}

      <!-- Freehand-mode controls -->
      {#if mode === "freehand"}
        <button
          onclick={() => {
            freehandPath = [];
            rawStroke = [];
          }}
          class="flex items-center gap-1 px-3 py-2 text-xs bg-gray-50 text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
          title="Clear freehand path"
        >
          <X class="w-3.5 h-3.5" /> Clear
        </button>
        <span class="text-xs text-gray-400">
          {freehandPath.length} pts &nbsp;·&nbsp; drag to pan disabled while drawing
        </span>
      {/if}

      <!-- Point-mode controls -->
      {#if mode === "point"}
        <button
          onclick={() => {
            selectedPoint = null;
          }}
          class="flex items-center gap-1 px-3 py-2 text-xs bg-gray-50 text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
          title="Clear selected point"
        >
          <X class="w-3.5 h-3.5" /> Clear
        </button>
        <span class="text-xs text-gray-400">
          {selectedPoint
            ? `(${selectedPoint.x.toFixed(2)}, ${selectedPoint.y.toFixed(2)})`
            : "Click to select point"}
        </span>
      {/if}

      <div class="ml-auto flex items-center gap-2">
        {#if !running}
          <button
            onclick={startRun}
            disabled={!canRun}
            class="flex items-center gap-1.5 px-3 py-2 text-xs rounded-md transition-colors {canRun
              ? 'bg-green-600 hover:bg-green-700 text-white'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'}"
            title={canRun ? "Send path to robot" : "Draw a path first"}
          >
            <Play class="w-3.5 h-3.5" /> Run
          </button>
        {:else}
          <button
            onclick={() => stopRun()}
            class="flex items-center gap-1.5 px-3 py-2 text-xs rounded-md bg-red-600 hover:bg-red-700 text-white transition-colors"
          >
            <StopCircle class="w-3.5 h-3.5" /> Stop
          </button>
        {/if}
        <button
          onclick={() => {
            stageX = WIDTH / 2;
            stageY = HEIGHT / 2;
            zoom = 1;
          }}
          class="p-2 bg-gray-50 flex items-center text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors text-xs px-3 whitespace-nowrap"
        >
          Reset View
        </button>
        <span class="text-xs text-gray-400 whitespace-nowrap"
          >Scroll to zoom{mode === "spline" && !running
            ? " · Drag to pan"
            : ""}</span
        >
      </div>
    </div>

    <!-- Run-mode status banner -->
    {#if running}
      <div
        class="mb-2 flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium
        {pathComplete
          ? 'bg-green-50 text-green-700 border border-green-200'
          : 'bg-amber-50 text-amber-700 border border-amber-200'}"
      >
        {#if pathComplete}
          ✓ Path complete
        {:else}
          <span
            class="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"
          ></span>
          Running {runSource} path… waiting for robot confirmation
        {/if}
      </div>
    {/if}

    <div
      bind:this={containerEl}
      style="cursor: {mode === 'freehand'
        ? isDrawing
          ? 'crosshair'
          : 'crosshair'
        : mode === 'point'
          ? 'crosshair'
          : 'default'}"
    >
      <Stage
        width={WIDTH}
        height={HEIGHT}
        x={stageX}
        y={stageY}
        scaleX={zoom}
        scaleY={zoom}
        draggable={mode === "spline" && !running}
        onwheel={handleWheel}
        ondragend={handleDragEnd}
        onmousedown={(e) => {
          if (mode === "point") {
            pointModeClick(e);
          } else {
            freehandMouseDown(e);
          }
        }}
        onmousemove={freehandMouseMove}
        onmouseup={freehandMouseUp}
        onmouseleave={freehandMouseUp}
      >
        <!-- Grid & axes -->
        <Layer>
          {#each gridLines as line}
            <Line points={line.points} stroke="#eee" strokeWidth={1 / zoom} />
          {/each}
          <!-- X axis -->
          <Line
            points={[-VIRTUAL_SIZE, 0, VIRTUAL_SIZE, 0]}
            stroke="#aaa"
            strokeWidth={1.5 / zoom}
          />
          <!-- Y axis -->
          <Line
            points={[0, -VIRTUAL_SIZE, 0, VIRTUAL_SIZE]}
            stroke="#aaa"
            strokeWidth={1.5 / zoom}
          />
          {#each axisTicks as tick}
            <Line
              points={[tick.x1, tick.y1, tick.x2, tick.y2]}
              stroke="#888"
              strokeWidth={1 / zoom}
            />
            <Text
              x={tick.x2 + 2 / zoom}
              y={tick.y2 + 2 / zoom}
              text={tick.label}
              fontSize={9 / zoom}
              fill="#888"
            />
          {/each}
        </Layer>

        <!-- Spline path — hidden during freehand run -->
        {#if !running || runSource === "spline"}
          <Layer>
            {#if running && runSource === "spline"}
              <!-- Offset the spline visually so it starts at robot pos -->
              <Line
                points={path
                  .render(PATH_RENDER_INTERVAL, SCALE, WIDTH, HEIGHT)
                  .map((v, i) =>
                    i % 2 === 0
                      ? v + runOffsetX * SCALE
                      : v - runOffsetY * SCALE,
                  )}
                stroke="#0EA5E9"
                strokeWidth={3 / zoom}
                closed={false}
              />
            {:else}
              <Line
                points={path.render(PATH_RENDER_INTERVAL, SCALE, WIDTH, HEIGHT)}
                stroke="#0EA5E9"
                strokeWidth={3.5 / zoom}
                closed={false}
              />
            {/if}
          </Layer>
        {/if}

        <!-- Control lines — hidden while running -->
        {#if !running}
          {#each path.getControlLines(SCALE, WIDTH, HEIGHT) as cl}
            <Layer>
              <Line
                points={[cl.x1, cl.y1, cl.x2, cl.y2]}
                stroke="gray"
                strokeWidth={1 / zoom}
                dash={[4 / zoom, 4 / zoom]}
              />
              <Text
                x={(cl.x1 + cl.x2) / 2}
                y={(cl.y1 + cl.y2) / 2}
                text={cl.label}
                fontSize={12 / zoom}
                fill="gray"
              />
            </Layer>
          {/each}
        {/if}

        <!-- Control points — hidden while running -->
        {#if !running}
          {#each path.getControlPoints(SCALE, WIDTH, HEIGHT) as cp, idx}
            <Layer>
              <Circle
                x={cp.x}
                y={cp.y}
                radius={5 / zoom}
                fill="blue"
                stroke="white"
                strokeWidth={1.5 / zoom}
                draggable
                ondragstart={(e) => e.target.getStage().draggable(false)}
                ondragend={(e) => e.target.getStage().draggable(true)}
                ondragmove={(e) =>
                  path.updateControlPoint(
                    idx,
                    e.target.position().x,
                    e.target.position().y,
                    SCALE,
                    WIDTH,
                    HEIGHT,
                  )}
              />
            </Layer>
          {/each}
        {/if}

        <!-- Freehand finalised path — hidden during spline run -->
        {#if (!running || runSource === "freehand") && runFreehandPoints.length >= 4}
          <Layer>
            <Line
              points={runFreehandPoints}
              stroke="#ea580c"
              strokeWidth={2 / zoom}
              closed={false}
              lineCap="round"
              lineJoin="round"
            />
          </Layer>
        {/if}

        <!-- Freehand live stroke (while drawing) — hidden while running -->
        {#if !running && rawStrokePoints.length >= 4}
          <Layer>
            <Line
              points={rawStrokePoints}
              stroke="#fb923c"
              strokeWidth={2 / zoom}
              closed={false}
              lineCap="round"
              lineJoin="round"
              opacity={0.6}
            />
          </Layer>
        {/if}

        <!-- Selected point (point mode) — hidden while running -->
        {#if !running && mode === "point" && selectedPoint !== null}
          {@const px = selectedPoint.x * SCALE}
          {@const py = -selectedPoint.y * SCALE}
          <Layer>
            <Circle
              x={px}
              y={py}
              radius={8 / zoom}
              fill="#a855f7"
              stroke="white"
              strokeWidth={2 / zoom}
            />
            <Text
              x={px + 12 / zoom}
              y={py - 8 / zoom}
              text={`(${selectedPoint.x.toFixed(2)}, ${selectedPoint.y.toFixed(2)})`}
              fontSize={10 / zoom}
              fill="#a855f7"
            />
          </Layer>
        {/if}

        <!-- Robot position -->
        {#if displayRobotPos !== null}
          {@const cx = displayRobotPos.x * SCALE}
          {@const cy = -displayRobotPos.y * SCALE}
          {@const arrowLen = 18}
          {@const tipX =
            cx + (Math.cos(displayRobotPos.theta) * arrowLen) / zoom}
          {@const tipY =
            cy - (Math.sin(displayRobotPos.theta) * arrowLen) / zoom}
          <Layer>
            <!-- Outer ring -->
            <Circle
              x={cx}
              y={cy}
              radius={10 / zoom}
              stroke="#16a34a"
              strokeWidth={2 / zoom}
              fill="rgba(22,163,74,0.2)"
            />
            <!-- Heading arrow -->
            <Line
              points={[cx, cy, tipX, tipY]}
              stroke="#16a34a"
              strokeWidth={2 / zoom}
            />
            <!-- Arrow tip -->
            <Circle x={tipX} y={tipY} radius={3 / zoom} fill="#16a34a" />
            <!-- Label -->
            <Text
              x={cx + 12 / zoom}
              y={cy - 8 / zoom}
              text={`(${displayRobotPos.x.toFixed(2)}, ${displayRobotPos.y.toFixed(2)}) ${((displayRobotPos.theta * 180) / Math.PI).toFixed(1)}°`}
              fontSize={10 / zoom}
              fill="#16a34a"
            />
          </Layer>
        {/if}
      </Stage>
    </div>
  </div>
{/if}
