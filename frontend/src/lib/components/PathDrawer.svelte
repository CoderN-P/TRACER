<script lang="ts">
  import { browser } from "$app/environment";
  import { onMount } from "svelte";
  import { io as socket } from "$lib/api/socket";
  import {
    PlusIcon,
    Trash,
    PenLine,
    Spline,
    Image,
    X,
    Play,
    StopCircle,
    CircleIcon,
    Square,
  } from "lucide-svelte";
  import { Stage, Layer, Line, Circle, Rect, Text } from "svelte-konva";
  import {
    QuinticHermiteSplineSvelte,
    SplinePathSvelte,
  } from "$lib/types/index.js";
  import RouteStats, {
    type RouteStatsSnapshot,
  } from "$lib/components/RouteStats.svelte";

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
  let HEIGHT = $state(460);
  const GRID_SPACING = 100; // pixels between grid lines (in world pixels at zoom=1)
  const TICK_LENGTH = 10; // length of axis ticks
  const PATH_RENDER_INTERVAL = 0.01; // seconds (dt)
  const SCALE = 100; // pixels per meter

  $effect(() => {
    if (!containerEl) return;
    const ro = new ResizeObserver(([entry]) => {
      const w = Math.floor(entry.contentRect.width);
      const h = Math.floor(entry.contentRect.height);
      if (w > 0 && h > 0 && (w !== WIDTH || h !== HEIGHT)) {
        // Keep the camera origin centred after resize.
        const dx = (w - WIDTH) / 2;
        const dh = (h - HEIGHT) / 2;
        stageX += dx;
        stageY += dh;
        WIDTH = w;
        HEIGHT = h;
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
  let robotTrajectory = $state<{ x: number; y: number }[]>([]);
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

  $effect(() => {
    if (!running || robotPos === null) return;

    const sample = { x: robotPos.x, y: robotPos.y };
    const lastSample = robotTrajectory[robotTrajectory.length - 1];
    if (
      lastSample &&
      Math.hypot(sample.x - lastSample.x, sample.y - lastSample.y) < 0.005
    ) {
      return;
    }

    robotTrajectory = [...robotTrajectory, sample];
  });

  // ── Mode ──────────────────────────────────────────────────────────────────
  type Mode = "spline" | "freehand" | "point" | "svg" | "obstacle";
  let mode = $state<Mode>("spline");

  // ── Point mode ────────────────────────────────────────────────────────────
  let selectedPoint = $state<{ x: number; y: number } | null>(null);

  // ── SVG mode ──────────────────────────────────────────────────────────────
  let svgPath = $state<{ x: number; y: number }[]>([]);
  let svgFileName = $state<string | null>(null);

  // ── Virtual obstacles ────────────────────────────────────────────────────
  type ObstacleShape = "circle" | "rectangle";
  type ObstacleAvoidanceMode = "normal" | "virtual";
  type VirtualObstaclePayload = {
    obstacle_type: ObstacleShape;
    position: [number, number];
    width: number | null;
    height: number | null;
    radius: number | null;
    rotation: number | null;
  };

  type VirtualObstacle =
    | {
        id: string;
        shape: "circle";
        x: number;
        y: number;
        radius: number;
      }
    | {
        id: string;
        shape: "rectangle";
        x: number;
        y: number;
        width: number;
        height: number;
        rotation: number;
      };

  let obstacleShape = $state<ObstacleShape>("circle");
  let obstacleAvoidanceMode = $state<ObstacleAvoidanceMode>("normal");
  let virtualObstacles = $state<VirtualObstacle[]>([]);
  let selectedObstacleId = $state<string | null>(null);
  let obstacleIdCounter = 0;

  function serializeVirtualObstacles(
    obstacles: VirtualObstacle[],
  ): VirtualObstaclePayload[] {
    return obstacles.map((obstacle) =>
      obstacle.shape === "circle"
        ? {
            obstacle_type: "circle",
            position: [obstacle.x, obstacle.y],
            width: null,
            height: null,
            radius: obstacle.radius,
            rotation: null,
          }
        : {
            obstacle_type: "rectangle",
            position: [obstacle.x, obstacle.y],
            width: obstacle.width,
            height: obstacle.height,
            radius: null,
            rotation: (obstacle.rotation * Math.PI) / 180,
          },
    );
  }

  function emitVirtualObstacles(obstacles: VirtualObstacle[]) {
    socket.emit(
      "update_virtual_obstacles",
      serializeVirtualObstacles(obstacles),
    );
  }

  function setVirtualObstacles(nextObstacles: VirtualObstacle[]) {
    virtualObstacles = nextObstacles;
    emitVirtualObstacles(nextObstacles);
  }

  function setObstacleAvoidanceMode(nextMode: ObstacleAvoidanceMode) {
    obstacleAvoidanceMode = nextMode;
    socket.emit("update_obstacle_mode", { mode: nextMode });

    if (nextMode === "virtual") {
      emitVirtualObstacles(virtualObstacles);
    }
  }

  function updateObstacle(
    id: string,
    update: (obstacle: VirtualObstacle) => VirtualObstacle,
  ) {
    setVirtualObstacles(
      virtualObstacles.map((obstacle) =>
        obstacle.id === id ? update(obstacle) : obstacle,
      ),
    );
  }

  function addVirtualObstacle(center: { x: number; y: number }) {
    const id = `virtual-obstacle-${++obstacleIdCounter}`;
    const obstacle: VirtualObstacle =
      obstacleShape === "circle"
        ? {
            id,
            shape: "circle",
            x: center.x,
            y: center.y,
            radius: 0.2,
          }
        : {
            id,
            shape: "rectangle",
            x: center.x,
            y: center.y,
            width: 0.4,
            height: 0.3,
            rotation: 0,
          };

    setVirtualObstacles([...virtualObstacles, obstacle]);
    selectedObstacleId = id;
  }

  function obstacleModeClick(e) {
    if (mode !== "obstacle" || running) return;
    if (e.evt.button !== 0) return;
    if (e.target !== e.target.getStage()) return;

    const world = pointerToWorld(e.target.getStage());
    addVirtualObstacle({ x: world.x / SCALE, y: -world.y / SCALE });
  }

  function deleteSelectedObstacle() {
    if (selectedObstacleId === null) return;
    setVirtualObstacles(
      virtualObstacles.filter((obstacle) => obstacle.id !== selectedObstacleId),
    );
    selectedObstacleId = null;
  }

  function clearVirtualObstacles() {
    setVirtualObstacles([]);
    selectedObstacleId = null;
  }

  function rotatePoint(
    point: { x: number; y: number },
    center: { x: number; y: number },
    degrees: number,
  ) {
    const radians = (degrees * Math.PI) / 180;
    const cos = Math.cos(radians);
    const sin = Math.sin(radians);
    const dx = point.x - center.x;
    const dy = point.y - center.y;

    return {
      x: center.x + dx * cos - dy * sin,
      y: center.y + dx * sin + dy * cos,
    };
  }

  function screenToWorldMeters(position: { x: number; y: number }) {
    return {
      x: position.x / SCALE,
      y: -position.y / SCALE,
    };
  }

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

  /** Resample a polyline in meters so points are evenly spaced by `step`. */
  function resamplePolylineMeters(
    pts: { x: number; y: number }[],
    step: number,
  ): { x: number; y: number }[] {
    if (pts.length < 2) return pts.length === 1 ? [{ ...pts[0] }] : [];
    const result: { x: number; y: number }[] = [{ ...pts[0] }];
    let carry = 0;
    for (let i = 1; i < pts.length; i++) {
      const dx = pts[i].x - pts[i - 1].x;
      const dy = pts[i].y - pts[i - 1].y;
      const segLen = Math.sqrt(dx * dx + dy * dy);
      if (segLen === 0) continue;
      let offset = step - carry;
      while (offset <= segLen) {
        const t = offset / segLen;
        result.push({
          x: pts[i - 1].x + t * dx,
          y: pts[i - 1].y + t * dy,
        });
        offset += step;
      }
      carry = segLen - (offset - step);
    }
    return result;
  }

  async function handleSvgUpload(e: Event) {
    const input = e.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".svg")) {
      svgPath = [];
      svgFileName = null;
      input.value = "";
      return;
    }

    const svgText = await file.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(svgText, "image/svg+xml");
    const parseError = doc.querySelector("parsererror");
    if (parseError) {
      svgPath = [];
      svgFileName = null;
      input.value = "";
      return;
    }

    const sourceSvg = doc.querySelector("svg");
    if (!sourceSvg) {
      svgPath = [];
      svgFileName = null;
      input.value = "";
      return;
    }

    // Attach the SVG off-screen so geometry APIs can evaluate lengths/points.
    const host = document.createElement("div");
    host.style.position = "absolute";
    host.style.left = "-10000px";
    host.style.top = "-10000px";
    host.style.width = "0";
    host.style.height = "0";
    host.style.overflow = "hidden";

    const workSvg = document.importNode(sourceSvg, true) as SVGSVGElement;
    host.appendChild(workSvg);
    document.body.appendChild(host);

    try {
      const geometryEls = Array.from(
        workSvg.querySelectorAll(
          "path, polyline, polygon, rect, circle, ellipse, line",
        ),
      ) as SVGGeometryElement[];

      let selected: SVGGeometryElement | null = null;
      let longest = 0;
      for (const el of geometryEls) {
        const length = Number(el.getTotalLength?.());
        if (!Number.isFinite(length) || length <= 0) continue;
        if (length > longest) {
          longest = length;
          selected = el;
        }
      }

      if (!selected || longest < 2) {
        svgPath = [];
        svgFileName = null;
        input.value = "";
        return;
      }

      const sampleCount = Math.max(80, Math.min(3000, Math.round(longest / 2)));
      const sampledPx: { x: number; y: number }[] = [];
      for (let i = 0; i < sampleCount; i++) {
        const d = (i / (sampleCount - 1)) * longest;
        const p = selected.getPointAtLength(d);
        sampledPx.push({ x: p.x, y: p.y });
      }

      const xs = sampledPx.map((p) => p.x);
      const ys = sampledPx.map((p) => p.y);
      const width = Math.max(...xs) - Math.min(...xs);
      const height = Math.max(...ys) - Math.min(...ys);
      const maxDim = Math.max(width, height, 1);
      const targetSizeM = 2; // normalize SVG so its largest dimension is ~2m
      const scaleToMeters = targetSizeM / maxDim;

      const first = sampledPx[0];
      const meters = sampledPx.map((p) => ({
        x: (p.x - first.x) * scaleToMeters,
        y: -(p.y - first.y) * scaleToMeters,
      }));

      svgPath = resamplePolylineMeters(meters, 0.01);
      svgFileName = file.name;
      mode = "svg";
    } finally {
      host.remove();
      input.value = "";
    }
  }

  /** Flat array of world-pixel coords for rendering the live stroke. */
  let rawStrokePoints = $derived(rawStroke.flatMap((p) => [p.x, p.y]));

  /** Flat array of world-pixel coords for rendering the finalised freehand path. */
  let freehandPathPoints = $derived(
    freehandPath.flatMap((p) => [p.x * SCALE, -p.y * SCALE]),
  );

  /** Flat array of world-pixel coords for rendering the imported SVG path. */
  let svgPathPoints = $derived(
    svgPath.flatMap((p) => [p.x * SCALE, -p.y * SCALE]),
  );

  /** Flat array of world-pixel coords for the recorded robot trajectory. */
  let robotTrajectoryPoints = $derived(
    robotTrajectory.flatMap((p) => [p.x * SCALE, -p.y * SCALE]),
  );

  // ── Run mode ──────────────────────────────────────────────────────────────
  // When running, we record which type of path is active and a UI offset so
  // spline/freehand-style paths appear to start at the robot's current position.
  type RunSource = "spline" | "freehand" | "point" | "svg";
  let running = $state(false);
  let runSource = $state<RunSource>("spline");
  // Offset in meters applied only for rendering while running.
  let runOffsetX = $state(0);
  let runOffsetY = $state(0);

  function translatePathPoint(point: { x: number; y: number }) {
    return {
      x: point.x + runOffsetX,
      y: point.y + runOffsetY,
    };
  }

  function translateSplineJSON(
    splineJSON: ReturnType<SplinePathSvelte["exportToJSON"]>,
  ) {
    return {
      splines: splineJSON.splines.map((spline) => ({
        ...spline,
        start: [spline.start[0] + runOffsetX, spline.start[1] + runOffsetY] as [
          number,
          number,
        ],
        end: [spline.end[0] + runOffsetX, spline.end[1] + runOffsetY] as [
          number,
          number,
        ],
      })),
    };
  }

  function setRunOffsetFromStartPoint(startPoint: { x: number; y: number }) {
    if (displayRobotPos === null) {
      runOffsetX = 0;
      runOffsetY = 0;
      return;
    }

    runOffsetX = displayRobotPos.x - startPoint.x;
    runOffsetY = displayRobotPos.y - startPoint.y;
  }

  /** True when the active mode has a drawable path ready. */
  let canRun = $derived(
    mode === "spline"
      ? path.QuinticHermiteSplines.length > 0
      : mode === "freehand"
        ? freehandPath.length > 0
        : mode === "point"
          ? selectedPoint !== null
          : mode === "svg"
            ? svgPath.length > 1
            : false,
  );

  function startRun() {
    if (!canRun) return;
    runSource = mode;
    runOffsetX = 0;
    runOffsetY = 0;
    robotTrajectory = displayRobotPos
      ? [{ x: displayRobotPos.x, y: displayRobotPos.y }]
      : [];

    // Shift the path so its first point coincides with the robot's current pos.
    if (runSource === "freehand" && freehandPath.length > 0) {
      setRunOffsetFromStartPoint(freehandPath[0]);

      // Set camera to center on robot for freehand mode since the path can start anywhere
      if (displayRobotPos !== null) {
        stageX = WIDTH / 2 - displayRobotPos.x * SCALE * zoom;
        stageY = HEIGHT / 2 + displayRobotPos.y * SCALE * zoom;
      }
    } else if (
      runSource === "spline" &&
      path.QuinticHermiteSplines.length > 0
    ) {
      const firstSpline = path.QuinticHermiteSplines[0];
      setRunOffsetFromStartPoint({ x: firstSpline.x0, y: firstSpline.y0 });

      // Center camera on robot for spline mode as well, since the path always starts at the first control point which may be far from the canvas center
      if (displayRobotPos !== null) {
        stageX = WIDTH / 2 - displayRobotPos.x * SCALE * zoom;
        stageY = HEIGHT / 2 + displayRobotPos.y * SCALE * zoom;
      }
    } else if (runSource === "svg" && svgPath.length > 0) {
      // SVG outlines are treated like freehand paths for the emitted payload.
      setRunOffsetFromStartPoint(svgPath[0]);

      if (displayRobotPos !== null) {
        stageX = WIDTH / 2 - displayRobotPos.x * SCALE * zoom;
        stageY = HEIGHT / 2 + displayRobotPos.y * SCALE * zoom;
      }
    }
    running = true;

    // Build a typed payload and hand it off to the parent.
    let payload: RunPathPayload;
    if (runSource === "freehand") {
      payload = {
        type: "freehand",
        path: freehandPath.map(translatePathPoint),
      };
    } else if (runSource === "spline") {
      // Export the spline definition (control points + derivatives) directly —
      // no need to pre-sample; the RPi can integrate at its own resolution.
      const splineJSON = translateSplineJSON(path.exportToJSON());
      payload = {
        type: "spline",
        path: splineJSON,
      };
    } else if (runSource === "svg") {
      // SVG outline is converted to pure-pursuit points, same payload shape as freehand.
      payload = {
        type: "freehand",
        path: svgPath.map(translatePathPoint),
      };
    } else {
      // Point mode
      payload = {
        type: "point",
        path: {
          x: selectedPoint?.x ?? 0,
          y: selectedPoint?.y ?? 0,
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

  function clearTrajectory() {
    robotTrajectory = [];
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

  function clampDegrees(degrees: number): number {
    let angle = degrees % 360;
    return angle < 0 ? angle + 360 : angle;
  }

  type PointMeters = { x: number; y: number };

  type NearestPathResult = {
    distance: number;
    signedDistance: number;
    heading: number | null;
    segmentIndex: number;
  };

  const CONSTANTS_STORAGE_KEY = "tracer.constant-tuner.constants.v1";
  const DEFAULT_LOOKAHEAD_DISTANCE = 0.4;

  let lookaheadDistance = $state(DEFAULT_LOOKAHEAD_DISTANCE);

  function readStoredLookaheadDistance() {
    if (!browser) return DEFAULT_LOOKAHEAD_DISTANCE;

    try {
      const raw = localStorage.getItem(CONSTANTS_STORAGE_KEY);
      if (!raw) return DEFAULT_LOOKAHEAD_DISTANCE;

      const parsed = JSON.parse(raw) as { LOOKAHEAD_DISTANCE?: unknown };
      return typeof parsed.LOOKAHEAD_DISTANCE === "number" &&
        Number.isFinite(parsed.LOOKAHEAD_DISTANCE) &&
        parsed.LOOKAHEAD_DISTANCE > 0
        ? parsed.LOOKAHEAD_DISTANCE
        : DEFAULT_LOOKAHEAD_DISTANCE;
    } catch {
      return DEFAULT_LOOKAHEAD_DISTANCE;
    }
  }

  function syncLookaheadFromConstants(constants: unknown) {
    const value =
      constants &&
      typeof constants === "object" &&
      "LOOKAHEAD_DISTANCE" in constants
        ? (constants as { LOOKAHEAD_DISTANCE?: unknown }).LOOKAHEAD_DISTANCE
        : null;

    if (typeof value === "number" && Number.isFinite(value) && value > 0) {
      lookaheadDistance = value;
    }
  }

  onMount(() => {
    lookaheadDistance = readStoredLookaheadDistance();

    function handleConstantsUpdated(event: Event) {
      syncLookaheadFromConstants((event as CustomEvent).detail);
    }

    window.addEventListener("tracer:constants-updated", handleConstantsUpdated);
    return () =>
      window.removeEventListener(
        "tracer:constants-updated",
        handleConstantsUpdated,
      );
  });

  function normalizeRadians(angle: number) {
    let normalized = ((angle + Math.PI) % (2 * Math.PI)) - Math.PI;
    if (normalized < -Math.PI) normalized += 2 * Math.PI;
    return normalized;
  }

  function plannedSplinePoints(): PointMeters[] {
    return path.QuinticHermiteSplines.flatMap((spline) => {
      const points: PointMeters[] = [];
      for (let t = 0; t <= 1.000001; t += PATH_RENDER_INTERVAL) {
        const p = spline.evaluate(Math.min(t, 1));
        points.push(translatePathPoint(p));
      }
      return points;
    });
  }

  function activePathPoints(): PointMeters[] {
    if (running) {
      if (runSource === "freehand") return freehandPath.map(translatePathPoint);
      if (runSource === "svg") return svgPath.map(translatePathPoint);
      if (runSource === "spline") return plannedSplinePoints();
      return selectedPoint ? [selectedPoint] : [];
    }

    if (mode === "freehand") return freehandPath;
    if (mode === "svg") return svgPath;
    if (mode === "point") return selectedPoint ? [selectedPoint] : [];
    return plannedSplinePoints();
  }

  function findNearestPathSegment(
    point: PointMeters,
    points: PointMeters[],
  ): NearestPathResult | null {
    if (points.length === 0) return null;
    if (points.length === 1) {
      return {
        distance: Math.hypot(point.x - points[0].x, point.y - points[0].y),
        signedDistance: Math.hypot(point.x - points[0].x, point.y - points[0].y),
        heading: null,
        segmentIndex: 0,
      };
    }

    let best: NearestPathResult | null = null;
    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i];
      const end = points[i + 1];
      const dx = end.x - start.x;
      const dy = end.y - start.y;
      const lenSq = dx * dx + dy * dy;
      if (lenSq === 0) continue;

      const projection = Math.max(
        0,
        Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lenSq),
      );
      const nearest = {
        x: start.x + projection * dx,
        y: start.y + projection * dy,
      };
      const cross = dx * (point.y - start.y) - dy * (point.x - start.x);
      const distance = Math.hypot(point.x - nearest.x, point.y - nearest.y);
      const candidate = {
        distance,
        signedDistance: Math.sign(cross || 1) * distance,
        heading: Math.atan2(dy, dx),
        segmentIndex: i,
      };

      if (best === null || candidate.distance < best.distance) {
        best = candidate;
      }
    }

    return best;
  }

  function percentile(values: number[], percentileValue: number) {
    if (values.length === 0) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.min(
      sorted.length - 1,
      Math.ceil((percentileValue / 100) * sorted.length) - 1,
    );
    return sorted[Math.max(0, index)];
  }

  function curvatureAt(points: PointMeters[], index: number) {
    if (points.length < 3) return null;
    const i = Math.max(1, Math.min(points.length - 2, index));
    const a = points[i - 1];
    const b = points[i];
    const c = points[i + 1];
    const ab = Math.hypot(b.x - a.x, b.y - a.y);
    const bc = Math.hypot(c.x - b.x, c.y - b.y);
    const ca = Math.hypot(a.x - c.x, a.y - c.y);
    const denominator = ab * bc * ca;
    if (denominator < 1e-9) return null;

    const twiceArea =
      (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
    return (2 * twiceArea) / denominator;
  }

  function lookaheadIndex(
    points: PointMeters[],
    startIndex: number,
    lookaheadDistance: number,
  ) {
    let accumulated = 0;
    for (let i = startIndex; i < points.length - 1; i++) {
      accumulated += Math.hypot(
        points[i + 1].x - points[i].x,
        points[i + 1].y - points[i].y,
      );
      if (accumulated >= lookaheadDistance) return i + 1;
    }
    return Math.max(0, points.length - 1);
  }

  function buildRouteStats(
    points: PointMeters[],
    pose: { x: number; y: number; theta: number } | null,
    trajectory: PointMeters[],
  ): RouteStatsSnapshot {
    const nearest = pose ? findNearestPathSegment(pose, points) : null;
    const samples = trajectory.length > 0 ? trajectory : pose ? [pose] : [];
    const errors = samples
      .map((sample) => findNearestPathSegment(sample, points)?.distance ?? null)
      .filter((value): value is number => value !== null);
    const goal = points[points.length - 1] ?? null;
    const purePursuitActive =
      running && (runSource === "freehand" || runSource === "svg");
    const curvatureIndex = nearest?.segmentIndex ?? 0;

    return {
      currentCrossTrackError: nearest?.signedDistance ?? null,
      averageCrossTrackError:
        errors.length > 0
          ? errors.reduce((sum, value) => sum + value, 0) / errors.length
          : null,
      headingError:
        pose && nearest?.heading !== null && nearest?.heading !== undefined
          ? (normalizeRadians(pose.theta - nearest.heading) * 180) / Math.PI
          : null,
      maxCrossTrackError: errors.length > 0 ? Math.max(...errors) : null,
      percentile95CrossTrackError: percentile(errors, 95),
      distanceToGoal:
        pose && goal ? Math.hypot(pose.x - goal.x, pose.y - goal.y) : null,
      currentCurvature: purePursuitActive
        ? curvatureAt(points, curvatureIndex)
        : null,
      targetCurvature: purePursuitActive
        ? curvatureAt(
            points,
            lookaheadIndex(
              points,
              curvatureIndex,
              lookaheadDistance,
            ),
          )
        : null,
      lookaheadDistance,
      purePursuitActive,
      sampleCount: errors.length,
    };
  }

  let routeStats = $derived(
    buildRouteStats(activePathPoints(), displayRobotPos, robotTrajectory),
  );
</script>

{#if !browser}
  <p>Loading...</p>
{:else}
  <div
    class="h-full min-h-0 rounded-lg border border-gray-200 p-4 bg-white flex flex-col select-none"
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
        <button
          onclick={() => {
            mode = "svg";
          }}
          disabled={running}
          class="flex items-center gap-1 px-3 py-2 text-xs transition-colors border-l border-gray-200 {mode ===
          'svg'
            ? 'bg-emerald-600 text-white'
            : 'bg-gray-50 text-black hover:bg-gray-100'} disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Image class="w-3.5 h-3.5" /> SVG
        </button>
        <button
          onclick={() => {
            mode = "obstacle";
          }}
          disabled={running}
          class="flex items-center gap-1 px-3 py-2 text-xs transition-colors border-l border-gray-200 {mode ===
          'obstacle'
            ? 'bg-red-600 text-white'
            : 'bg-gray-50 text-black hover:bg-gray-100'} disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Square class="w-3.5 h-3.5" /> Obstacles
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

      <!-- SVG-mode controls -->
      {#if mode === "svg"}
        <label
          class="flex items-center gap-1 px-3 py-2 text-xs bg-gray-50 text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
          title="Upload an SVG outline"
        >
          <Image class="w-3.5 h-3.5" /> Upload SVG
          <input
            type="file"
            accept=".svg,image/svg+xml"
            onchange={handleSvgUpload}
            class="hidden"
            disabled={running}
          />
        </label>
        <button
          onclick={() => {
            svgPath = [];
            svgFileName = null;
          }}
          class="flex items-center gap-1 px-3 py-2 text-xs bg-gray-50 text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
          title="Clear imported SVG path"
        >
          <X class="w-3.5 h-3.5" /> Clear
        </button>
        <span class="text-xs text-gray-400">
          {svgFileName
            ? `${svgFileName} · ${svgPath.length} pts`
            : "Upload an SVG; longest outline is converted to path"}
        </span>
      {/if}

      <!-- Obstacle-mode controls -->
      {#if mode === "obstacle"}
        <div class="flex overflow-hidden rounded-md border border-gray-200">
          <button
            onclick={() => setObstacleAvoidanceMode("normal")}
            class="px-3 py-2 text-xs font-semibold transition-colors {obstacleAvoidanceMode ===
            'normal'
              ? 'bg-gray-900 text-white'
              : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}"
            title="Use physical sensors for obstacle handling"
          >
            Normal
          </button>
          <button
            onclick={() => setObstacleAvoidanceMode("virtual")}
            class="border-l border-gray-200 px-3 py-2 text-xs font-semibold transition-colors {obstacleAvoidanceMode ===
            'virtual'
              ? 'bg-red-600 text-white'
              : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}"
            title="Use virtual map obstacles for obstacle handling"
          >
            Virtual
          </button>
        </div>
        <div class="flex overflow-hidden rounded-md border border-gray-200">
          <button
            onclick={() => {
              obstacleShape = "circle";
            }}
            class="flex items-center gap-1 px-3 py-2 text-xs transition-colors {obstacleShape ===
            'circle'
              ? 'bg-red-600 text-white'
              : 'bg-gray-50 text-black hover:bg-gray-100'}"
            title="Place circular obstacles"
          >
            <CircleIcon class="w-3.5 h-3.5" /> Circle
          </button>
          <button
            onclick={() => {
              obstacleShape = "rectangle";
            }}
            class="flex items-center gap-1 border-l border-gray-200 px-3 py-2 text-xs transition-colors {obstacleShape ===
            'rectangle'
              ? 'bg-red-600 text-white'
              : 'bg-gray-50 text-black hover:bg-gray-100'}"
            title="Place rectangular obstacles"
          >
            <Square class="w-3.5 h-3.5" /> Rect
          </button>
        </div>
        <button
          onclick={deleteSelectedObstacle}
          disabled={selectedObstacleId === null}
          class="flex items-center gap-1 px-3 py-2 text-xs bg-gray-50 text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors disabled:cursor-not-allowed disabled:opacity-40"
          title="Delete selected obstacle"
        >
          <Trash class="w-3.5 h-3.5" /> Delete
        </button>
        <button
          onclick={clearVirtualObstacles}
          disabled={virtualObstacles.length === 0}
          class="flex items-center gap-1 px-3 py-2 text-xs bg-gray-50 text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors disabled:cursor-not-allowed disabled:opacity-40"
          title="Clear virtual obstacles"
        >
          <X class="w-3.5 h-3.5" /> Clear
        </button>
        <span class="text-xs text-gray-400">
          {virtualObstacles.length} obstacle{virtualObstacles.length === 1
            ? ""
            : "s"} · click map to place, drag to move, drag red/orange handles
          to scale/rotate
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
        {#if robotTrajectory.length > 0}
          <button
            onclick={clearTrajectory}
            class="flex items-center gap-1.5 px-3 py-2 text-xs rounded-md border border-gray-200 bg-gray-50 text-gray-700 transition-colors hover:bg-gray-100"
            title="Clear recorded robot trajectory"
          >
            <X class="w-3.5 h-3.5" /> Clear Trail
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
      class="min-h-0 flex-1 w-full"
      style="cursor: {mode === 'freehand'
        ? isDrawing
          ? 'crosshair'
          : 'crosshair'
        : mode === 'point' || mode === 'obstacle'
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
          } else if (mode === "obstacle") {
            obstacleModeClick(e);
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

        <!-- Virtual obstacles -->
        {#if virtualObstacles.length > 0}
          <Layer>
            {#each virtualObstacles as obstacle (obstacle.id)}
              {@const selected = selectedObstacleId === obstacle.id}
              {#if obstacle.shape === "circle"}
                <Circle
                  x={obstacle.x * SCALE}
                  y={-obstacle.y * SCALE}
                  radius={obstacle.radius * SCALE}
                  fill="rgba(239, 68, 68, 0.18)"
                  stroke={selected ? "#dc2626" : "#f97316"}
                  strokeWidth={(selected ? 2.5 : 1.5) / zoom}
                  dash={selected ? [] : [8 / zoom, 6 / zoom]}
                  draggable={!running}
                  onclick={() => {
                    selectedObstacleId = obstacle.id;
                  }}
                  ondragmove={(e) => {
                    const pos = e.target.position();
                    updateObstacle(obstacle.id, (current) =>
                      current.shape === "circle"
                        ? {
                            ...current,
                            x: pos.x / SCALE,
                            y: -pos.y / SCALE,
                          }
                        : current,
                    );
                  }}
                />
                {#if selected && !running}
                  <Circle
                    x={(obstacle.x + obstacle.radius) * SCALE}
                    y={-obstacle.y * SCALE}
                    radius={6 / zoom}
                    fill="#dc2626"
                    stroke="white"
                    strokeWidth={1.5 / zoom}
                    draggable
                    ondragmove={(e) => {
                      const pos = e.target.position();
                      const world = { x: pos.x / SCALE, y: -pos.y / SCALE };
                      updateObstacle(obstacle.id, (current) =>
                        current.shape === "circle"
                          ? {
                              ...current,
                              radius: Math.max(
                                0.05,
                                Math.hypot(
                                  world.x - current.x,
                                  world.y - current.y,
                                ),
                              ),
                            }
                          : current,
                      );
                    }}
                  />
                {/if}
              {:else}
                {@const rectWidthPx = obstacle.width * SCALE}
                {@const rectHeightPx = obstacle.height * SCALE}
                {@const resizeHandle = rotatePoint(
                  {
                    x: obstacle.x + obstacle.width / 2,
                    y: obstacle.y - obstacle.height / 2,
                  },
                  obstacle,
                  obstacle.rotation,
                )}
                {@const rotationHandle = rotatePoint(
                  {
                    x: obstacle.x,
                    y: obstacle.y + obstacle.height / 2 + 0.18,
                  },
                  obstacle,
                  obstacle.rotation,
                )}
                {@const rotationStem = rotatePoint(
                  {
                    x: obstacle.x,
                    y: obstacle.y + obstacle.height / 2,
                  },
                  obstacle,
                  obstacle.rotation,
                )}
                <Rect
                  x={obstacle.x * SCALE}
                  y={-obstacle.y * SCALE}
                  width={rectWidthPx}
                  height={rectHeightPx}
                  offsetX={rectWidthPx / 2}
                  offsetY={rectHeightPx / 2}
                  rotation={-obstacle.rotation}
                  fill="rgba(239, 68, 68, 0.16)"
                  stroke={selected ? "#dc2626" : "#f97316"}
                  strokeWidth={(selected ? 2.5 : 1.5) / zoom}
                  dash={selected ? [] : [8 / zoom, 6 / zoom]}
                  draggable={!running}
                  onclick={() => {
                    selectedObstacleId = obstacle.id;
                  }}
                  ondragmove={(e) => {
                    const pos = e.target.position();
                    updateObstacle(obstacle.id, (current) =>
                      current.shape === "rectangle"
                        ? {
                            ...current,
                            x: pos.x / SCALE,
                            y: -pos.y / SCALE,
                          }
                        : current,
                    );
                  }}
                />
                {#if selected && !running}
                  <Line
                    points={[
                      rotationStem.x * SCALE,
                      -rotationStem.y * SCALE,
                      rotationHandle.x * SCALE,
                      -rotationHandle.y * SCALE,
                    ]}
                    stroke="#dc2626"
                    strokeWidth={1.5 / zoom}
                  />
                  <Circle
                    x={rotationHandle.x * SCALE}
                    y={-rotationHandle.y * SCALE}
                    radius={5.5 / zoom}
                    fill="#f97316"
                    stroke="white"
                    strokeWidth={1.5 / zoom}
                    draggable
                    ondragmove={(e) => {
                      const world = screenToWorldMeters(e.target.position());
                      updateObstacle(obstacle.id, (current) => {
                        if (current.shape !== "rectangle") return current;
                        const angle =
                          (Math.atan2(
                            world.y - current.y,
                            world.x - current.x,
                          ) *
                            180) /
                            Math.PI -
                          90;
                        return {
                          ...current,
                          rotation: angle,
                        };
                      });
                    }}
                  />
                  <Circle
                    x={resizeHandle.x * SCALE}
                    y={-resizeHandle.y * SCALE}
                    radius={6 / zoom}
                    fill="#dc2626"
                    stroke="white"
                    strokeWidth={1.5 / zoom}
                    draggable
                    ondragmove={(e) => {
                      const world = screenToWorldMeters(e.target.position());
                      updateObstacle(obstacle.id, (current) => {
                        if (current.shape !== "rectangle") return current;
                        const local = rotatePoint(
                          world,
                          current,
                          -current.rotation,
                        );
                        const left = current.x - current.width / 2;
                        const top = current.y + current.height / 2;
                        const width = Math.max(0.05, local.x - left);
                        const height = Math.max(0.05, top - local.y);
                        const center = rotatePoint(
                          {
                            x: left + width / 2,
                            y: top - height / 2,
                          },
                          current,
                          current.rotation,
                        );
                        return {
                          ...current,
                          width,
                          height,
                          x: center.x,
                          y: center.y,
                        };
                      });
                    }}
                  />
                {/if}
              {/if}
            {/each}
          </Layer>
        {/if}

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

        <!-- Imported SVG outline path -->
        {#if (!running || runSource === "svg") && svgPathPoints.length >= 4}
          <Layer>
            <Line
              points={running && runSource === "svg"
                ? svgPath.flatMap((p) => [
                    (p.x + runOffsetX) * SCALE,
                    -(p.y + runOffsetY) * SCALE,
                  ])
                : svgPathPoints}
              stroke="#059669"
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
        {#if mode === "point" && selectedPoint !== null}
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

        <!-- Recorded robot trajectory during the active run -->
        {#if robotTrajectoryPoints.length >= 4}
          <Layer>
            <Line
              points={robotTrajectoryPoints}
              stroke="#ef4444"
              strokeWidth={2.5 / zoom}
              closed={false}
              lineCap="round"
              lineJoin="round"
              dash={[8 / zoom, 6 / zoom]}
              opacity={0.9}
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
              text={`(${displayRobotPos.x.toFixed(2)}, ${displayRobotPos.y.toFixed(2)}) ${clampDegrees((displayRobotPos.theta * 180) / Math.PI).toFixed(1)}°`}
              fontSize={10 / zoom}
              fill="#16a34a"
            />
          </Layer>
        {/if}
      </Stage>
    </div>
    <RouteStats stats={routeStats} {running} />
  </div>
{/if}
